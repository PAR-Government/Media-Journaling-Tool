import cv2
import numpy as np
from PIL import Image ,ImageOps
from operator import mul
import math
from datetime import datetime
from skimage.measure import compare_ssim
import warnings
from scipy import ndimage
from scipy import misc
import getpass
import re
import imghdr


imagefiletypes = [("jpeg files","*.jpg"),("png files","*.png"),("tiff files","*.tiff"),("Raw NEF",".nef"),("bmp files","*.bmp"),("avi files","*.avi")]

videofiletypes = [("mpeg files","*.mp4"),("mov files","*.mov"),('wmv','*.wmv'),('m4p','*.m4p'),('m4v','*.m4v'),('f4v','*.flv')]

suffixes = ["*.nef",".jpg",".png",".tiff","*.bmp",".avi",".mp4",".mov","*.wmv","*.ppm","*.pbm","*.gif"]
maskfiletypes = [("png files","*.png"),("zipped masks","*.tgz"),("mpeg files","*.mp4")]

def getMaskFileTypes():
   return maskfiletypes

def getFileTypes():
   return imagefiletypes + videofiletypes

def fileType(fileName):
  pos=fileName.rfind('.')
  suffix = fileName[pos+1:] if pos > 0 else ''
  return 'image' if (suffix in imagefiletypes or imghdr.what(fileName) is not None) else 'video'

def openFile(fileName):
   """
    Open a file using a native OS associated program
   """
   import os
   import sys
   if sys.platform.startswith('linux'):
     os.system('xdg-open "' + fileName + '"')
   elif sys.platform.startswith('win'):
     os.startfile(fileName)
   else:
     os.system('open "' + fileName + '"')

"""
   Support UID discovery using a class that supports a method getpwuid().
   tool_set.setPwdX(classInstance) to set the class.  By default, the os UID is used.
"""

try:
  import pwd
  import os
  class PwdX():
     def getpwuid(self):
          return pwd.getpwuid( os.getuid() )[ 0 ]

except ImportError:
  class PwdX():
     def getpwuid(self):
          return getpass.getuser()

pwdAPI = PwdX()

class CustomPwdX:
   uid = None
   def __init__(self, uid):
      self.uid = uid
   def getpwuid(self):
      return self.uid

def setPwdX(api):
  global pwdAPI
  pwdAPI = api


def get_username():
    return pwdAPI.getpwuid()

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

def validateCoordinates(v):
   """
   Coordinates are [x,y] or (x,y) or x,y where x and y are integers.
   Return False if the coordinates are invalid.
   """
   try:
      return len([int(re.sub('[()]','',x)) for x in v.split(',')]) == 2
   except ValueError:
      return False
   
def validateTimeString(v):
   try:
      stdt = datetime.strptime(v, '%H:%M:%S.%f')
   except ValueError:
      try:
        stdt = datetime.strptime(v, '%H:%M:%S')
      except ValueError:
        return False
   return True

def validateAndConvertTypedValue(argName,argValue,operationDef):
   """
     Validate a typed operation argument
     return the type converted argument if necessary
     raise a ValueError if invalid
   """
   if not argValue or len(str(argValue)) == 0:
      raise ValueError(argName + ' cannot be an empty string')
   argDef = operationDef.optionalparameters[argName] if argName in operationDef.optionalparameters else None
   argDef = operationDef.mandatoryparameters[argName] if not argDef and argName in operationDef.mandatoryparameters else argDef
   if argDef:
      if argDef['type'].startswith('float'):
         typeDef = argDef['type']
         vals = [float(x) for x in typeDef[typeDef.rfind('[')+1:-1].split(':')]
         if float(argValue) < vals[0] or float(argValue) > vals[1]:
            raise ValueError(argName + ' is not within the defined range')
         return float(argValue)
      elif argDef['type'].startswith('int'):
         typeDef = argDef['type']
         vals = [int(x) for x in typeDef[typeDef.rfind('[')+1:-1].split(':')]
         if int(argValue) < vals[0] or int(argValue) > vals[1]:
           raise ValueError(argName + ' is not within the defined range')
         return int(argValue)
      elif argDef['type'] == 'list':
         if argValue not in argDef['values']:
           raise ValueError(argName + ' is not one of the allowed values')
      elif argDef['type'] == 'time':
         if not validateTimeString(argValue):
           raise ValueError(argName + ' is not a valid time (e.g. HH:MM:SS.micro)')
      elif argDef['type'] == 'yesno':
         if argValue.lower() not in ['yes','no']:
           raise ValueError(argName + ' is not yes or no')
      elif argDef['type'] == 'coorindates':
         if not validateCoordinates(argValue):
           raise ValueError(argName + ' is not a valid coordinate (e.g. (6,4)')
   return argValue

