#!/usr/bin/python

# ---------------------
# Developed by National Center for Media Forensics
# University of Colorado Denver
# YouTubeUP-DOWN.sh v.6 9/23/2017
#
# REQUIREMENTS:
# View README.txt
#
# This file is derived from from Google's developer resources and has been modified
# to integrate the youtube-dl Python library
# ---------------------

# this imports a Python library needed for unicode encoding in download object args
from __future__ import unicode_literals

import httplib
import httplib2
import json
import os
import random
import sys
import time
import argparse
import subprocess as sp
import contextlib
from maskgen import software_loader
from maskgen import video_tools
import maskgen
import logging
from collections import OrderedDict
try:
    import youtube_dl
except ImportError:
    logging.getLogger('maskgen').error('Missing python library youtube_dl, run: pip install youtube-dl')
    raise ValueError('Missing python dependencies')
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from oauth2client.client import flow_from_clientsecrets
    from oauth2client.file import Storage
    from oauth2client.tools import run_flow
except ImportError:
    logging.getLogger('maskgen').error('Missing python libraries for google API or oauth.\n'
                                       'run: pip install --upgrade google-api-python-client')
    raise ValueError('Missing python dependencies')

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
                        httplib.IncompleteRead, httplib.ImproperConnectionState,
                        httplib.CannotSendRequest, httplib.CannotSendHeader,
                        httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google Developers Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = software_loader.getFileName('client_secrets.json')
OAUTH_FILE = software_loader.getFileName('youtube-oauth2.json')

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """Please configure OAuth 2.0

To run this plugin, you will need to place a populated client_secrets.json file in maskgen/resources. 
If there is one there already, it is invalid.

Download the Json using the developers console at:
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
"""

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

def get_authenticated_service(scope, oauth):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=scope, message=MISSING_CLIENT_SECRETS_MESSAGE)
    storage = Storage(oauth if oauth is not None else
                      os.path.join(os.path.dirname(CLIENT_SECRETS_FILE), 'youtube-oauth2.json'))
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        try:
            credentials = run_flow(flow, storage)
        except SystemExit:
            raise ValueError('Credentials file could not be obtained!')

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)


def initialize_upload(youtube, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category
        ),
        status=dict(
            privacyStatus=options.privacyStatus
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )
    return resumable_upload(insert_request)


# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            status, response = insert_request.next_chunk()
            if 'id' not in response:
                logging.getLogger('maskgen').error("The upload failed with an unexpected response: %s" % response)
                raise ValueError('Unexpected Response')
        except HttpError, e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS, e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            logging.getLogger('maskgen').error(error)
            retry += 1
            if retry > MAX_RETRIES:
                logging.getLogger('maskgen').error("No longer attempting to retry.")
                raise ValueError('Retrying ultimately failed.')

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            logging.getLogger('maskgen').info("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)
    return str(response['id']).strip()

def upload_file(youtube, fname):
    # get the file extension for later use in saving downloaded video
    #ext = os.path.splitext(fname)[0]

    # replacing the args namespace variable above to repurpose it.
    # since these are pretty standard here, we can simplify the command
    # line requirements by using a Namespace object to pass the necessary
    # data into the auth process
    args = argparse.Namespace()
    args.file = fname
    args.title = os.path.split(fname)[1]
    args.description = fname
    args.keywords = ''
    args.category = 22
    args.privacyStatus = 'unlisted'
    args.logging_level = 'ERROR'
    args.noauth_local_webserver = 'true'

    # does the file we are trying to upload exist?
    if not os.path.exists(args.file):
        logging.getLogger('maskgen').info("Video file, " + args.file + " cannot be found or is invalid.")

    # start the upload process
        logging.getLogger('maskgen').info('uploading ' + fname + '...')

    # the upload happens here and we are returned the YouTube ID
    try:
        youtubeID = initialize_upload(youtube, args)
    except HttpError, e:
        rc = json.loads(e.content)
        logging.getLogger('maskgen').error('An HTTP error %d occurred and the process could not continue:\n%s' % (
            e.resp.status, rc['code'] + ': ' + rc['message']))
        raise ValueError('HTTP Error')

    # get the uploaded video id

    return youtubeID

def get_upload_status(youtube, youtubeID):
    status = videos_list_by_id(youtube, part='status', id=youtubeID)
    return str(status['items'][0]['status']['uploadStatus'])

def download_files(youtubeID, quality, resultDir):

    # Set YoutubeDL parms
    ydl_opts = {
        'format': quality,
        'outtmpl': resultDir
    }

    # create the video object and retrieve the video using the loop quality/format
    # level and youtubeID from the list.
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            url = 'https://www.youtube.com/watch?v=' + youtubeID
            # if we got this far the assumption can be made that an error is either unavailable format or a
            # connection issue neither of which can be controlled from here and processing should continue.
            # after the except.
            ydl.download([url])
    except youtube_dl.DownloadError:
        pass

# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):
    good_kwargs = {}
    if kwargs is not None:
        for key, value in kwargs.iteritems():
            if value:
                good_kwargs[key] = value
    return good_kwargs


def videos_list_by_id(client, **kwargs):
    # See full sample for function
    kwargs = remove_empty_kwargs(**kwargs)
    response = client.videos().list(**kwargs).execute()
    return response

def delete_video(client, **kwargs):
    kwargs = remove_empty_kwargs(**kwargs)
    response = client.videos().delete(**kwargs).execute()
    return response

def get_valid_resolution(source, target_resolution):
    resolutions = ['2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p']
    width, height = video_tools.get_shape_of_video(source)
    orientation = 'landscape' if width > height else 'portrait'
    src_resolution = height if orientation == 'landscape' else width
    if int(target_resolution[:-1]) > src_resolution:
        index = len(resolutions)-1
        while index > 0:
            if src_resolution <= int(resolutions[index][:-1]):
                return resolutions[index]
            index -= 1
    return target_resolution

def waitForProcessing(youtube, youtubeID, source, quality):
    #scale the wait time by duration and wait longer if we target better quality
    waitTime = int((video_tools.get_duration(video_tools.FileMetaDataLocator(source))/1000))
    target_res = int(quality[:-1])
    #Just guessing on most of these, might need to wait even longer for 1440 and 4k
    if target_res >= 2160:
        waitTime *= 12
    elif target_res >= 1440:
        waitTime *= 11
    elif target_res >= 1080:
        waitTime *= 8
    elif target_res >= 720:
        waitTime *= 5
    elif target_res >= 480:
        waitTime *= 3
    waitTime = 30 if waitTime < 30 else waitTime
    logging.getLogger('maskgen').info('Waiting %s seconds for processing- higher resolutions wait longer.' % waitTime)
    time.sleep(15) # wait 15 to find out if we got rejected
    status = get_upload_status(youtube, youtubeID)
    if status == 'rejected':
        return
    time.sleep(waitTime-15)
    #make sure processing is finished, but don't wait all day.
    while waitTime <= 600:
        status = get_upload_status(youtube, youtubeID)
        if status == 'processed':
            return
        else:
            waitTime += 10
            time.sleep(10)

def compare_dimensions(pathOne='',pathTwo=''):
    path = ''
    try:
        if os.path.exists(pathOne) and os.path.exists(pathTwo):
            #return best resolution video of the two
            heightOne = video_tools.get_shape_of_video(pathOne)[1]
            heightTwo = video_tools.get_shape_of_video(pathTwo)[1]
            path = pathOne if heightOne > heightTwo else pathTwo
        elif not os.path.exists(pathOne) and not os.path.exists(pathTwo):
            raise ValueError('Requested quality file not available- try again with a different max_resolution')
        else:
            path = pathOne if os.path.exists(pathOne) else pathTwo
        return path
    finally:
        #Clean up the unused tempfile
        if path == pathOne and os.path.exists(pathTwo):
            os.remove(pathTwo)
        elif path == pathTwo and os.path.exists(pathOne):
            os.remove(pathOne)

def transform(img,source,target,**kwargs):
    quality = get_valid_resolution(source, kwargs['max_resolution']) #There will never be a larger res video from youtube.
    if CLIENT_SECRETS_FILE == None:
        logging.getLogger('maskgen').error(MISSING_CLIENT_SECRETS_MESSAGE)
        raise ValueError('Invalid or missing client_secrets.json- see console/log for more information.')
    # authenticate with the youtube account
    youtube = get_authenticated_service(YOUTUBE_UPLOAD_SCOPE, OAUTH_FILE)
    # instantiate a list for the IDs
    logging.getLogger('maskgen').info('Attempting upload of ' + str(source))
    youtubeID = upload_file(youtube, source)
    try:
        waitForProcessing(youtube, youtubeID, source, quality)
        logging.getLogger('maskgen').info('Retrieving best resolution video smaller or equal to: ' + quality)
        #Fetch the versions of the video with separate streams and the pre-merged, we'll pick the better of the two.
        tmpfile = os.path.splitext(target)[0]
        tmpfile_merge = tmpfile + '_downloaded_merged' + os.path.splitext(target)[1]
        tmpfile_best = tmpfile + '_downloaded_best' + os.path.splitext(target)[1]
        download_files(youtubeID, "bestvideo[height <=? " + quality[:-1] + "]+bestaudio", tmpfile_merge)
        download_files(youtubeID, "best[height <=? " + quality[:-1] + "]", tmpfile_best)
        # select better of the two, or raise error if neither available.
        tmpfile = compare_dimensions(tmpfile_merge,tmpfile_best)
        os.remove(target) #remove the copy of the source node
        os.rename(tmpfile, target)#replace the old target file
        return None, None
    finally:
        delete_video(youtube, id=youtubeID) #Always cleanup file uploaded to youtube

def suffix():
    return None

def operation():
    return {'name': 'SocialMedia',
            'category': 'Laundering',
            'description': 'Upload source to Youtube, download a processed version back as result.',
            'software': 'maskgen',
            'version': maskgen.__version__[0:3],
            'arguments': OrderedDict([
                ('max_resolution', {
                    'type': 'list',
                    'values': ['2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p'],
                    'defaultvalue': '2160p',
                    'description': 'Download the best available resolution at or below the target'
                }),
                ('type', {
                    'type':'list',
                    'values' : ['Facebook', 'Instagram', 'Youtube'],
                    'description':'Service',
                    'defaultvalue': 'Youtube'
                }),
                ('upload', {
                    'type': 'list',
                    'values': ['Mobile Device', 'Desktop'],
                    'description': 'How was the image uploaded?',
                    'defaultvalue': 'Desktop'
                }),
                ('download', {
                    'type': 'list',
                    'values': ['Mobile Device', 'Desktop'],
                    'description': 'How was the image downloaded?',
                    'defaultvalue': 'Desktop'
                })
            ]),
            'transitions': [
                'video.video'
            ]
            }