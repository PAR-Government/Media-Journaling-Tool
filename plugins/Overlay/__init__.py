import cv2
from PIL import Image
import numpy
from maskgen.image_wrap import ImageWrapper,openImageFile

def transform(img,source,target,**kwargs):
    rgba = img.convert('RGBA')
    donor_img_file = kwargs['donor']
    inputmask = openImageFile(donor_img_file)
    donor = inputmask.convert('RGBA')
    if donor.size != rgba.size:
      donor = donor.resize(rgba.size, Image.ANTIALIAS)
    rgba.paste(donor,(0,0),donor)
    rgba.save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return {'name':'PasteSplice',
          'category':'Paste',
          'description':'Overlay image',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments':{
              'donor':{
                  'type':'donor',
                  'defaultvalue':None,
                  'description':'Image to overlay'
              }
          },
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None