from subprocess import call,Popen, PIPE
import os

def copyexif(source,target):
  exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
  try:
     call([exifcommand, '-TagsFromFile', source,target])
     return None
  except OSError:
     return 'exiftool not installed'

def getexif(source):
  exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
  p = Popen([exifcommand,source],stdout=PIPE,stderr=PIPE)
  meta = {}
  try:
    while True:
      line = p.stdout.readline()  
      if line is None or len(line) == 0:
         break
      pos = line.find(': ')
      if pos > 0:
         meta[line[0:pos].strip()] = line[pos+2:].strip()
  finally:
    p.stdout.close()
    p.stderr.close()
  return meta

def compareexif(source,target):
  metasource = getexif(source)
  metatarget = getexif(target)
  diff = {}
  for k,v in metasource.iteritems():
     if k in metatarget:
       if metatarget[k] != v:
         diff[k] = ('change',v,metatarget[k])
     else:
         diff[k] = ('delete',v)
  for k,v in metatarget.iteritems():
     if k not in metasource:
         diff[k] = ('add',v)
  return diff

