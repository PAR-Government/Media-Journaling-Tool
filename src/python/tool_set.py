import cv2
import numpy as np
from PIL import Image 
from operator import mul

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
       return img1, img2
   thirdchannel = max(img1.shape[2],img2.shape[2])
   z1 = np.ones((img1.shape[0],img1.shape[1],thirdchannel))*255
   z2 = np.ones((img2.shape[0],img2.shape[1],thirdchannel))*255
   for d in range(thirdchannel):
       if (d < img1.shape[2]):
         z1[:,:,d] = img1[:,:,d]
       if (d < img2.shape[2]):
         z2[:,:,d] = img2[:,:,d]
   return z1,z2

def findBestMatchOld(img1,img2):
    img1y=img1.shape[0]
    img1x=img1.shape[1]

    img2y=img2.shape[0]
    img2x=img2.shape[1]

    stopy=img1y-img2y+1
    stopx=img1x-img2x+1

    maxv = -1
    maxc = (-1,-1)
    done = False
    for x1 in range(0,stopx):
        if done:
           break
        for y1 in range(0,stopy):
            x2=x1+img2x
            y2=y1+img2y

            subpic=img1[y1:y2,x1:x2,:]
            test=subpic==img2

            matches = np.sum(test)
            if (matches > maxv):
                maxc = (x1,y1)
                maxv = matches
            if matches == img2.shape[0]*img2.shape[1]:
               done = True
               break
    return (maxc[1],maxc[0],maxc[1]+img2y,maxc[0]+img2x) if maxv>0 else None


def findBestMatch(big,small):
    smalli = small.astype('uint8')
    bigi = big.astype('uint8')
    if (np.any(np.asarray([(x[1]-x[0]) for x in zip(smalli.shape,bigi.shape)])<0)):
       return None
    result = np.zeros((bigi.shape[0]-smalli.shape[0]+1,bigi.shape[1]-smalli.shape[1]+1))
    for d in range(smalli.shape[2]):
      result += cv2.matchTemplate(bigi[:,:,d], smalli[:,:,d], cv2.cv.CV_TM_SQDIFF_NORMED)
    mn,_,mnLoc,_ = cv2.minMaxLoc(result)
#    subpic=bigi[mnLoc[0]:mnLoc[0]+smalli.shape[0],mnLoc[1]:mnLoc[1]+smalli.shape[1],:]
#    matches = np.sum(subpic==small)
#    ratio = float(matches)/reduce(mul, small.shape)
    return (mnLoc[0],mnLoc[1],mnLoc[0]+smalli.shape[0],mnLoc[1]+smalli.shape[1])

def composeCropImageMask(img1,img2):
    tuple = findBestMatch(img1,img2)
    mask = np.zeros(img1.shape)
    if tuple is not None:
        dims = (0,img2.shape[0],0,img2.shape[1])
        
        diffIm = np.zeros(img1.shape)
        diffIm[tuple[0]:tuple[2],tuple[1]:tuple[3],:]=img2

        diffIm2 = np.copy(img1)
        diffIm2[tuple[0]:tuple[2],tuple[1]:tuple[3],:]=img2

        pinned = np.where(np.array(dims)==np.array(tuple))[0]

        dst = np.abs(img1-diffIm).astype('uint8')
        dst2 = np.abs(img1-diffIm2).astype('uint8')

        gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        gray_image2 = cv2.cvtColor(dst2, cv2.COLOR_BGR2GRAY)

        ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
        ret,thresh2 = cv2.threshold(gray_image2,1,255,cv2.THRESH_BINARY)

        mask = thresh1
        mask = seamMask(thresh2) if (len(pinned)>=2) else mask
    else:
        mask = np.array(mask*255)[:,:,0]
    return abs(255-mask)

def composeExpandImageMask(img1,img2):
    tuple = findBestMatch(img2,img1)
    mask = np.ones(img2.shape)*255
    if tuple is not None:
        subpic=img2[tuple[0]:tuple[2],tuple[1]:tuple[3],:]
        dst = np.abs(img1-subpic).astype('uint8')
        gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
        mask = thresh1
    return abs(255-mask)

def diffMask(img1,img2,invert):
    dst = np.abs(img1-img2).astype('uint8')
    gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
    if (dst.shape[2]==4):
       gray_image[dst[:,:,3]>0] = 255
    ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
    return np.array(thresh1) if invert else (255-np.array(thresh1))

def createMask(img1, img2, invert):
    img1, img2 = alignChannels(img1,img2)
    if (sum(img1.shape) > sum(img2.shape)):
      return composeCropImageMask(img1,img2)
    if (sum(img1.shape) < sum(img2.shape)):
      return composeCropImageMask(img2,img1)
    return diffMask(img1,img2,invert)

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

def imageResize(img,dim):
   wpercent = float(dim[0])/float(img.size[0])
   hpercent = float(dim[1])/float(img.size[1])
   perc = min(wpercent,hpercent)
   wsize = int((float(img.size[0])*float(perc)))
   hsize = int((float(img.size[1])*float(perc)))
   return img.resize((wsize,hsize), Image.ANTIALIAS).convert('RGBA')

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
    

