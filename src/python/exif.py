from subprocess import call,Popen, PIPE
import os

def copyexif(source,target):
  exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
  try:
     call([exifcommand, '-all=', target])
     call([exifcommand, '-P', '-TagsFromFile',  source, '-all:all', '-unsafe', target])
     call([exifcommand, '-XMPToolkit=', target])
     call([exifcommand, '-Warning=', target])
     return None
  except OSError:
     return 'exiftool not installed'

def getexif(source):
  exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
  meta = {}
  try:
    p = Popen([exifcommand,source],stdout=PIPE,stderr=PIPE)
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
  except OSError:
    print "Exiftool not installed"
  return meta

def compareexif(source,target):
  metasource = getexif(source)
  metatarget = getexif(target)
  diff = {}
  for k,v in metasource.iteritems():
     mk = unicode(metatarget[k].decode('cp1252'))
     v = unicode(v.decode('cp1252'))
     if k in metatarget:
       if mk != v:
         diff[k] = ('change',v,mk)
     else:
         diff[k] = ('delete',v)
  for k,v in metatarget.iteritems():
     if k not in metasource:
         diff[k] = ('add',v)
  return diff

