from maskgen.exif import runexif, get_version


def transform(img, source, target, **kwargs):
    lat = kwargs["latitude"]
    lon = kwargs["longitude"]
    exifcmd = ["-exif:gpslatitude=" + lat, "-xmp:gpslatitude=" + lat,
               "-exif:gpslongitude=" + lon, "-xmp:gpslongitude=" + lon,
               target]
    ok = runexif(exifcmd)
    if ok:
        runexif(['-overwrite_original', '-P', '-q', '-m', '-XMPToolkit=', target])

    return None, None


def suffix():
    return None


def operation():
    return {'name': 'AntiForensicEditExif::GPSChange',
            'category': 'AntiForensic',
            'description': 'Set GPS Location',
            'software': 'exiftool',
            'version': get_version(),
            'arguments': {
                'latitude': {
                    'type': 'float[-90:90]',
                    'description': 'Desired latitude value'
                },
                'longitude': {
                    'type': 'float[-180:180]',
                    'description': 'Desired longitude value'
                }
            },
            'transitions': [
                'image.image',
                'video.video'
            ]
            }
