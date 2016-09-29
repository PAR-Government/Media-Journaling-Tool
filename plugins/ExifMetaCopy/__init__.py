from subprocess import call
from PIL import Image

def update_size(imageFile):
    with Image.open(imageFile) as im:
        width, height = im.size
    call(['exiftool', '-P', '-q', '-m', '-ExifImageWidth=' + str(width),
                                        '-ImageWidth=' + str(width),
                                        '-ExifImageHeight=' + str(height),
                                        '-ImageHeight=' + str(height),
                                        imageFile])

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    call(['-overwrite_original', '-q', '-all=', target])
    call(['exiftool', '-P', '-q', '-m', '-TagsFromFile',  donor[1], '-all:all', '-unsafe', target])
    call(['exiftool', '-P', '-q', '-m', '-XMPToolkit=', target])
    update_size(target)
    return False,None

def suffix():
    return '.jpg'

def operation():
    return ['AntiForensicCopyExif','AntiForensicExif','Copy Image EXIF from donor','exiftool','10.23']
  
def args():
    return [('donor', None, 'JPEG with donor EXIF')]
