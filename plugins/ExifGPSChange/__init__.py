import os
from maskgen.exif import *


def get_new_position(start, range=0, degrees_of_change=3):
    import random
    if start is None:
        startdegrees = random.randint(1, range - 1)
    else:
        parts = start.split()
        startdegrees = int(float(parts[0]))
    return '{} {:} {:.2f}'.format((random.randint(-degrees_of_change, degrees_of_change) + startdegrees) % (range - 1),
                                  random.randint(1, 59),
                                  random.random() * 60)


def get_same_positon(start, range=0):
    if start is None:
        return get_new_position(start, range=range)
    return start


def modify_value(source, target, tag, name, modifier):
    result = getexif(source, args=[tag])
    newvalue = modifier(result[name] if name in result else None)
    if newvalue is None:
        newvalue = get_new_position(None)
    return runexif(['-overwrite_original', '-P', '-q', '-m',
                    tag + '=' + newvalue, target], fix=False)


def relocate(source, target, degrees_of_change):
    import functools
    latfunc = functools.partial(get_new_position, range=90, degrees_of_change=degrees_of_change)
    lonfunc = functools.partial(get_new_position, range=180, degrees_of_change=degrees_of_change)
    ok = False
    ok |= modify_value(source, target, '-xmp:gpslatitude', 'GPS Latitude', latfunc)
    ok |= modify_value(source, target, '-exif:gpslatitude', 'GPS Latitude', latfunc)
    ok |= modify_value(source, target, '-exif:gpslongitude', 'GPS Longitude', lonfunc)
    ok |= modify_value(source, target, '-xmp:gpslongitude', 'GPS Longitude', lonfunc)
    return ok


def relocate_to(donor, target):
    import functools
    ok = False
    latfunc = functools.partial(get_same_positon, range=90, )
    lonfunc = functools.partial(get_same_positon, range=180)
    ok |= modify_value(donor, target, '-xmp:gpslatitude', 'GPS Latitude', latfunc)
    ok |= modify_value(donor, target, '-exif:gpslatitude', 'GPS Latitude', latfunc)
    ok |= modify_value(donor, target, '-exif:gpslongitude', 'GPS Longitude', lonfunc)
    ok |= modify_value(donor, target, '-xmp:gpslongitude', 'GPS Longitude', lonfunc)
    return ok


def transform(img, source, target, **kwargs):
    degrees_of_change = int(kwargs['degrees of change']) if 'degrees of change' in kwargs else 3
    if 'donor' in kwargs and kwargs['donor'] is not None and os.path.exists(kwargs['donor']):
        donor = kwargs['donor']
        ok = relocate_to(donor, target)
    else:
        ok = relocate(source, target, degrees_of_change)
    if ok:
        runexif(['-overwrite_original', '-P', '-q', '-m', '-XMPToolkit=', target])
    return None, 'Failed' if not ok else None


def suffix():
    return None


def operation():
    return {'name': 'AntiForensicEditExif::GPSChange',
            'category': 'AntiForensic',
            'description': 'Set GPS Location',
            'software': 'exiftool',
            'version': get_version(),
            'arguments': {
                'donor': {
                    'type': 'donor',
                    'defaultValue': None,
                    'description': 'Image/video with donor metadata.'
                },
                'degrees of change': {
                    'type': 'int',
                    'defaultValue': 3,
                    'description': 'Positive/negative range of change.'
                }
            },
            'transitions': [
                'image.image',
                'video.video'
            ]
            }
