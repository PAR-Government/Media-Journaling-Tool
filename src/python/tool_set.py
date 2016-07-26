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

def alignChannels(img1, img2):
   if (len(img1.shape)==2):
    img1 = img1.reshape(img1.shape[0], img1.shape[1],1)

   if (len(img2.shape)==2):
    img2 = img2.reshape(img2.shape[0], img2.shape[1],1)

   if (img1.shape[2] == img2.shape[2]):
       return img1.astype('uint8'), img2.astype('uint8')
   thirdchannel = max(img1.shape[2],img2.shape[2])
   z1 = np.ones((img1.shape[0],img1.shape[1],thirdchannel))*255
   z2 = np.ones((img2.shape[0],img2.shape[1],thirdchannel))*255
   for d in range(thirdchannel):
       if (d < img1.shape[2]):
         z1[:,:,d] = img1[:,:,d]
       if (d < img2.shape[2]):
         z2[:,:,d] = img2[:,:,d]
   return z1.astype('uint8'), z2.astype('uint8')

def findBestMatch(big,small):
    smalli = small.astype('uint8')
    bigi = big.astype('uint8')
    if (np.any(np.asarray([(x[1]-x[0]) for x in zip(smalli.shape,bigi.shape)])<0)):
       return None
    result = np.zeros((bigi.shape[0]-smalli.shape[0]+1,bigi.shape[1]-smalli.shape[1]+1))
    for d in range(smalli.shape[2]):
      result += cv2.matchTemplate(bigi[:,:,d], smalli[:,:,d], cv2.cv.CV_TM_SQDIFF_NORMED)
    mn,_,mnLoc,_ = cv2.minMaxLoc(result)
    tuple=(mnLoc[1],mnLoc[0],mnLoc[1]+smalli.shape[0],mnLoc[0]+smalli.shape[1])
    if (tuple[2] > big.shape[0] or tuple[3] > big.shape[1]):
      return None
    return tuple

def composeCropImageMask(img1,img2,seamAnalysis=True):
    tuple = findBestMatch(img1,img2)
    mask = None
    analysis={}
    if tuple is not None:
        dims = (0,img2.shape[0],0,img2.shape[1])
        
        diffIm = np.zeros(img1.shape).astype('uint8')
        diffIm[tuple[0]:tuple[2],tuple[1]:tuple[3],:]=img2

        diffIm2 = np.copy(img1).astype('uint8')
        diffIm2[tuple[0]:tuple[2],tuple[1]:tuple[3],:]=img2

        pinned = np.where(np.array(dims)==np.array(tuple))[0]

        analysis = img_analytics(img1,diffIm)

        dst = np.abs(img1-diffIm).astype('uint8')
        dst2 = np.abs(img1-diffIm2).astype('uint8')

        gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        gray_image2 = cv2.cvtColor(dst2, cv2.COLOR_BGR2GRAY)

        ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
        ret,thresh2 = cv2.threshold(gray_image2,1,255,cv2.THRESH_BINARY)

        mask = thresh1
        if (len(pinned)>=2 and seamAnalysis):
           mask = seamMask(thresh2)
    else:
       img1 = np.array(Image.fromarray(img1).resize((img2.shape[1],img2.shape[0])))
       dst = np.abs(img1-img2).astype('uint8')
       gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
       ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
       analysis = img_analytics(img1,img2)
       mask = thresh1
    return (abs(255-mask).astype('uint8'),analysis)

def composeExpandImageMask(img1,img2):
    tuple = findBestMatch(img2,img1)
    mask = np.ones(img2.shape)*255
    if tuple is not None:
        subpic=img2[tuple[0]:tuple[2],tuple[1]:tuple[3],:]
        dst = np.abs(img1-subpic).astype('uint8')
        gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
        mask = thresh1
    return abs(255-mask).astype('uint8')

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
#     gi1 = cv2.cvtColor(z1.astype('uint16'), cv2.COLOR_BGR2GRAY)
#     gi2 = cv2.cvtColor(z2.astype('uint16'), cv2.COLOR_BGR2GRAY)
#     if z1.shape[2] == 4:
#        gi1[z1[:,:,3]==255] = 0
#     if z2.shape[2] == 4:
#        gi2[z1[:,:,3]==255] = 0
     return {'ssim':compare_ssim(z1,z2,multichannel=True),'psnr':colorPSNR(z1,z2),'shape change':size_diff(z1,z2)}

def diffMask(img1,img2,invert):
    dst = np.abs(img1-img2).astype('uint8')
    gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
    if (dst.shape[2]==4):
       gray_image[dst[:,:,3]>0] = 255
    ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
    analysis = img_analytics(img1,img2)
    return (np.array(thresh1) if invert else (255-np.array(thresh1)),analysis)

def createMask(img1, img2, invert, seamAnalysis=True):
    img1, img2 = alignChannels(img1,img2)
    if (sum(img1.shape) > sum(img2.shape)):
      return composeCropImageMask(img1,img2,seamAnalysis=seamAnalysis)
    if (sum(img1.shape) < sum(img2.shape)):
#     return composeCropImageMask(img2,img1)  
#     if this a splice, then it should be two manipulations, the base image being a blank slate
      mask = np.ones(img1.shape)*255
      return abs(255-mask).astype('uint8'),{}
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
    except ValueError:
      mask = np.ones(img1.shape)*255
      return abs(255-mask).astype('uint8'),{}

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
    
