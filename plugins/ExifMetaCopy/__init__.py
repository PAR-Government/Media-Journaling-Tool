import os
from PIL import Image
import tempfile
from subprocess import call

def transform(img,target, **kwargs):
    donor = kwargs['donor']
    call(['exiftool', '-TagsFromFile',  donor[1],target])

def operation():
    return ['AntiForensicCopyExif','AntiForensicExif','Copy Image EXIF from donor','exiftool','10.23']
  
def args():
    return [('donor', None)]
