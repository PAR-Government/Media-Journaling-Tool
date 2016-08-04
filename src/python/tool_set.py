import cv2
import numpy as np
from PIL import Image ,ImageOps
from operator import mul
import math
from skimage.measure import compare_ssim
import warnings
from scipy import ndimage
from scipy import misc


"""  These functions are designed to support mask generation.
"""

def imageResize(img,dim):
   return img.resize(dim, Image.ANTIALIAS).convert('RGBA')

def imageResizeRelative(img,dim,otherIm):
   wmax=max(img.size[0],otherIm[0])
   hmax=max(img.size[1],otherIm[1])
   wpercent = float(dim[0])/float(wmax)
   hpercent = float(dim[1])/float(hmax)
   perc = min(wpercent,hpercent)
   wsize = int((float(img.size[0])*float(perc)))
   hsize = int((float(img.size[1])*float(perc)))
   return img.resize((wsize,hsize), Image.ANTIALIAS)


def openImage(file):
   with open(file,"rb") as fp:
      im = Image.open(fp)
      im.load()
      return im

def createMask(img1, img2, invert, seamAnalysis=False,arguments={}):
      mask,analysis = __composeMask(img1,img2,invert,seamAnalysis=seamAnalysis,arguments=arguments)
      analysis['shape change'] = __sizeDiff(img1,img2)
      return Image.fromarray(mask),analysis

def __composeMask(img1, img2, invert, seamAnalysis=False,arguments={}):
    img1, img2 = __alignChannels(img1,img2)
    # rotate image two if possible to compare back to image one.
    # The mask is not perfect.
    rotation = float(arguments['rotation']) if 'rotation' in arguments else 0.0
    if abs(rotation) > 0.0001:
       return  __compareRotatedImage(rotation, img1, img2,invert,arguments)
    if (sum(img1.shape) > sum(img2.shape)):
      return __composeCropImageMask(img1,img2,seamAnalysis=seamAnalysis)
    if (sum(img1.shape) < sum(img2.shape)):
      return __composeExpandImageMask(img1,img2)
    try:
      if img1.shape == img2.shape:
       return __diffMask(img1,img2,invert)
    except ValueError as e:
      print 'Mask generation failure ' + e
    mask = np.ones(img1.shape)*255
    return abs(255-mask).astype('uint8'),{}

def __alignShape(im,shape):
   x = min(shape[0],im.shape[0])
   y = min(shape[1],im.shape[1])
   z = np.zeros(shape)
   for d in range(min(shape[2],im.shape[2])):
      z[0:x,0:y,d] = im[0:x,0:y,d]
   return z

def __resize(img,dimensions):
   if img.shape[0] != dimensions[0]:
      diff = abs(img.shape[0] - dimensions[0])
      img = np.concatenate((np.zeros((diff/2,img.shape[1])),img),axis=0)
      img = np.concatenate((img,np.zeros((diff-(diff/2),img.shape[1]))),axis=0)
   if img.shape[1] != dimensions[1]:
      diff = abs(img.shape[1] - dimensions[1])
      img = np.concatenate((np.zeros((img.shape[0],diff/2)),img),axis=1)
      img = np.concatenate((img,np.zeros((img.shape[0],diff-(diff/2)))),axis=1)
   return img


def __rotateImage(rotation, img,expectedDims,cval=0):
   rotNorm = int(rotation/90) if (rotation % 90) == 0 else None
   rotNorm = rotNorm if rotNorm is None or rotNorm >= 0 else (4+rotNorm)
   npRotation = rotNorm is not None and img.shape == (expectedDims[1],expectedDims[0])
   if npRotation:
       res = np.rot90(img,rotNorm)
   else:
       res = ndimage.interpolation.rotate(img,rotation,cval=cval,reshape=(img.shape != expectedDims))
   return res

def __compareRotatedImage(rotation, img1,img2, invert,arguments):
   res = __rotateImage(rotation,img1,img2.shape,cval=img2[0,0])
   mask,analysis = __composeExpandImageMask(res,img2) if res.shape != img2.shape else __diffMask(res,img2,invert)
   res = __rotateImage(-rotation,mask,img1.shape,cval=255)
   return res,analysis

