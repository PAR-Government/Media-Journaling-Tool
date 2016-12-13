from subprocess import call
import shutil
import maskgen.exif
from PIL import Image

def emc_update_size(size,imageFile):
    width, height = size
    maskgen.exif.runexif(['exiftool', '-P', '-q', '-m', '-ExifImageWidth=' + str(width),
                                                        '-ImageWidth=' + str(width),
                                                        '-ExifImageHeight=' + str(height),
                                                        '-ImageHeight=' + str(height),
                                                        imageFile])

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    shutil.copy2(source, target)
    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target])
    if target.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff')):
        maskgen.exif.runexif(['exiftool', '-P', '-q', '-m', '-TagsFromFile',  donor[1], '-all:all', '-unsafe', target])
        emc_update_size(img.size, target)
    else:
        maskgen.exif.runexif(['exiftool', '-P', '-q', '-m', '-TagsFromFile', donor[1], '-all:all', target])
        maskgen.exif.runexif(['exiftool', '-P', '-q', '-m', '-XMPToolkit=', target])

    return None,None

def suffix():
    return None

def operation():
    return ['AntiForensicCopyExif','AntiForensicExif','Copy Image metadata from donor','exiftool','10.23']
  
def args():
    return [('donor', None, 'Image/video with donor metadata')]
