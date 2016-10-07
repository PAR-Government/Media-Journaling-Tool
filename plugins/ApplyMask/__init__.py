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
    return True,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['SelectRegion','Select','Apply a mask to create an alpha channel','OpenCV','2.4.13']

def args():
  return [('inputmaskname',None,'Mask to set alpha channel to 0')]

