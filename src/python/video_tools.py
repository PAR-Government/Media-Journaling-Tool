import numpy as np
import cv2
from subprocess import call,Popen, PIPE
import os
import json

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

def addToMeta(meta,prefix,line,split=True):
   parts = line.split(',') if split else [line]
   for part in parts:
     pair = [x.strip().lower() for x in part.split(': ')]
     if len(pair)>1 and pair[1] != '':
       if prefix != '':
         meta[prefix + '.' + pair[0]] = pair[1]
       else:
         meta[pair[0]] = pair[1]
   
def getStreamId(line):
   start = line.find('#')
   if start > 0:
     end = line.find('(',start)
     end = min(end,line.find(': ',start))
     return line[start:end]
   return ''

def processMeta(stream):
   meta = {}
   prefix = ''
   while True:
     line = stream.readline()   
     if line is None or len(line) == 0:
         break
     if 'Stream' in line:
         prefix=getStreamId(line)
         splitPos = line.find(': ')
         meta[line[0:splitPos].strip()] = line[splitPos+2:].strip()
         continue
     if 'Duration' in line:
       addToMeta(meta,prefix, line)
     else:
       addToMeta(meta,prefix, line, split=False)
   return meta

def sortFrames(frames):
   for k,v in frames.iteritems():
    frames[k] = sorted(v,key=lambda meta: meta['pkt_pts_time'])

def _addMetaToFrames(frames,meta):
   if len(meta) > 0 and 'stream_index' in meta:
      index = meta['stream_index']
      if index not in frames:
         frames[index] = []
      frames[index].append(meta)
      meta.pop('stream_index')

def processFrames(stream):
   frames = {}
   meta = {}
   while True:
     line = stream.readline()  
     if line is None or len(line) == 0:
         break
     if '[/FRAME]' in line:
        _addMetaToFrames(frames,meta)
        meta = {}
     else:
         parts = line.split('=')
         if len(parts)>1:
            meta[parts[0].strip()] = parts[1].strip()
   _addMetaToFrames(frames,meta)
   return frames
#   sortFrames(frames)
   
def getMeta(file,withFrames=False):
   p = Popen(['ffprobe',file, '-show_frames'] if withFrames else ['ffprobe',file],stdout=PIPE,stderr=PIPE)
   try:
     frames= processFrames(p.stdout) if withFrames else {}
     meta = processMeta(p.stderr) 
   finally:
     p.stdout.close()
     p.stderr.close()
   return meta,frames

# str(ffmpeg.compareMeta({'f':1,'e':2,'g':3},{'f':1,'y':3,'g':4}))=="{'y': ('a', 3), 'e': ('d', 2), 'g': ('c', 4)}"
def compareMeta(oneMeta,twoMeta,skipMeta=None):
  diff = {}
  for k,v in oneMeta.iteritems():
    if skipMeta is not None and k in skipMeta:
      continue
    if k in twoMeta and twoMeta[k] != v:
      diff[k] = ('change',v, twoMeta[k])
    if k not in twoMeta:
      diff[k] = ('delete',v)
  for k,v in twoMeta.iteritems():
    if k not in oneMeta:
      diff[k] = ('add',v)
  return diff

