import cv2
import numpy as np
from PIL import Image 
from operator import mul
import math
from skimage.measure import compare_ssim
import warnings

def openImage(file):
   with open(file,"rb") as fp:
      im = Image.open(fp)
      im.load()
      return im

def alignShape(im,shape):
   x = min(shape[0],im.shape[0])
   y = min(shape[1],im.shape[1])
   z = np.zeros(shape)
   for d in range(min(shape[2],im.shape[2])):
      z[0:x,0:y,d] = im[0:x,0:y,d]
   return z

def alignChannels(rawimg1, rawimg2):
   img1 = np.asarray(rawimg1.convert('F'))
   img2 = np.asarray(rawimg2.convert('F'))
   return img1,img2

#   if (len(img1.shape)==2):
#    img1 = img1.reshape(img1.shape[0], img1.shape[1],1)##

#   if (len(img2.shape)==2):
#    img2 = img2.reshape(img2.shape[0], img2.shape[1],1)

#   if (img1.shape[2] == img2.shape[2]):
#       return img1.astype('uint8'), img2.astype('uint8')
#   thirdchannel = max(img1.shape[2],img2.shape[2])
#   z1 = np.ones((img1.shape[0],img1.shape[1],thirdchannel))*255
#   z2 = np.ones((img2.shape[0],img2.shape[1],thirdchannel))*255
#   for d in range(thirdchannel):
#       if (d < img1.shape[2]):
#         z1[:,:,d] = img1[:,:,d]
#       if (d < img2.shape[2]):
#         z2[:,:,d] = img2[:,:,d]
#   return z1.astype('uint8'), z2.astype('uint8')
    

def findBestMatch(big,small):
    if (np.any(np.asarray([(x[1]-x[0]) for x in zip(small.shape,big.shape)])<0)):
       return None
    result = cv2.matchTemplate(big, small, cv2.cv.CV_TM_SQDIFF_NORMED)
    mn,_,mnLoc,_ = cv2.minMaxLoc(result)
    tuple=(mnLoc[1],mnLoc[0],mnLoc[1]+small.shape[0],mnLoc[0]+small.shape[1])
    if (tuple[2] > big.shape[0] or tuple[3] > big.shape[1]):
      return None
    return tuple

def composeCropImageMask(img1,img2,seamAnalysis=True):
    tuple = findBestMatch(img1,img2)
    mask = None
    analysis={}
    if tuple is not None:
        dims = (0,img2.shape[0],0,img2.shape[1])
        
        diffIm = np.zeros(img1.shape).astype('float32')
        diffIm[tuple[0]:tuple[2],tuple[1]:tuple[3]]=img2
        pinned = np.where(np.array(dims)==np.array(tuple))[0]
        analysis = img_analytics(img1,diffIm)
        dst = np.abs(img1-diffIm)
        gray_image = np.zeros(img1.shape).astype('uint8')
        gray_image[dst>0.0001] = 255
        mask = gray_image
        if (len(pinned)>=2 and seamAnalysis):
           diffIm2 = np.copy(img1).astype(float)
           diffIm2[tuple[0]:tuple[2],tuple[1]:tuple[3]]=img2
           dst2 = np.abs(img1-diffIm2)
           gray_image2 = np.zeros(img1.shape).astype('uint8')
           gray_image2[dst2>0.0001] = 255
           mask = seamMask(gray_image2)
    else:
        mask = np.ones(img1.shape)*255
    return Image.fromarray(abs(255-mask).astype('uint8')),analysis

def colorPSNR(z1,z2):
    d = (z1-z2)**2
    sse = np.sum(d)
    mse=  float(sse)/float(reduce(lambda x, y: x*y, d.shape))
    return 0.0 if mse==0.0 else 20.0* math.log10(255.0/math.sqrt(mse))

def size_diff(z1,z2):
   return str((z1.shape[0]-z2.shape[0],z1.shape[1]-z2.shape[1]))

def img_analytics(z1,z2):
   with warnings.catch_warnings():
     warnings.simplefilter("ignore")
     return {'ssim':compare_ssim(z1,z2,multichannel=False),'psnr':colorPSNR(z1,z2),'shape change':size_diff(z1,z2)}

def diffMask(img1,img2,invert):
    dst = np.abs(img1-img2)
    gray_image = np.zeros(img1.shape).astype('uint8')
    gray_image[dst>0.0001] = 255
    analysis = img_analytics(img1,img2)
    return Image.fromarray(np.array(gray_image) if invert else (255-np.array(gray_image))),analysis

def createMask(img1, img2, invert, seamAnalysis=True):
    img1, img2 = alignChannels(img1,img2)
    if (sum(img1.shape) > sum(img2.shape)):
      return composeCropImageMask(img1,img2,seamAnalysis=seamAnalysis)
    if (sum(img1.shape) < sum(img2.shape)):
      mask = np.ones(img1.shape)*255
      return Image.fromarray(abs(255-mask).astype('uint8')),{}
    #rotation
    try:
      if (img1.shape != img2.shape):
        one = np.rot90(img2,1)
        one_diff,one_analysis = diffMask(img1,one,invert)
        three = np.rot90(img2,3)
        three_diff,three_analysis = diffMask(img1,three,invert)
        if abs(three_analysis['ssim']) > abs(one_analysis['ssim']):
           return three_diff,three_analysis
        else:
           return one_diff,one_analysis
      else:    
        return diffMask(img1,img2,invert)
    except ValueError as e:
      print 'Mask generation failure ' + e
      mask = np.ones(img1.shape)*255
      return Image.fromarray(abs(255-mask).astype('uint8')),{}

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

def imageResizeRelative(img,dim,otherIm):
   wmax=max(img.size[0],otherIm[0])
   hmax=max(img.size[1],otherIm[1])
   wpercent = float(dim[0])/float(wmax)
   hpercent = float(dim[1])/float(hmax)
   perc = min(wpercent,hpercent)
   wsize = int((float(img.size[0])*float(perc)))
   hsize = int((float(img.size[1])*float(perc)))
   return img.resize((wsize,hsize), Image.ANTIALIAS)

def imageResize(img,dim):
   return img.resize(dim, Image.ANTIALIAS).convert('RGBA')

def findNeighbors(paths,next):
   newpaths = list()
   s = set()
   for path in paths:
     x = path[len(path)-1]
     for i in np.intersect1d(np.array([x-1,x,x+1]),next):
        if (i not in s):
          newpaths.append(path + [i])
          s.add(i)
   return newpaths

def findVerticalSeam(mask):
  paths = list()
  for candidate in np.where(mask[0,:]>0)[0]:
     paths.append([candidate])
  for x in range(1,mask.shape[0]):
    paths = findNeighbors(paths,np.where(mask[x,:]>0)[0])
  return paths

def findHorizontalSeam(mask):
  paths = list()
  for candidate in np.where(mask[:,0]>0)[0]:
     paths.append([candidate])
  for y in range(1,mask.shape[1]):
    paths = findNeighbors(paths,np.where(mask[:,y]>0)[0])
  return paths

def seamMask(mask):
    seams = findVerticalSeam(mask)
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
      seams = findHorizontalSeam(mask)
      if (len(seams)==0):
         return mask
      first = seams[0]
      #should compare to seams[-1]
      mask = np.zeros(mask.shape)
      for i in range(len(first)): 
        mask[first[i],i] = 255
      return mask
    