#      res = __resize(mask,(max(img2.shape[0],img1.shape[0]), max(img2.shape[1],img1.shape[1])))
#      res[res<0.00001] = 0
#      res[res>0] = 255
#      # now crop out the rotation difference, to make sure the original image is not modified
#      if img1.shape != res.shape:
#        diff = (res.shape[0]-img1.shape[0], res.shape[1]-img1.shape[1])
#        diff = (diff[0] if diff[0] > 0 else 0, diff[1] if diff[1] > 0 else 0)
#        res = res[diff[0]/2:res.shape[0]-((diff[0]/2) -diff[0]),diff[1]/2:res.shape[1]-((diff[1]/2) - diff[1])]


def __alignChannels(rawimg1, rawimg2):
   f1 = np.asarray(rawimg1)
   f2 = np.asarray(rawimg2)
   img1 = np.asarray(rawimg1.convert('F'))
   img2 = np.asarray(rawimg2.convert('F'))
   if len(f1.shape) == len(f2.shape) and len(f1.shape)==3:
      #this is messed up.  The conversion does not compare alpha-channels and we to see of one the images
      #had added an alpha
      if f2.shape[2] != f1.shape[2]:
        if f2.shape[2] == 4:
           img2 = img2 * f2[:,:,3].astype('float32')/255.0
        elif f1.shape[2] == 4:
           img1 = img1 * f1[:,:,3].astype('float32')/255.0
   return img1,img2

def __findBestMatch(big,small):
    """ Return a tuple describing the bounding box (xl,xh,yl,yh) with the most
        likely match to the small image.
    """
    if (np.any(np.asarray([(x[1]-x[0]) for x in zip(small.shape,big.shape)])<0)):
       return None
    result = cv2.matchTemplate(big, small, cv2.cv.CV_TM_SQDIFF_NORMED)
    mn,_,mnLoc,_ = cv2.minMaxLoc(result)
    tuple=(mnLoc[1],mnLoc[0],mnLoc[1]+small.shape[0],mnLoc[0]+small.shape[1])
    if (tuple[2] > big.shape[0] or tuple[3] > big.shape[1]):
      return None
    return tuple

def __composeCropImageMask(img1,img2,seamAnalysis=False):
    """ Return a masking where img1 is bigger than img2 and
        img2 is likely a crop of img1.
    """
    tuple = __findBestMatch(img1,img2)
    mask = None
    analysis={}
    analysis['location']='(0,0)'
    if tuple is not None:
        dims = (0,img2.shape[0],0,img2.shape[1])
        analysis['location'] = str((tuple[0],tuple[1]))
        diffIm = np.zeros(img1.shape).astype('float32')
        diffIm[tuple[0]:tuple[2],tuple[1]:tuple[3]]=img2
        pinned = np.where(np.array(dims)==np.array(tuple))[0]
        analysis = img_analytics(img1,diffIm)
        dst = np.abs(img1-diffIm)
        gray_image = np.zeros(img1.shape).astype('uint8')
        gray_image[dst>0.0001] = 255
        mask = gray_image
        if (len(pinned)>=2 and seamAnalysis):
           diffIm2 = np.copy(img1).astype('float32')
           diffIm2[tuple[0]:tuple[2],tuple[1]:tuple[3]]=img2
           dst2 = np.abs(img1-diffIm2)
           gray_image2 = np.zeros(img1.shape).astype('uint8')
           gray_image2[dst2>0.0001] = 255
           mask = __seamMask(gray_image2)
    else:
        mask = np.ones(img1.shape)*255
    return abs(255-mask).astype('uint8'),analysis

def __composeExpandImageMask(img1,img2):
    """ Return a masking where img1 is smaller than img2 and
        img2 contains img1.
    """
    tuple = __findBestMatch(img2,img1)
    mask = None
    analysis={}
    if tuple is not None:
        diffIm = img2[tuple[0]:tuple[2],tuple[1]:tuple[3]]
        analysis = img_analytics(img1,diffIm)
        dst = np.abs(img1-diffIm)
        gray_image = np.zeros(img1.shape).astype('uint8')
        gray_image[dst>0.0001] = 255
        mask = gray_image
    else:
        mask = np.ones(img1.shape)*255
    return abs(255-mask).astype('uint8'),analysis


def __colorPSNR(z1,z2):
    d = (z1-z2)**2
    sse = np.sum(d)
    mse=  float(sse)/float(reduce(lambda x, y: x*y, d.shape))
    return 0.0 if mse==0.0 else 20.0* math.log10(255.0/math.sqrt(mse))

def __sizeDiff(z1,z2):
   """
      z1 and z2 are expected to be PIL images
   """
   # size is inverted due to Image's opposite of numpy arrays
   return str((z2.size[1]-z1.size[1],z2.size[0]-z1.size[0]))

def invertMask(mask):
    return ImageOps.invert(mask)

