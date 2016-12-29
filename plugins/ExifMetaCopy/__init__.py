from subprocess import call
import shutil
import maskgen.exif
from PIL import Image

def emc_update_size(size,imageFile):
    width, height = size
    maskgen.exif.runexif(['-P', '-q', '-m', '-ExifImageWidth=' + str(width),
                                            '-ImageWidth=' + str(width),
                                            '-ExifImageHeight=' + str(height),
                                            '-ImageHeight=' + str(height),
                                            imageFile])

def update_modifytime(imageFile):
    createtime = maskgen.exif.getexif(imageFile, args=['-args', '-System:FileCreateDate'], separator='=')
    maskgen.exif.runexif(['-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], imageFile])

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor, '-all:all', '-unsafe', target])
    if target.lower().endswith(('.jpg', '.jpeg')):
        emc_update_size(img.size, target)
    update_modifytime(target)
    maskgen.exif.runexif(['-P', '-q', '-m', '-XMPToolkit=', target])



    return None,None

def suffix():
    return None

def operation():
    return {'name':'AntiForensicCopyExif',
            'category':'AntiForensic',
            'description':'Copy Image metadata from donor',
            'software':'exiftool',
            'version':'10.23',
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultValue': None,
                    'description': 'Image/video with donor metadata.'
                    }
                },
            'transitions':[
                'image.image',
                'video.video'
                ]
            }
