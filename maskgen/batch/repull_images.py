import argparse
import os
import maskgen.scenario_model
from maskgen.tool_set import *
from maskgen import video_tools
import tempfile
from maskgen.scenario_model import ImageProjectModel
from maskgen.image_graph import extract_archive
from maskgen.graph_rules import processProjectProperties
from maskgen.batch import BatchProcessor, pick_projects
import hashlib
import shutil
import sys
import csv
from urllib import urlretrieve, FancyURLopener
class MyOpener(FancyURLopener):

    def __init__(self,*args,**kwargs):
        FancyURLopener.__init__(self,*args,**kwargs)

    def prompt_user_passwd(self,h,r):
        return ('erobertson','theyeje6')

prefLoader = MaskGenLoader()


sign_url = "https://medifor.rankone.io/api/sign/"

def download(file_name, directory, prefix='images'):
    import requests
    response = requests.post('https://medifor.rankone.io/api/login/',
                             {'username': 'erobertson', 'password': 'theyeje6'})
    if response.status_code == requests.codes.ok:
        token = response.json()['key']
    #token = prefLoader.get_key('apitoken')
    headers = {"Content-Type": "application/json", "Authorization": "Token %s" % token}

    response  = requests.get(sign_url + "?file=%s&prefix=%s" % (file_name, prefix), headers=headers)
    if response.status_code == requests.codes.ok:
         url = response.json()["url"]
    else:
         url = "https://s3.amazonaws.com/medifor/%s/%s" % (prefix, file_name)

    downloadFilename = os.path.join(directory, file_name)
    if os.path.exists(downloadFilename):
        os.remove(downloadFilename)
    urlretrieve(url, downloadFilename)

def get_image(directory, file, url):
    try:
        #response = requests.get(url + "?file=%s&prefix=%s" % (file_name, prefix), headers=headers)
        #if response.status_code == requests.codes.ok:
        #    newurl = response.json()["url"]
        #opener = MyOpener()
        #opener.retrieve(url,file)
        download(file,directory)
    except Exception as e:
        logging.getLogger('maskgen').critical("Cannot reach external service " + url)
        logging.getLogger('maskgen').error(str(e))
    return url

def perform_update(project,images, s3dir):
    scModel = maskgen.scenario_model.ImageProjectModel(project)
    for image in images:
        get_image(scModel.get_dir(),image[1],image[0])
    for node_id in scModel.getGraph().get_nodes():
        if len(scModel.getGraph().predecessors(node_id)) == 0:
            for succ in scModel.getGraph().successors(node_id):
                #edge  = scModel.getGraph().get_edge(node_id,succ)
                scModel.reproduceMask(edge_id=(node_id,succ))
    scModel.exporttos3(s3dir)

def fetchfromS3(dir, location, file):
    import boto3
    BUCKET = location.split('/')[0].strip()
    DIR = location[location.find('/') + 1:].strip() +'/'
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(BUCKET)
    my_bucket.download_file(DIR + file, os.path.join(dir, file))

def processProject(file_to_process):
    import thread
    """

    :param args:
    :param functions:
    :param file_to_process:
    :return:
    @type file_to_process : str
    """
    dir = '/tmp/foo/' + str(thread.get_ident())
    print dir
    os.mkdir(dir)
    try:
        fetchfromS3(dir, 'medifor/par/journal/ingested',file_to_process[0]+'.tgz')
        extract_archive(os.path.join(dir, file_to_process[0]+'.tgz'), dir)
        for project in pick_projects(dir):
            perform_update(project, file_to_process[1],'medifor/par/journal/staging')
    finally:
        shutil.rmtree(dir)
    return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f',  '--file', required=True, help='File of projects')
    parser.add_argument('-t', '--threads', required=False, default=1, help='Download folder')
    parser.add_argument('-cf', '--completefile', required=True, help='Projects to Completed')
    args = parser.parse_args()


    with open(args.file, 'r') as input_file:
        csvreader = csv.reader(input_file, delimiter=',')
        files_to_process = [row for row in csvreader]

    journals = {}
    for fp in files_to_process:
        if fp[1] not in journals:
            journals[fp[1]] = []
        journals[fp[1]].append((fp[3],fp[4]))

    journals = [(j,i) for j,i in journals.iteritems()]

    processor = BatchProcessor(args.completefile,journals,threads=int(args.threads))
    processor.process(processProject)

if __name__ == '__main__':
    main()
