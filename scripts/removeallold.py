import site; 
import os;
import shutil;

for pkg in site.getsitepackages():
   if not os.path.exists(pkg):
       continue
   for file in os.listdir(pkg):
       if file.startswith('maskgen') and file != 'maskgen.egg-link' and not file.startswith('maskgen_coco'):
           print 'good bye ' + file
           shutil.rmtree(os.path.join(pkg,file))
