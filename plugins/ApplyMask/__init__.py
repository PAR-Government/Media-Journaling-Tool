import PIL
from PIL import Image
import numpy

def transform(img,source,target,**kwargs):
    rgba = img.convert('RGBA')
    inputmask = Image.open(kwargs['inputmaskname'])
    if inputmask.size != rgba.size:
      rgba = rgba.resize(inputmask.size, Image.ANTIALIAS)
    cv_image = numpy.asarray(rgba)
    mask = numpy.array(inputmask)
    bmask = mask>0
    cv_image[:,:,3][bmask]=0
    Image.fromarray(cv_image,'RGBA').save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return {'name':'SelectRegion',
          'category':'Select',
          'description':'Apply a mask to create an alpha channel',
          'software':'PIL',
          'version':PIL.__version__,
          'arguments':{
              'inputmaskname':{
                  'type':'inputmaskname',
                  'defaultvalue':None,
                  'description':'Mask to set alpha channel to 0'
              }
          },
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None