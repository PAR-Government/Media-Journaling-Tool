from PIL import Image
import numpy
import cv2
import random
from maskgen.image_wrap import ImageWrapper
from maskgen import tool_set,image_wrap
from skimage import data, io, segmentation, color
from skimage.future import graph

def transform(img,source,target,**kwargs):
    img_to_paste = image_wrap.ImageWrapper(tool_set.openImageFile(kwargs['imagefile']))
    gray = numpy.asarray( img.convert('L')).astype('uint8')
    labels1 = segmentation.slic(gray, compactness=0.1, n_segments=400)
    g = graph.rag_mean_color(img, labels1, mode='similarity')
    labels2 = graph.cut_normalized(labels1, g)
    
    ImageWrapper(labels2).save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['PasteSplice','Paste','Apply a mask to create an alpha channel','OpenCV','2.4.13']

def args():
  return [('inputimagename',None,'Mask to set alpha channel to 0')]

def suffix():
    return None