# video_tools.compareStream([{'i':0,'h':1},{'i':1,'h':1},{'i':2,'h':1},{'i':3,'h':1},{'i':5,'h':2},{'i':6,'k':3}],[{'i':0,'h':1},{'i':3,'h':1},{'i':4,'h':9},{'i':4,'h':2}], orderAttr='i')
# [('delete', 1.0, 2.0, 2), ('add', 4.0, 4.0, 2), ('delete', 5.0, 6.0, 2)]
def compareStream(a,b,orderAttr='pkt_pts_time',skipMeta=None):
  apos = 0
  bpos = 0
  diff = []
  start=0
  while apos < len(a) and bpos < len(b):
    apacket = a[apos]
    aptime = float(apacket[orderAttr])
    bpacket = b[bpos]
    try:
      bptime = float(bpacket[orderAttr])
    except ValueError as e:
      print bpacket
      raise e
    if aptime==bptime:
      metaDiff = compareMeta(apacket,bpacket,skipMeta=skipMeta)
      if len(metaDiff)>0:
        diff.append(('change',apos,bpos,aptime,metaDiff))
      apos+=1
      bpos+=1
    elif aptime < bptime:
      start = aptime
      c = 0
      while aptime < bptime and apos < len(a):
         end = aptime
         apos+=1
         c+=1
         if apos < len(a):
           apacket = a[apos]
           aptime = float(apacket[orderAttr])
      diff.append(('delete',start,end,c))
    elif aptime > bptime:
      start = bptime
      c = 0
      while aptime > bptime and bpos < len(b):
          end = bptime
          c+=1
          bpos+=1
          if bpos < len(b):
            bpacket = b[bpos]
            bptime = float(bpacket[orderAttr])
      diff.append(('add',start,end,c))
  if apos < len(a):
    start = float(a[apos][orderAttr])
    c = 0
    while apos < len(a):
       apacket = a[apos]
       aptime = float(apacket[orderAttr])
       apos+=1
       c+=1
    diff.append(('delete',start,aptime,c))
  elif bpos < len(b):
    start = float(b[bpos][orderAttr])
    c = 0
    while bpos < len(b):
       bpacket = b[apos]
       bptime = float(apacket[orderAttr])
       bpos+=1
       c+=1
    diff.append(('add',start,bptime,c))
  return diff

def compareFrames(oneFrames,twoFrames,skipMeta=None):
  diff = {}
  for streamId, packets in oneFrames.iteritems():
    if streamId in twoFrames:
       diff[streamId] = ('change',compareStream(packets, twoFrames[streamId],skipMeta=skipMeta))
    else:
       diff[streamId] = ('delete',[])
  for streamId, packets in twoFrames.iteritems():
    if streamId not in oneFrames:
       diff[streamId] = ('add',[])
  return diff
    
#video_tools.formMetaDataDiff('/Users/ericrobertson/Documents/movie/videoSample.mp4','/Users/ericrobertson/Documents/movie/videoSample1.mp4')
def formMetaDataDiff(fileOne, fileTwo):
  oneMeta,oneFrames = getMeta(fileOne,withFrames=True)
  twoMeta,twoFrames = getMeta(fileTwo,withFrames=True)
  metaDiff = compareMeta(oneMeta,twoMeta)
  frameDiff = compareFrames(oneFrames, twoFrames, skipMeta=['pkt_pos','pkt_size'])
  return metaDiff,frameDiff

#video_tools.processSet('/Users/ericrobertson/Documents/movie',[('videoSample','videoSample1'),('videoSample1','videoSample2'),('videoSample2','videoSample3'),('videoSample4','videoSample5'),('videoSample5','videoSample6'),('videoSample6','videoSample7'),('videoSample7','videoSample8'),('videoSample8','videoSample9'),('videoSample9','videoSample10'),('videoSample11','videoSample12'),('videoSample12','videoSample13'),('videoSample13','videoSample14'),('videoSample14','videoSample15')] ,'.mp4')
def processSet(dir,set,postfix):
  first = None
  for pair in set:
    print pair
    resMeta,resFrame = formMetaDataDiff(os.path.join(dir,pair[0]+postfix),os.path.join(dir,pair[1]+postfix))
    resultFile = os.path.join(dir,pair[0] + "_" + pair[1] + ".json")
    with open(resultFile, 'w') as f:
       json.dump({"meta":resMeta,"frames":resFrame},f,indent=2)


#video_tools.formMaskDiff('/Users/ericrobertson/Documents/movie/videoSample.mp4','/Users/ericrobertson/Documents/movie/videoSample1.mp4')
def formMaskDiff(fileOne, fileTwo):
   prefixOne = fileOne[0:fileOne.rfind('.')]
   prefixTwo = os.path.split(fileTwo[0:fileTwo.rfind('.')])[1]
   postFix = fileOne[fileOne.rfind('.'):]
   call(['ffmpeg', '-y', '-i', fileOne, '-i', fileTwo, '-filter_complex', 'blend=all_mode=difference', prefixOne + '_'  + prefixTwo + postFix])  
   buildMasksFromCombinedVideo(prefixOne + '_'  + prefixTwo + postFix)

