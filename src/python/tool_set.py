import cv2
import numpy as np

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
   z1 = np.zeros((img1.shape[0],img1.shape[1],thirdchannel))
   z2 = np.zeros((img2.shape[0],img2.shape[1],thirdchannel))
   for d in range(thirdchannel):
       if (d < img1.shape[2]):
         z1[:,:,d] = img1[:,:,d]
       if (d < img2.shape[2]):
         z2[:,:,d] = img2[:,:,d]
   return z1,z2

def findBestMatch(img1,img2):
    img1y=img1.shape[0]
    img1x=img1.shape[1]

    img2y=img2.shape[0]
    img2x=img2.shape[1]

    stopy=img1y-img2y+1
    stopx=img1x-img2x+1

    maxv = -1
    maxc = (-1,-1)
    for x1 in range(0,stopx):
        for y1 in range(0,stopy):
            x2=x1+img2x
            y2=y1+img2y

            subpic=img1[y1:y2,x1:x2,:]
            test=subpic==img2

            matches = np.sum(test)
            if (matches > maxv):
                maxc = (x1,y1)
                maxv = matches
    return (maxc[1],maxc[0],maxc[1]+img2y,maxc[0]+img2x) if maxv>0 else None

def composeCropImageMask(img1,img2):
    tuple = findBestMatch(img1,img2)
    mask = np.ones(img2.shape)
    if tuple is not None:
        dims = (0,img2.shape[0],0,img2.shape[1])
        pinned = np.where(np.array(dims)==np.array(tuple))[0]
        subpic=img1[tuple[0]:tuple[2],tuple[1]:tuple[3],:]
        test=np.array(subpic==img2)
        mask[test] = 0
        mask = np.array(mask*255)[:,:,0]
        # look for splices
        mask = spliceMask(mask) if (len(pinned)>=2) else mask
    else:
        mask = np.array(mask*255)[:,:,0]
    return mask

def composeExpandImageMask(img1,img2):
    tuple = findBestMatch(img2,img1)
    mask = np.ones(img2.shape)
    if tuple is not None:
        subpic=img2[tuple[0]:tuple[2],tuple[1]:tuple[3],:]
        test=np.array(subpic==img1)
        submask = np.ones(test.shape)
        submask[test] = 0
        mask[tuple[0]:tuple[2],tuple[1]:tuple[3]] = submask
    return np.array(mask*255)[:,:,0]

def createMask(img1, img2):
    img1, img2 = alignChannels(img1,img2)
    if (sum(img1.shape) > sum(img2.shape)):
      return composeCropImageMask(img1,img2)
    if (sum(img1.shape) < sum(img2.shape)):
      return composeExpandImageMask(img1,img2)
    dst = np.abs(img1-img2).astype('uint8')
    gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
    ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
    return np.array(thresh1)

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

def spliceMask(mask):
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
    
