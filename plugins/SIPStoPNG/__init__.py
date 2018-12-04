from subprocess import call, Popen, PIPE
"""
Save te image as PNG using SIPS
"""

def sips_version():
      p = Popen(['sips','-h'],stdout=PIPE)
      stdout = p.communicate()[0]
      if p.returncode != 0:
          return '1.0'
      return stdout.splitlines()[0].split(' ')[1]

def transform(img, source, target, **kwargs):

    if call(['sips',
               '-s',
               'format',
               'png',
               '-s',
               'formatOptions',
               '100',
                source,
                "--out",
                target]):
        raise EnvironmentError("Cannot run sips.  Are you on a Mac?")
    return {'Image Rotated':'no'}, None


def operation():
    return {'name': 'OutputPng',
            'category': 'Output',
            'description': 'Mac specific: Save an image as .png from .heic',
            'software': 'sips',
            'version': sips_version(),
            'arguments': {
                'Image Rotated': {
                    'type': 'yesno',
                    'defaultvalue': 'no',
                    'description': 'Rotate image according to EXIF'
                }
            },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return '.png'
