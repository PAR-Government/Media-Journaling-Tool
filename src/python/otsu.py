import numpy as np
import cv2
from subprocess import call
import os

def peakness(hist, threshold=0.5):

  valleys = []
  P = hist[0]
# start of valley
  vA = 0
#end of valley
  vB = 0
  N = 0
# width of valley
  W = 1
  peakiness = 0.0
  peak = 0
  l  = False
  j  = 0
  while j < 255:
     l = False
     vA = hist[j]
     P = vA;
     W = 1;
     N = vA;

     i = j + 1;

     #To find the peak
     while (i < 255 and P < hist[i]):
        P = hist[i]
        W += 1
        N += hist[i]
        i += 1
  
     # To find the border of the valley other side
     peak = i - 1;
     vB = hist[i]
#       N += hist[i]
     i+=1
     W+=1

     l = True
     while (i < 255 and vB >= hist[i]):
        vB = hist[i]
        W += 1
        N += hist[i]
        i += 1 

       # Calculate peakiness
     peakiness = (1.0 - (float(vA + vB) / (2.0 * float(P)))) * (1.0 - (float(N) / float(W * P)))
     if peakiness > threshold and j not in valleys:
         valleys.append(j)
         valleys.append(i - 1)
     j = i - 1
  return valleys

#    }
#    catch (Exception)
#    {
#        if (l)
#        {
#            vB = histogram[255];###
#
#            peakiness = (1 - (double)((vA + vB) / (2.0 * P))) * (1 - ((double)N / (double)(W * P)));#
#
#            if (peakiness > peakinessThres)
#                valleys.Add(255);##
#
#                //peaks.Add(255);
#            return valleys;
#        }   
#    }

#        //if(!valleys.Contains(255))
#        //    valleys.Add(255);

#    return valleys;
#}

def otsu(hist):
  total = sum(hist)
  sumB = 0
  wB = 0
  maximum = 0.0
  sum1 = np.dot( np.asarray(range(256)), hist)
  for ii in range(256):
    wB = wB + hist[ii]
    if wB == 0:
        continue
    wF = total - wB;
    if wF == 0:
        break
    sumB = sumB +  ii * hist[ii]
    mB = sumB / wB
    mF = (sum1 - sumB) / wF;
    between = wB * wF * (mB - mF) * (mB - mF);
    if between >= maximum:
        level = ii
        maximum = between
  return level

set = [('videoSample5','videoSample6'),('videoSample6','videoSample7'),('videoSample7','videoSample8'),('videoSample8','videoSample9'),('videoSample9','videoSample10'),\
   ('videoSample11','videoSample12'),('videoSample12','videoSample13'),('videoSample13','videoSample14'),('videoSample14','videoSample15')]

def runSet(set):
  for s in set:
     buildCombinedVideo(s[0],s[1])

def buildCombinedVideo(fileOne, fileTwo):
  prefixOne = fileOne[0:fileOne.rfind('.')]
  prefixTwo = os.path.split(fileTwo[0:fileTwo.rfind('.')])[1]
  postFix = fileOne[fileOne.rfind('.'):]
  call(['ffmpeg', '-i', fileOne, '-i', fileTwo, '-filter_complex', 'blend=all_mode=difference', prefixOne + '_'  + prefixTwo + postFix])  
  buildMasksFromCombinedVideo(prefixOne + '_'  + prefixTwo + postFix)

def buildCombinedVideo(fileOne, fileTwo):
  prefixOne = fileOne[0:fileOne.rfind('.')]
  prefixTwo = os.path.split(fileTwo[0:fileTwo.rfind('.')])[1]
  postFix = fileOne[fileOne.rfind('.'):]
  maskprefix = prefixOne + '_' + prefixTwo;
  cap1 = cv2.VideoCapture(fileOne)
  cap2 = cv2.VideoCapture(fileTwo) 
  start = None
  end = None
  while(cap1.isOpened() and cap2.isOpened()):
    ret, frame1 = cap1.read()
    if not ret:
      break
    ret, frame2 = cap2.read()
    if not ret:
      break
    elapsed_time1 = cap2.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
    elapsed_time2 = cap2.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
    if elapsed_time1 != elapsed_time2:
        start = min(elapsed_time1,elapsed_time2)
        print start
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    diff = abs(gray1-gray2)
    if (sum(sum(diff))>1):
      out = np.ones(gray1.shape)*255
      out[diff>0] = 0
      cv2.imwrite(maskprefix + '_mask_' + str(elapsed_time1) + '.png',out)      

buildCombinedVideo('videoSample10.mp4','videoSample11.mp4')

def buildMasksFromCombinedVideo(file):
  cap = cv2.VideoCapture(file)
  maskprefix = file[0:file.rfind('.')]
  hist = np.zeros(256).astype('int64')
  bins=np.asarray(range(257))
  while(cap.isOpened()):
    ret, frame = cap.read()
    if not ret:
      break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hist += np.histogram(frame,bins=bins)[0]
  cap.release()
  threshold = otsu(hist)+10
  print threshold
  cap = cv2.VideoCapture(file)
  while(cap.isOpened()):
    ret, frame = cap.read()
    if not ret:
      break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray[gray>=threshold] = 255
    gray[gray<threshold] = 0
    elapsed_time = cap.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
    if (sum(sum(gray>=threshold)) > 0):
       cv2.imwrite(maskprefix + '_mask_' + str(elapsed_time) + '.png',gray)      
  cap.release()



