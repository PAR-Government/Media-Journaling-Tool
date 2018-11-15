'''
Plugin to modify date and time in exif
Plugin adapted from ExifGPSChange\__init__.py
'''

from maskgen.exif import getexif
from maskgen.ffmpeg_api import run_ffmpeg, get_ffmpeg_version
import datetime
import random


def get_defaults(source):
    try:
        exifdata = getexif(source)
        date, time = exifdata['Create Date'].split(" ")
        date = "-".join(date.split(":"))
    except KeyError:
        time = str(datetime.datetime.utcnow().strftime("%H:%M:%S"))
        date = str(datetime.datetime.utcnow().date())
    except TypeError:
        return False, False

    return date, time


def modify_datetime(source, target, date, time):
    dt = " ".join([date, time + "Z"])
    # ffmpeg -i input.mp4 -c copy -map 0 -metadata creation_time="2013-06-21 12:00:00" output.mp4

    run_ffmpeg(['-y', '-i', source, '-c', 'copy', '-map', '0', '-metadata', 'creation_time=' + dt, target])
    return


def random_date(mindate, maxdate):
    try:
        startdate = datetime.datetime.strptime(mindate, "%m-%d-%Y").date()
        enddate = datetime.datetime.strptime(maxdate, "%m-%d-%Y").date()
    except TypeError:
        return False

    if startdate > enddate:
        return False

    dif = enddate - startdate

    rand_change = random.randint(0, dif.days)

    date = datetime.datetime.fromordinal(startdate.toordinal()+rand_change).strftime("%Y-%m-%d")

    return str(date)


def random_time(mintime, maxtime):
    try:
        starttime = datetime.datetime.strptime(mintime, "%H:%M:%S")
        endtime = datetime.datetime.strptime(maxtime, "%H:%M:%S")
    except TypeError:
        return False

    if starttime > endtime:
        endtime += datetime.timedelta(days=1)

    dif = (endtime - starttime)

    rand_change = random.randint(0, dif.seconds)

    start_seconds = (starttime.time().second + 60 * starttime.time().minute + (60 * 60 * starttime.hour))

    time = datetime.datetime.utcfromtimestamp(rand_change + start_seconds).time()

    return str(time)


def transform(img, source, target, **kwargs):
    mintime = kwargs['Time Minimum'] if 'Time Minimum' in kwargs else None
    maxtime = kwargs['Time Maximum'] if 'Time Maximum' in kwargs else None
    mindate = kwargs['Date Minimum'] if 'Date Minimum' in kwargs else None
    maxdate = kwargs['Date Maximum'] if 'Date Maximum' in kwargs else None

    date, time = get_defaults(source)

    if not (date and time):
        return None, "Invalid Arguments"

    if mintime and maxtime:
        randtime = random_time(mintime, maxtime)
        time = randtime if randtime else time
    if mindate and maxdate:
        randdate = random_date(mindate, maxdate)
        date = randdate if randdate else date
    else:
        return None, "Invalid field entries."

    modify_datetime(source, target, date, time)

    return None, "Error changing time" if not time and date else "Error changing date" if time and not date else None \
        if time and date else "Error changing time and date"


def suffix():
    return None


def operation():
    return {'name': 'AntiForensicEditExif',
            'category': 'AntiForensic',
            'description': 'Set Date and Time of Video Capture',
            'software': 'ffmpeg',
            'version': get_ffmpeg_version(),
            'arguments': {
                'Date Minimum': {
                    'type': 'String',
                    'defaultValue': None,
                    'description': 'Minimum date to change to in the format MM-DD-YYYY. (ex. 01-01-2000)'
                },
                'Date Maximum': {
                    'type': 'String',
                    'defaultValue': None,
                    'description': 'Maximum date to change to in the format MM-DD-YYYY. (ex. 12-31-2017)'
                },
                'Time Minimum': {
                    'type': 'Time',
                    'defaultValue': None,
                    'description': 'Minimum time to change to in the format HH:MM:SS. (ex. 00:00:00)'
                },
                'Time Maximum': {
                    'type': 'Time',
                    'defaultValue': None,
                    'description': 'Maximum time to change to in the format HH:MM:SS. (ex. 23:59:59)'
                }
            },
            'transitions': [
                'video.video'
            ]
            }
