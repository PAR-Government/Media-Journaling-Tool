# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from os.path import expanduser
import shutil
import os
import json
from maskgen import config

imageLoaded = False

class MaskGenLoader:
    def __init__(self):
        self.load()

    def load(self):
        global_image = config.global_config['global_image'] if 'global_image' in config.global_config else None
        if global_image is not None:
            return global_image
        file_path = os.path.join(expanduser("~"), ".maskgen2")
        if os.path.exists(file_path):
            with open(file_path, "r") as jsonfile:
                global_image = json.load(jsonfile)
                config.global_config['global_image'] = global_image

    def __iter__(self):
        return self.load().keys()

    def __contains__(self,key):
        return key in self.load()

    def __setitem__(self,key,value):
        self.load()[key] = value

    def __getitem__(self, key):
        global_image = self.load()
        return global_image[key] if key in global_image else None

    def get_key(self, key, default_value=None):
        global_image = self.load()
        return global_image[key] if key in global_image else default_value

    def _backup(self):
        mainfile = os.path.join(expanduser("~"), ".maskgen2")
        backup  = os.path.join(expanduser("~"), ".maskgen2.bak")
        if os.path.exists(mainfile):
            if os.path.exists(backup):
                # A mild protection against backing-up a corrupted file. These files do not shrink much normally
                mainsize = os.path.getsize(mainfile)
                backupsize = os.path.getsize(backup)
                okToBackup = mainsize >= 0.8*(backupsize)
            else:
                okToBackup= True
        else:
            okToBackup = False
        if (okToBackup):
            shutil.copy(mainfile,backup)

    def save(self, key, data):
        global_image = self.load()
        global_image[key] = data
        self._backup()
        file_path = os.path.join(expanduser("~"), ".maskgen2")
        with open(file_path, 'w') as f:
            json.dump(global_image, f, indent=2)

    def saveall(self, idanddata):
        global_image = self.load()
        for key, data in idanddata:
            global_image[key] = data
        file_path = os.path.join(expanduser("~"), ".maskgen2")
        self._backup()
        with open(file_path, 'w') as f:
            json.dump(global_image, f, indent=2)

def main():
    import sys
    loader = MaskGenLoader()
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        id = args[i]
        v = args[i+1]
        loader.save(id,v)
        i+=2

if __name__ == '__main__':
    main()