def openImage(filename,videoFrameTime=None,isMask=False,preserveSnapshot=False):
   """
   Open and return an image from the file. If the file is a video, find the first non-uniform frame.
   videoFrameTime, integer time in milliseconds, is provided, then find the frame after that point in time
   preserveSnapshot, False by default, informs the function to save the frame image after extraction for videos
   """
   import os
   from scipy import ndimage

   snapshotFileName = filename
   if not os.path.exists(filename):
      return openImage('./icons/RedX.png')

   if filename[filename.rfind('.')+1:].lower() in ['avi','mp4','mov','flv','qt','wmv','m4p','mpeg','mpv','m4v']:
     snapshotFileName = filename[0:filename.rfind ('.')-len(filename)]+'.png'

   if not os.path.exists(snapshotFileName) and snapshotFileName != filename:
     cap = cv2.VideoCapture(filename)
     bestSoFar = None
     bestVariance = -1
     maxTry = 20
     try:
       while(cap.isOpened()):
         ret, frame = cap.read()
         if not ret:
            break
         if videoFrameTime and videoFrameTime < float(cap.get(cv2.cv.CV_CAP_PROP_POS_MSEC)):
           bestSoFar = frame
           break
         varianceOfImage = math.sqrt(ndimage.measurements.variance(frame)) 
         if frame is not None and bestVariance < varianceOfImage:
            bestSoFar = frame
            bestVariance = varianceOfImage
         maxTry-=1
         if not videoFrameTime and maxTry <= 0:
           break
     finally:
       cap.release()
     if bestSoFar is None:
        print 'invalid or corrupted file '+ filename
        return openImage('./icons/RedX.png')
     img = Image.fromarray(bestSoFar)
     img = img.convert('L')  if isMask else img
     if preserveSnapshot and snapshotFileName != filename:
       img.save(snapshotFileName)
     return img
   else:
     try:
       with open(snapshotFileName,"rb") as fp:
          img = Image.open(fp)
          img.load()
          return img
     except IOError as e:
        print e
        return openImage('./icons/RedX.png')

def interpolateMask(mask,img1, img2, invert=False,arguments={}):
     mask = np.asarray(mask)
     maskInverted = np.copy(mask) if invert else 255-mask
     maskInverted[maskInverted>0] = 1
     TM= __sift(img1,img2,mask2=maskInverted)
     if TM is not None:
       newMask = cv2.warpPerspective(mask, TM, img1.size, flags=cv2.WARP_INVERSE_MAP)
       analysis = {}
       analysis['transform matrix'] = serializeMatrix(TM)
       return newMask,analysis
     else:
       return None,None

def serializeMatrix(m):
   dict = {}
   dict['r'] = m.shape[0]
   dict['c'] = m.shape[1]
   for r in range(m.shape[0]):
      dict['r'+str(r)] = list(m[r,:])
   return dict

def deserializeMatrix(dict):
   m = np.zeros((int(dict['r']),int(dict['c'])))
   for r in range(m.shape[0]):
     m[r,:]= dict['r'+str(r)]
   return m

def globalTransformAnalysis(analysis,img1,img2,mask=None,arguments={}):
    globalchange = img1.size != img2.size
    if mask is not None and not globalchange:
      totalPossible = sum(img1.size)*255
      totalChanged = totalPossible - sum(sum(np.asarray(mask)))
      globalchange = (float(totalChanged)/float(totalPossible) > 0.85)
    analysis['apply transform'] = 'no' if globalchange else 'yes'

def siftAnalysis(analysis,img1,img2,mask=None,arguments={}):
    mask2 = misc.imresize(mask, np.asarray(img2).shape, interp='nearest') if mask is not None and img1.size != img2.size else mask
    matrix = __sift(img1,img2,mask1=mask,mask2=mask2)
    if matrix is not None:
      analysis['transform matrix'] = serializeMatrix(matrix)   

def createMask(img1, img2, invert, arguments={}):
      mask,analysis = __composeMask(img1,img2,invert,arguments=arguments)
      analysis['shape change'] = __sizeDiff(img1,img2)
      return Image.fromarray(mask),analysis

