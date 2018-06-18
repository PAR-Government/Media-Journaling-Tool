import requests
import json
import os
import data_files


class API_Camera_Handler:
    """
    Manages camera metadata. If cannot connect to browser, will load from data/devices.json
    :param url: base URL
    :param token: browser login token
    :param given_id: camera local id to look up
    """
    def __init__(self, master, url, token, given_id):
        self.master = master
        self.url = url
        self.token = token
        self.given_id = given_id
        self.localIDs = []
        self.models_hp = []
        self.models_exif = []
        self.makes_exif = []
        self.sn_exif = []
        self.ids = []
        self.device_types = []
        self.all = {}
        self.source = None
        if given_id == "download_locally":
            self.write_devices()
        elif given_id != "":
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

    def get_source(self):
        return self.source

    def get_ids(self):
        return self.ids

    def get_types(self):
        return self.device_types

    def load_data(self):
        try:
            headers = {'Authorization': 'Token ' + self.token, 'Content-Type': 'application/json'}
            url = self.url + '/cameras/filters/?fields=hp_device_local_id, hp_camera_model, exif_device_serial_number, exif_camera_model, exif_camera_make/'
            camera_data = {"hp_device_local_id": {"type": "exact", "value": self.given_id}}
            print 'Updating camera list from browser API... ',

            while True:
                response = requests.post(url, json=camera_data, headers=headers)
                if response.status_code == requests.codes.ok:
                    r = json.loads(response.content)
                    for item in r['results']:
                        self.all[item['hp_device_local_id']] = item
                        self.localIDs.append(item['hp_device_local_id'])
                        self.models_hp.append(item['hp_camera_model'])
                        self.ids.append(item['id'])
                        self.device_types.append(item['camera_type'])
                        for configuration in item['exif']:
                            self.models_exif.append(configuration['exif_camera_model'])
                            self.makes_exif.append(configuration['exif_camera_make'])
                            self.sn_exif.append(configuration['exif_device_serial_number'])
                    break
                else:
                    raise requests.HTTPError()
            print 'complete.'

            self.source = 'remote'
        except:
            print 'Could not connect. Loading from local file... ',
            self.localIDs = []
            self.models_hp = []
            self.models_exif = []
            self.makes_exif = []
            self.sn_exif = []
            self.all = {}
            devices_path = data_files._LOCALDEVICES if os.path.exists(data_files._LOCALDEVICES) else data_files._DEVICES
            with open(devices_path) as j:
                device_data = json.load(j)
            for localID, data in device_data.iteritems():
                self.all[localID] = data
                self.localIDs.append(data['hp_device_local_id'])
                self.models_hp.append(data['hp_camera_model'])
                self.ids.append(item['id'])
                self.device_types.append(item['camera_type'])
                for configuration in data['exif']:
                    self.models_exif.append(configuration['exif_camera_model'])
                    self.makes_exif.append(configuration['exif_camera_make'])
                    self.sn_exif.append(configuration['exif_device_serial_number'])
            print 'complete.'
            self.source = 'local'

    def write_devices(self):
        try:
            headers = {'Authorization': 'Token ' + self.token, 'Content-Type': 'application/json'}
            url = self.url + '/cameras/filters/?fields=hp_device_local_id, hp_camera_model, exif_device_serial_number, exif_camera_model, exif_camera_make/'
            camera_data = {"high_provenance": {"type": "exact", "value": True}}

            print 'Downloading camera list from browser API... ',

            while True:
                response = requests.post(url, json=camera_data, headers=headers)
                if response.status_code == requests.codes.ok:
                    r = json.loads(response.content)
                    for item in r['results']:
                        self.all[item['hp_device_local_id']] = item

                    url = r['next']
                    if url is None:
                        break
                else:
                    raise requests.HTTPError()

            with open(data_files._LOCALDEVICES, 'w') as j:
                json.dump(self.all, j, indent=4)

            self.source = 'remote'

            print 'complete.'
        except (requests.ConnectionError, requests.ConnectTimeout, requests.HTTPError):
            print 'Could not connect to browser.  Try again later.'
            self.source = 'local'


class ValidResolutions:
    def __init__(self, master, url, token, local_id=None, cam_id=None):
        self.master = master
        self.url = url
        self.token = token
        self.cam_id = cam_id
        self.resolutions = {"primary": [], "secondary": []}

        if local_id and not self.cam_id:
            cam = API_Camera_Handler(self.master, self.url, self.token, local_id)
            try:
                self.cam_id = cam.get_ids()[0]
            except IndexError:
                return

        if self.cam_id:
            self.fetch_resolutions()

    def fetch_resolutions(self):
        print('Fetching valid sizes... '),
        try:
            headers = {'Authorization': 'Token ' + self.token, 'Content-Type': 'application/json'}
            url = self.url + "/cameras/" + str(self.cam_id) + "/sizes/"

            # get primary data
            response = requests.get(url + "?primary_secondary=primary", headers=headers)
            if response.status_code == requests.codes.ok:
                r = json.loads(response.content)
                for item in r:
                    self.resolutions['primary'].append((item['width'], item['height']))

            # get secondary data
            response = requests.get(url + "?primary_secondary=secondary", headers=headers)
            if response.status_code == requests.codes.ok:
                r = json.loads(response.content)
                for item in r:
                    self.resolutions['secondary'].append((item['width'], item['height']))

            print('complete.')
        except (requests.ConnectionError, requests.ConnectTimeout):
            print('\nCould not fetch camera sizes.  Try again later')
            pass
        return

    def get_resolutions(self):
        return self.resolutions

