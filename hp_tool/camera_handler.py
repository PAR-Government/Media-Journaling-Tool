import requests
import json
import tkMessageBox

class API_Camera_Handler:
    def __init__(self, master, url, token):
        self.master = master
        self.url = url
        self.token = token
        self.localIDs = []
        self.models_hp = []
        self.models_exif = []
        self.makes_exif = []
        self.sn_exif = []
        self.all = {}
        self.load_data()

    def get_local_ids(self):
        return self.localIDs

    def get_model_hp(self):
        return self.models_hp

    def get_model_exif(self):
        return self.models_exif

    def get_makes_exif(self):
        return self.makes_exif

    def get_sn(self):
        return self.sn_exif

    def get_all(self):
        return self.all

    def load_data(self):
        try:
            headers = {'Authorization': 'Token ' + self.token, 'Content-Type': 'application/json'}
            url = self.url + '/api/cameras/?fields=hp_device_local_id, hp_camera_model, exif_device_serial_number, exif_camera_model, exif_camera_make/'
            print 'Checking browser API for list of devices...'

            while True:
                response = requests.get(url, headers=headers)
                if response.status_code == requests.codes.ok:
                    r = json.loads(response.content)
                    for item in r['results']:
                        self.all[item['hp_device_local_id']] = item
                        self.localIDs.append(item['hp_device_local_id'])
                        self.models_hp.append(item['hp_camera_model'])
                        self.sn_exif.append(item['exif_device_serial_number'])
                        for configuration in item['exif']:
                            self.models_exif.append(configuration['exif_camera_model'])
                            self.makes_exif.append(configuration['exif_camera_make'])

                    url = r['next']
                    if url is None:
                        break
                else:
                    raise requests.HTTPError()
        except (requests.HTTPError, requests.ConnectionError):
            print 'An error ocurred connecting to Medifor browser (' + str(response.status_code) + ').\n Devices will be loaded from hp_tool/data.'
        except KeyError:
            tkMessageBox.showerror(title='Information', message='Could not find browser credentials in settings. Please '
                                                               'add them via Settings in the File menu.')