from os.path import expanduser
import csv
import platform
import os
import json

global_image = {}
imageLoaded = False


class MaskGenLoader:
    def __init__(self):
        self.load()

    def load(self):
        global global_image
        global imageLoaded
        if imageLoaded:
            return
        file_path = os.path.join(expanduser("~"), ".maskgen2")
        if os.path.exists(file_path):
            with open(file_path, "r") as jsonfile:
                global_image = json.load(jsonfile)
        imageLoaded = True

    def get_key(self, image_id, default_value=None):
        global global_image
        return global_image[image_id] if image_id in global_image else default_value

    def save(self, image_id, data):
        global global_image
        global_image[image_id] = data
        file_path = os.path.join(expanduser("~"), ".maskgen2")
        with open(file_path, 'w') as f:
            json.dump(global_image, f, indent=2)

    def saveall(self, idanddata):
        global global_image
        for image_id, data in idanddata:
            global_image[image_id] = data
        file_path = os.path.join(expanduser("~"), ".maskgen2")
        with open(file_path, 'w') as f:
            json.dump(global_image, f, indent=2)
