import cv2
from maskgen import image_wrap
import numpy
from maskgen import tool_set
import os
import tempfile
import subprocess
import logging

def transform(img,source,target,**kwargs):
    source_im = numpy.asarray(img)
    mask = tool_set.openImageFile(kwargs['inputmaskname']).to_mask()
    mask_array = numpy.asarray(mask)
    black_image = source_im.copy()
    new_im = source_im.copy()
    black_image[:,:] = (0,0,0)
    cv2.bitwise_and( source_im, black_image, new_im, mask_array)
    save_im = image_wrap.ImageWrapper(new_im)
    maskfd,maskfile = tempfile.mkstemp(suffix='.png')
    os.close(maskfd)
    save_im.save(maskfile)
    target_im = None
    try:
        lqrCommandLine = ['gmic',maskfile,'-gimp_inpaint_patchmatch',' 0,9,10,5,1,0,0,0,0,3,0','-o',target]
        pcommand = subprocess.Popen(" ".join(lqrCommandLine), shell=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, stderr = pcommand.communicate()
        if pcommand.returncode == 0:
            target_im = numpy.asarray(tool_set.openImageFile(target))
        else:
            logging.getLogger('maskgen').error('Failure of Remove (inpainting) plugin {}'.format(str(stderr)))
    except Exception as e:
        logging.getLogger('maskgen').error( 'Failure of Remove (inpainting) plugin {}'.format(str(e)))
    os.remove(maskfile)
    if target_im is None:
        target_im = cv2.inpaint(source_im, mask_array, 3, cv2.INPAINT_TELEA)
    save_im = image_wrap.ImageWrapper(target_im)
    save_im.save(target)
    return {'purpose':'remove'},None

def operation():
  return {
          'category': 'Paste',
          'name': 'ContentAwareFill',
          'description':'Use gmic, if installed, to do inpaiting, otherwise use cv2 ',
          'software':'gmic',
          'version':'2.0.0',
          'arguments':{
              'inputmaskname':{
                  'type':'imagefile',
                  'defaultvalue':None,
                  'description':'Mask image where black pixels identify region to remove'
              },
	          'removetype':{
                  'type': 'int[1:3]',
                  'defaultvalue':1,
                  'description':'Inpainting operation to use 1=Openv'
              }},
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None
