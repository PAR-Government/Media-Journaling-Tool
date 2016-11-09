import cv2
from PIL import Image
import numpy

def transform(img,source,target,**kwargs):
    rgba = img.convert('RGBA')
    inputmask = kwargs['donor']
    donor = inputmask[0].convert('RGBA')
    if donor.size != rgba.size:
      donor = donor.resize(rgba.size, Image.ANTIALIAS)
    rgba.paste(donor,(0,0),donor)
    rgba.save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['PasteSplice','Paste','Overlay image','OpenCV','2.4.13']

def args():
  return [('donor',None,'Image to overlay')]

def suffix():
    return None