def convertToMask(im):
    """
      Takes an image and produce a mask where all black areas are white
    """
    imGray = im.convert('L')
    imA = np.asarray(im)
    imGrayA = np.asarray(imGray)
    gray_image = np.ones(imGrayA.shape).astype('uint8')
    gray_image[imGrayA<255] = 0
    gray_image = gray_image * 255
    if imA.shape[2] == 4:
      gray_image[imA[:,:,3]==0]=255
    return Image.fromarray(gray_image)

def __checkInterpolation(val):
   validVals = ['nearest', 'lanczos', 'bilinear', 'bicubic' or 'cubic']
   return val if val in validVals else 'nearest'

def alterMask(compositeMask,rotation=0.0, sizeChange=(0,0),interpolation='nearest',location=(0,0)):
    res = compositeMask
    if abs(rotation) > 0.001:
       res = __rotateImage(rotation,res,(compositeMask[0]+sizeChange[0],compositeMask[1]+sizeChange[1]),cval=255)
    if location != (0,0):
      sizeChange = (-location[0],-location[1]) if sizeChange == (0,0) else sizeChange
    expectedSize = (res.shape[0] + sizeChange[0],res.shape[1] + sizeChange[1])
    if location != (0,0):
      upperBound = (res.shape[0] + (sizeChange[0]/2),res.shape[1] + (sizeChange[1]/2))
      res = res[location[0]:upperBound[0], location[1]:upperBound[1]]
    if expectedSize != res.shape:
      try:
         res = misc.imresize(res,expectedSize,interp=__checkInterpolation(interpolation))
      except KeyError:   
         res = misc.imresize(res,expectedSize,interp='nearest')
    return res

def mergeMask(compositeMask, newMask):
   if compositeMask.shape != newMask.shape:
      compositeMask = misc.imresize(compositeMask,newMask.shape,interp='nearest')
   else:
      compositeMask = np.copy(compositeMask)
   compositeMask[newMask==0] = 0
   return compositeMask

def img_analytics(z1,z2):
   with warnings.catch_warnings():
     warnings.simplefilter("ignore")
     return {'ssim':compare_ssim(z1,z2,multichannel=False),'psnr':__colorPSNR(z1,z2)}

def __diffMask(img1,img2,invert):
    dst = np.abs(img1-img2)
    gray_image = np.zeros(img1.shape).astype('uint8')
    gray_image[dst>0.0001] = 255
    analysis = img_analytics(img1,img2)
    return (np.array(gray_image) if invert else (255-np.array(gray_image))),analysis

def fixTransparency(img):
   if img.mode.find('A')<0:
      return img
   xx = np.asarray(img)
   perc = xx[:,:,3].astype(float)/float(255)
   xx.flags['WRITEABLE'] = True
   for d in range(3):
     xx[:,:,d] = xx[:,:,d]*perc
   xx[:,:,3]=np.ones((xx.shape[0], xx.shape[1]))*255
   return Image.fromarray(xx)


def __findNeighbors(paths,next):
   newpaths = list()
   s = set()
   for path in paths:
     x = path[len(path)-1]
     for i in np.intersect1d(np.array([x-1,x,x+1]),next):
        if (i not in s):
          newpaths.append(path + [i])
          s.add(i)
   return newpaths

def __findVerticalSeam(mask):
  paths = list()
  for candidate in np.where(mask[0,:]>0)[0]:
     paths.append([candidate])
  for x in range(1,mask.shape[0]):
    paths = __findNeighbors(paths,np.where(mask[x,:]>0)[0])
  return paths

def __findHorizontalSeam(mask):
  paths = list()
  for candidate in np.where(mask[:,0]>0)[0]:
     paths.append([candidate])
  for y in range(1,mask.shape[1]):
    paths = __findNeighbors(paths,np.where(mask[:,y]>0)[0])
  return paths

def __seamMask(mask):
    seams = __findVerticalSeam(mask)
    if (len(seams)>0):
      first = seams[0]
      #should compare to seams[-1].  this would be accomplished by
      # looking at the region size of the seam. We want one of the first or last seam that is most
      # centered
      mask = np.zeros(mask.shape)
      for i in range(len(first)): 
        mask[i,first[i]] = 255
      return mask
    else:
      seams = __findHorizontalSeam(mask)
      if (len(seams)==0):
         return mask
      first = seams[0]
      #should compare to seams[-1]
      mask = np.zeros(mask.shape)
      for i in range(len(first)): 
        mask[first[i],i] = 255
      return mask
    