def __indexOf(source, dest):
   positions = []
   for spos in range(len(source)):
     for dpos in  range(len(dest)):
        if (source[spos] == dest[dpos]).all():
           positions.append(spos)
           break
   return positions


def __toGrey(img):
    splits = img.split()
    img_array = np.asarray(img.convert('RGB'))
    if (len(splits)) > 3:
       alpha = np.asarray(splits[3])
       zeros = np.zeros(alpha.shape)
       zeros[alpha>0] = 1
       img_array2 = np.zeros(img_array.shape)
       for i in range(3):
           img_array2[:,:,i] = img_array[:,:,i]*zeros
       img_array = img_array2
    return img_array.astype('uint8')
         
def __sift(img1,img2,mask1=None,mask2=None):
   img1 = __toGrey(img1)
   img2 = __toGrey(img2)
   if mask1 is not None:
     for i in range(3):
        img1[:, :, i] = img1[:, :, i] * np.asarray(mask1)
   if mask2 is not None:
     for i in range(3):
        img2[:, :, i] = img2[:, :, i] * np.asarray(mask2)

   detector = cv2.FeatureDetector_create("SIFT")
   extractor = cv2.DescriptorExtractor_create("SIFT")
   matcher = cv2.DescriptorMatcher_create("BruteForce-Hamming")

   FLANN_INDEX_KDTREE = 0
   FLANN_INDEX_LSH = 6
   index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
   search_params = dict(checks = 50)

   flann = cv2.FlannBasedMatcher(index_params, search_params)

   kp1a = detector.detect(img1)
   kp2a = detector.detect(img2)

   (kp1, d1) = extractor.compute(img1, kp1a)
   (kp2, d2) = extractor.compute(img2, kp2a)

   d1 /= (d1.sum(axis=1, keepdims=True) + 1e-7)
   d1 = np.sqrt(d1)

   d2 /= (d2.sum(axis=1, keepdims=True) + 1e-7)
   d2 = np.sqrt(d2)

   matches = flann.knnMatch(d1,d2,k=2) if d1 is not None and d2 is not None else []

   # store all the good matches as per Lowe's ratio test.
   good = [m for m,n in matches if m.distance < 0.8*n.distance]

   if len(good)>10:
     src_pts = np.float32([ kp1[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
     dst_pts = np.float32([ kp2[m.trainIdx].pt for m in good ]).reshape(-1,1,2)
     M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,5.0)
     matchesMask = mask.ravel().tolist()
     return M
   return None

def __applyTransform(compositeMask,mask,TM):
     mask = np.copy(np.asarray(mask))
     maskInverted = 255-mask
     maskInverted[maskInverted>0] = 1
     compositeMaskFlipped = 255 - compositeMask
     compositeMaskAltered = compositeMaskFlipped*maskInverted
     newMask = cv2.warpPerspective(compositeMaskAltered, TM, (mask.shape[1],mask.shape[0]))
     mask[mask>0] = 1
     compositeMaskAltered = compositeMaskFlipped*mask
     newMask[compositeMaskAltered>0] = 255
     return 255-newMask

def __composeMask(img1, img2, invert,arguments={}):
    img1, img2 = __alignChannels(img1,img2)
    # rotate image two if possible to compare back to image one.
    # The mask is not perfect.
    rotation = float(arguments['rotation']) if 'rotation' in arguments else 0.0
    if abs(rotation) > 0.0001 and img1.shape != img2.shape:
       return  __compareRotatedImage(rotation, img1, img2,invert,arguments)
    if (sum(img1.shape) > sum(img2.shape)):
      return __composeCropImageMask(img1,img2)
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

def __rotateImage(rotation, mask, img, expectedDims, cval=0):
#   (h, w) = image.shape[:2]
#   center = (w / 2, h / 2) if rotationPoint=='center' else (0,0)
#   M = cv2.getRotationMatrix2D(center, rotation, 1.0)
#   rotated = cv2.warpAffine(image, M, (w, h))
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

def alterMask(compositeMask,edgeMask,rotation=0.0, sizeChange=(0,0),interpolation='nearest',location=(0,0),transformMatrix=None):
    res = compositeMask
    if transformMatrix is not None:
       res = __applyTransform(compositeMask,edgeMask,deserializeMatrix(transformMatrix))
    elif abs(rotation) > 0.001:
       res = __rotateImage(rotation,edgeMask,res,(compositeMask.shape[0]+sizeChange[0],compositeMask.shape[1]+sizeChange[1]),cval=255)
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
