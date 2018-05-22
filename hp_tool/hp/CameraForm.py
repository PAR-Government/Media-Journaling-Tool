import csv
import tkSimpleDialog
import webbrowser
from Tkinter import *
import ttk
import pandas as pd
import os
import collections
import subprocess
import tkFileDialog, tkMessageBox
import json
import requests
from camera_handler import API_Camera_Handler
from hp_data import exts
import data_files

"""
Contains classes for managing camera browser adding/editing
"""

class HP_Device_Form(Toplevel):
    """This class creates the window to add a new device. Must have browser login."""
    def __init__(self, master, validIDs=None, pathvar=None, token=None, browser=None, gan=False):
        Toplevel.__init__(self, master)
        self.geometry("%dx%d%+d%+d" % (600, 600, 250, 125))
        self.master = master
        self.pathvar = pathvar # use this to set a tk variable to the path of the output txt file
        self.validIDs = validIDs if validIDs is not None else []
        self.set_list_options()
        self.camera_added = False
        self.is_gan = gan
        self.renamed = {}
        self.trello_token = StringVar()
        self.trello_token.set(token) if token is not None else ''
        self.browser_token = StringVar()
        self.browser_token.set(browser) if browser is not None else ''

        self.trello_key = data_files._TRELLO['app_key']
        self.create_widgets()

    def set_list_options(self):
        """
        Sets combobox options for manufacturer, lens mounts, and device types
        :return: None
        """
        df = pd.read_csv(os.path.join(data_files._DB))
        self.manufacturers = [str(x).strip() for x in df['Manufacturer'] if str(x).strip() != 'nan']
        self.lens_mounts = [str(y).strip() for y in df['LensMount'] if str(y).strip() != 'nan']
        self.device_types = [str(z).strip() for z in df['DeviceType'] if str(z).strip() != 'nan']

    def create_widgets(self):
        """
        Creates form widgets
        :return: None
        """
        self.f = VerticalScrolledFrame(self)
        self.f.pack(fill=BOTH, expand=TRUE)

        Label(self.f.interior, text='Add a new HP Device', font=('bold underline', 25)).pack()
        Label(self.f.interior, text='Once complete, the new camera will be added automatically, and a notification card will be posted to trello.', wraplength=400).pack()

        if not self.is_gan:
            Label(self.f.interior, text='Sample File', font=('bold', 18)).pack()
            Label(self.f.interior, text='This is required. Select an image/video/audio file. Once metadata is loaded from it, you may continue to complete the form.'
                                        ' Some devices can have multiple make/model configurations for images vs. video, or for apps. In this instances, submit this '
                                        'form as normal, and then go to File->Update a Device on the main GUI.', wraplength=400).pack()
            self.imageButton = Button(self.f.interior, text='Select File', command=self.populate_from_image)
            self.imageButton.pack()

        # all questions defined here. end name with a * to make mandatory
        head = [('Media Type*', {'description': 'Select the type of media contained in the sample file (Image, Video, Audio)',
                                 'type': 'readonlylist',
                                 'values': ['image', 'video', 'audio']}),
                ('App', {'description': 'If the sample image was taken with a certain app, specify it here. Otherwise, leave blank.',
                         'type': 'text',
                         'values': None}),
                ('Exif Camera Make',{'description': 'Device make, pulled from device Exif.',
                                     'type': 'list',
                                     'values': self.manufacturers}),
                ('Exif Camera Model',{'description': 'Device model, pulled from device Exif.',
                                      'type': 'text',
                                      'values': None}),
                ('Device Serial Number', {'description': 'Device serial number, pulled from device Exif.',
                                          'type': 'text',
                                          'values': None}),
                ('Local ID*', {'description': 'This can be a one of a few forms. The most preferable is the cage number. If it is a personal device, you can use INITIALS-MODEL, such as'
                                              ' ES-iPhone4. Please check that the local ID is not already in use.',
                               'type': 'text',
                               'values': None}),
                ('Device Affiliation*', {'description': 'If it is a personal device, please define the affiliation as Other, and write in your organization and your initials, e.g. RIT-TK',
                                         'type': 'radiobutton',
                                         'values': ['RIT', 'PAR', 'Other (please specify):']}),
                ('HP Model*',{'description': 'Please write the make/model such as it would be easily identifiable, such as Samsung Galaxy S6.',
                             'type': 'text',
                             'values': None}),
                ('Edition',{'description': 'Specific edition of the device, if applicable and not already in the device\'s name.',
                            'type': 'text',
                            'values': None}),
                ('Device Type*',{'description': 'Select camera type. If none are applicable, select "other".',
                                 'type': 'readonlylist',
                                 'values':self.device_types}),
                ('Sensor Information',{'description': 'Sensor size/dimensions/other sensor info.',
                                       'type': 'text',
                                       'values': None}),
                ('Lens Mount*',{'description': 'Choose \"builtin\" if the device does not have interchangeable lenses.',
                                'type': 'list',
                                'values':self.lens_mounts}),
                ('Firmware/OS',{'description': 'Firmware/OS',
                                'type': 'text',
                                'values': None}),
                ('Firmware/OS Version',{'description': 'Firmware/OS Version',
                                        'type': 'text',
                                        'values': None}),
                ('General Description',{'description': 'Other specifications',
                                        'type': 'text',
                                        'values': None}),
        ]
        self.headers = collections.OrderedDict(head)

        self.questions = {}
        for h in self.headers:
            d = SectionFrame(self.f.interior, title=h, descr=self.headers[h]['description'], type=self.headers[h]['type'], items=self.headers[h]['values'], bd=5)
            d.pack(pady=4)
            self.questions[h] = d

        Label(self.f.interior, text='Trello Login Token', font=(20)).pack()
        Label(self.f.interior, text='This is required to send a notification of the new device to Trello.').pack()
        trello_link = 'https://trello.com/1/authorize?key=' + self.trello_key + '&scope=read%2Cwrite&name=HP_GUI&expiration=never&response_type=token'
        trelloTokenButton = Button(self.f.interior, text='Get Trello Token', command=lambda: self.open_link(trello_link))
        trelloTokenButton.pack()
        tokenEntry = Entry(self.f.interior, textvar=self.trello_token)
        tokenEntry.pack()

        Label(self.f.interior, text='Browser Login Token*', font=(20)).pack()
        Label(self.f.interior, text='This allows for the creation of the new device.').pack()
        browserTokenButton = Button(self.f.interior, text='Get Browser Token', command=lambda: tkMessageBox.showinfo("Get Browser Token", "Refer to the HP Tool guide to retrieve your browser token."))
        browserTokenButton.pack()
        browserEntry = Entry(self.f.interior, textvar=self.browser_token)
        browserEntry.pack()

        buttonFrame = Frame(self)
        buttonFrame.pack()

        self.okbutton = Button(buttonFrame, text='Complete', command=self.export_results)
        self.okbutton.pack()
        self.cancelbutton = Button(buttonFrame, text='Cancel', command=self.destroy)
        self.cancelbutton.pack()

        if self.is_gan:
            self.questions['Exif Camera Make'].edit_items([])
            self.questions['Device Type*'].edit_items(['Computational'])
            self.questions['Device Type*'].set('Computational')
            self.add_required('Edition')
            self.questions['Sensor Information'].pack_forget()
            self.questions['Device Serial Number'].pack_forget()
            self.add_required('Exif Camera Model')
            self.questions['HP Model*'].pack_forget()
            self.questions["Lens Mount*"].pack_forget()
            self.questions['Lens Mount*'].set("NA")
            self.remove_required("Lens Mount*")
            self.add_required('Firmware/OS')
            self.add_required('Firmware/OS Version')
            self.rename("Exif Camera Make", "GAN Name*", "Name of the GAN used")

        else:
            self.okbutton.configure(state='disabled')
            for q, a in self.questions.iteritems():
                a.disable()

    def remove_required(self, data):
        if not data.endswith("*"):
            return
        try:
            self.headers[data[:-1]] = self.headers.pop(data)
            self.questions[data].remove_required()
            self.renamed[data[:-1]] = data
        except KeyError:
            return

    def add_required(self, data):
        if data.endswith("*"):
            return
        try:
            self.headers[data + "*"] = self.headers.pop(data)
            self.questions[data].add_required()
            self.renamed[data + "*"] = data
        except KeyError:
            return

    def rename(self, item, title, desc):
        try:
            self.headers[title] = self.headers.pop(item)
            self.renamed[title] = item
            self.questions[item].rename(title, desc)
        except KeyError:
            return

    def populate_from_image(self):
        """
        Fill mandatory exif-fillable fields
        :return: None
        """
        self.imfile = tkFileDialog.askopenfilename(title='Select Image File', parent=self)
        if not self.imfile:
            return
        self.imageButton.config(text=os.path.basename(self.imfile))
        args = ['exiftool', '-f', '-j', '-Model', '-Make', '-SerialNumber', self.imfile]
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
            exifData = json.loads(p)[0]
        except:
            self.master.statusBox.println('An error ocurred attempting to pull exif data from image.')
            return

        for q, a in self.questions.iteritems():
            a.enable()
        if exifData['Make'] != '-':
            self.questions['Exif Camera Make'].set(exifData['Make'])
        self.questions['Exif Camera Make'].disable()
        if exifData['Model'] != '-':
            self.questions['Exif Camera Model'].set(exifData['Model'])
        self.questions['Exif Camera Model'].disable()
        if exifData['SerialNumber'] != '-':
            self.questions['Device Serial Number'].set(exifData['SerialNumber'])
        self.questions['Device Serial Number'].disable()
        self.okbutton.config(state='normal')

    def export_results(self):
        """
        Triggers when ok/complete button is clicked. Validates and exports the new camera data
        :return: None
        """
        if self.is_gan:
            self.questions["HP Model*"].set(self.questions['Exif Camera Model'].get())

        msg = None
        for h in self.headers:
            if h in self.renamed.keys():
                contents = self.questions[self.renamed[h]].get()
            else:
                contents = self.questions[h].get()
            if h.endswith('*') and contents == '':
                msg = 'Field ' + h[:-1] + ' is a required field.'
                break
        if self.browser_token.get() == '':
            msg = 'Browser Token is a required field.'
        check = self.local_id_used()
        msg = msg if check is None else check

        if msg:
            tkMessageBox.showerror(title='Error', message=msg, parent=self)
            return

        # post and check browser response
        browser_resp = self.post_to_browser()
        if browser_resp.status_code in (requests.codes.ok, requests.codes.created):
            cont = tkMessageBox.askyesno(title='Complete', message='Successfully posted new camera information! Post notification to Trello?', parent=self)
            self.camera_added = True
        else:
            tkMessageBox.showerror(title='Error', message='An error ocurred posting the new camera information to the MediBrowser. (' + str(browser_resp.status_code)+ ')', parent=self)
            return
        if cont:
            code = self.post_to_trello()
            if code is not None:
                tkMessageBox.showerror('Trello Error', message='An error ocurred connecting to trello (' + str(
                    code) + ').\nIf you\'re not sure what is causing this error, email medifor_manipulators@partech.com.', parent=self)
            else:
                tkMessageBox.showinfo(title='Information', message='Complete!', parent=self)

        self.destroy()

    def post_to_browser(self):
        """
        Handles the browser interaction
        :return: requests.post() response
        """
        url = self.master.settings.get_key("apiurl") + '/cameras/'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token ' + self.browser_token.get(),
        }
        data = { 'hp_device_local_id': self.questions['Local ID*'].get(),
                 'affiliation': self.questions['Device Affiliation*'].get(),
                 'hp_camera_model': self.questions['HP Model*'].get(),
                 'exif':[{'exif_camera_make': self.questions['Exif Camera Make'].get(),
                          'exif_camera_model': self.questions['Exif Camera Model'].get(),
                          'exif_device_serial_number': self.questions['Device Serial Number'].get(),
                          'hp_app': self.questions['App'].get(),
                          'media_type': self.questions['Media Type*'].get()}],
                 'camera_edition': self.questions['Edition'].get(),
                 'camera_type': self.questions['Device Type*'].get(),
                 'camera_sensor': self.questions['Sensor Information'].get(),
                 'camera_description': self.questions['General Description'].get(),
                 'camera_lens_mount': self.questions['Lens Mount*'].get(),
                 'camera_firmware': self.questions['Firmware/OS'].get(),
                 'camera_version': self.questions['Firmware/OS Version'].get()
        }
        data = self.json_string(data)

        return requests.post(url, headers=headers, data=data)

    def json_string(self, data):
        """
        Convert a dictionary of camera data to a string. Also changes empty strings in the dict to None
        :param data: dictionary containing camera data
        :return: string version of data
        """
        for key, val in data.iteritems():
            if val == '':
                data[key] = None
        for configuration in data['exif']:
            for key, val in configuration.iteritems():
                if val == '':
                    configuration[key] = None
        return json.dumps(data)

    def local_id_used(self):
        """
        Check if a user-entered local ID is already in use
        :return: (string) Error message (if error), otherwise None
        """
        print 'Verifying local ID is not already in use...'
        c = API_Camera_Handler(self, token=self.browser_token.get(), url=self.master.settings.get_key("apiurl"), given_id=self.questions["Local ID*"].get())
        local_id_reference = c.get_local_ids()
        if self.questions['Local ID*'].get().lower() in [i.lower() for i in local_id_reference]:
            return 'Local ID ' + self.questions['Local ID*'].get() + ' already in use.'

    def open_link(self, link):
        """
        Open a web browser link
        :param link: string containing website to open
        :return: None
        """
        webbrowser.open(link)

    def post_to_trello(self):
        """create a new card in trello and attach a file to it"""

        token = self.trello_token.get()

        # list ID for "New Devices" list
        list_id = data_files._TRELLO['camera_update_list']

        # post the new card
        new = self.questions['Local ID*'].get()
        resp = requests.post("https://trello.com/1/cards", params=dict(key=self.trello_key, token=token),
                             data=dict(name='NEW DEVICE: ' + new, idList=list_id))

        # attach the file and user, if the card was successfully posted
        if resp.status_code == requests.codes.ok:
            j = json.loads(resp.content)

            me = requests.get("https://trello.com/1/members/me", params=dict(key=self.trello_key, token=token))
            member_id = json.loads(me.content)['id']
            new_card_id = j['id']
            resp2 = requests.post("https://trello.com/1/cards/%s/idMembers" % (new_card_id),
                                  params=dict(key=self.trello_key, token=token),
                                  data=dict(value=member_id))
            return None
        else:
            return resp.status_code

class SectionFrame(Frame):
    """
    Question template for new camera form
    """
    def __init__(self, master, title, descr, type, items=None, **kwargs):
        Frame.__init__(self, master, **kwargs)
        self.title = title
        self.descr = descr
        self.type = type
        self.items = items # list items, if combobox type
        self.val = StringVar()
        self.row = 0
        self.create_form_item()

    def create_form_item(self):
        self._title = Label(self, text=self.title, font=(20))
        self._title.grid(row=self.row)
        self.row+=1
        self._descr = Label(self, text=self.descr, wraplength=350)
        self._descr.grid(row=self.row)
        self.row+=1
        if 'list' in self.type:
            self._form = ttk.Combobox(self, textvariable=self.val, values=self.items)
            self._form.bind('<MouseWheel>', self.remove_bind)
        elif 'radiobutton' in self.type:
            for item in self.items:
                if item.lower().startswith('other'):
                    Label(self, text='Other - Please specify: ').grid(row=self.row)
                    self._form = Entry(self, textvar=self.val)
                else:
                    Radiobutton(self, text=item, variable=self.val, value=item).grid(row=self.row)
                self.row+=1
        else:
            self._form = Entry(self, textvar=self.val)

        if 'readonly' in self.type and hasattr(self, '_form'):
            self._form.config(state='readonly')

        if hasattr(self, '_form'):
            self._form.grid(row=self.row)

    def remove_bind(self, event):
        return 'break'

    def get(self):
        return str(self.val.get())

    def set(self, val):
        self.val.set(str(val))

    def disable(self):
        if hasattr(self, '_form'):
            self._form.config(state='disabled')

    def enable(self):
        if hasattr(self, '_form'):
            self._form.config(state='normal')

    def edit_items(self, new_vals):
        self._form['values'] = new_vals

    def remove_required(self):
        self._title['text'] = self._title['text'][:-1] if self._title['text'].endswith("*") else self._title['text']

    def add_required(self):
        self._title['text'] = self._title['text'] + "*" if not self._title['text'].endswith("*") else self._title['text']

    def rename(self, title, desc):
        self._title['text'] = title if title else self._title['text']
        self._descr['text'] = desc if desc else self._descr['text']

class Update_Form(Toplevel):
    """
    Functions for updating a device. Accessed via File -> Update a Device in main menu. User must have valid browser
    login set in settings.
    """
    def __init__(self, master, device_data, trello=None, browser=None):
        Toplevel.__init__(self, master)
        self.master = master
        self.device_data = device_data
        self.trello = trello
        self.browser = browser
        self.configurations = {'exif_device_serial_number':[],'exif_camera_make':[], 'exif_camera_model':[], 'hp_app':[],
                               'media_type':[], 'username':[], 'created':[]}
        self.row = 0
        self.config_count = 0
        self.updated = False
        self.create_widgets()

    def create_widgets(self):
        self.f = VerticalScrolledFrame(self)
        self.f.pack(fill=BOTH, expand=TRUE)
        self.buttonsFrame = Frame(self)
        self.buttonsFrame.pack(fill=BOTH, expand=True)
        Label(self.f.interior, text='Updating Device:\n' + self.device_data['hp_device_local_id'], font=('bold', 20)).grid(columnspan=8)
        self.row+=1
        Label(self.f.interior, text='Shown below are the current exif configurations for this camera.').grid(row=self.row, columnspan=8)
        self.row+=1
        Button(self.f.interior, text='Show instructions for this form', command=self.show_help).grid(row=self.row, columnspan=8)
        self.row+=1
        col = 1
        for header in ['Serial', 'Make', 'Model', 'Software/App', 'Media Type', 'Username', 'Created']:
            Label(self.f.interior, text=header).grid(row=self.row, column=col)
            col+=1

        self.row += 1
        self.add_button = self.create_add_button()
        self.add_button.grid(row=self.row, columnspan=8)

        for configuration in self.device_data['exif']:
            self.add_config(configuration=configuration)

        ok = Button(self.buttonsFrame, text='Ok', command=self.go, width=20, bg='green')
        ok.pack()

        cancel = Button(self.buttonsFrame, text='Cancel', command=self.cancel, width=20)
        cancel.pack()

    def add_config(self, configuration):
        """
        Controls the mechanism for adding a new exif configuration
        :param configuration: dictionary containing exif fields shown in ordered dict
        :return: None
        """
        if hasattr(self, 'add_button'):
            self.add_button.grid_forget()
        col = 0
        self.row += 1
        stringvars = collections.OrderedDict([('exif_device_serial_number', StringVar()), ('exif_camera_make', StringVar()),
                                              ('exif_camera_model', StringVar()), ('hp_app', StringVar()),
                                              ('media_type', StringVar()), ('username', StringVar()), ('created', StringVar())])
        Label(self.f.interior, text='Config: ' + str(self.config_count + 1)).grid(row=self.row, column=col)
        col += 1
        for k, v in stringvars.iteritems():
            if configuration[k] is None:
                v.set('')
            else:
                v.set(configuration[k])
            if k == 'media_type':
                e = ttk.Combobox(self.f.interior, values=['image', 'video', 'audio'], state='readonly', textvariable=v)
            else:
                e = Entry(self.f.interior, textvar=v)
                if k != 'hp_app':
                    e.config(state=DISABLED)
            e.grid(row=self.row, column=col)
            self.configurations[k].append(v)
            col += 1
        self.config_count+=1
        self.row+=1
        self.add_button = self.create_add_button()
        self.add_button.grid(row=self.row, columnspan=8)

    def create_add_button(self):
        return Button(self.f.interior, text='Add a new configuration', command=self.get_data)

    def go(self):
        """
        Posts the camera update, and notifies trello if option is selected.
        :return: None. Should pop up box with status when complete.
        """
        url = self.master.settings.get_key('apiurl') + '/cameras/' + str(self.device_data['id']) + '/'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token ' + self.browser,
        }
        data = self.prepare_data()
        if data is None:
            return

        r = requests.put(url, headers=headers, data=data)
        if r.status_code in (requests.codes.ok, requests.codes.created):
            if tkMessageBox.askyesno(title='Done!', message='Camera updated. Post notification to Trello?', parent=self):
                self.camupdate_notify_trello(url)

            with open(data_files._LOCALDEVICES, 'r+') as j:
                local = json.load(j)
                for item in local:
                    if item == self.device_data['hp_device_local_id']:
                        local[item] = data
                        break
                new = json.dumps(local, indent=4)
                j.write(new)

            self.updated = True
            self.destroy()
        else:
            tkMessageBox.showerror(title='Error', message='An error occurred updating this device. (' + str(r.status_code) + ')', parent=self)

    def prepare_data(self):
        """
        Parse out exif data for posting on browser. Ensures no duplicates are created and assigns username/createdate.
        :return: string-formatted json data with the new exif data
        """
        data = {'exif':[]}
        for i in range(len(self.configurations['exif_camera_make'])):
            data['exif'].append({'exif_camera_make':self.configurations['exif_camera_make'][i].get(),
                         'exif_camera_model':self.configurations['exif_camera_model'][i].get(),
                         'hp_app': self.configurations['hp_app'][i].get(),
                         'media_type': self.configurations['media_type'][i].get(),
                         'exif_device_serial_number': self.configurations['exif_device_serial_number'][i].get()})
            if self.configurations['created'][i].get() != 'ToBeSetOnUpdate' and self.configurations['username'][i].get() != 'ToBeSetOnUpdate':
                data['exif'][i]['created'] = self.configurations['created'][i].get()
                data['exif'][i]['username'] = self.configurations['username'][i].get()

        for configuration in data['exif']:
            for key, val in configuration.iteritems():
                if val == '':
                    configuration[key] = None
                if key == 'media_type' and val == '':
                    configuration[key] = 'image'

        # remove duplicate entries
        data = [dict(t) for t in set([tuple(d.items()) for d in data['exif']])]
        return json.dumps({'exif':data})

    def camupdate_notify_trello(self, link):
        """
        Trello notifier. Posts a new card on update with user and details.
        :param link: Link to device
        :return: None. Message pop-up.
        """

        # list ID for "New Devices" list
        trello_key = data_files._TRELLO['app_key']
        list_id = data_files._TRELLO['camera_update_list']
        link = self.master.settings.get_key("apiurl")[:-4] + '/camera/' + str(self.device_data['id'])

        # post the new card
        title = 'Camera updated: ' + self.device_data['hp_device_local_id']
        resp = requests.post("https://trello.com/1/cards", params=dict(key=trello_key, token=self.trello),
                             data=dict(name=title, idList=list_id, desc=link))

        # attach the user, if successfully posted.
        if resp.status_code == requests.codes.ok:
            j = json.loads(resp.content)
            me = requests.get("https://trello.com/1/members/me", params=dict(key=trello_key, token=self.trello))
            member_id = json.loads(me.content)['id']
            new_card_id = j['id']
            resp2 = requests.post("https://trello.com/1/cards/%s/idMembers" % (new_card_id),
                                  params=dict(key=trello_key, token=self.trello),
                                  data=dict(value=member_id))
            tkMessageBox.showinfo(title='Information', message='Complete!', parent=self)
        else:
            tkMessageBox.showerror(title='Error', message='An error occurred connecting to trello (' + str(resp.status_code) + '). The device was still updated.')

    def show_help(self):
        tkMessageBox.showinfo(title='Instructions',
                              parent=self,
                              message='Occasionally, cameras can have different metadata for make and model for image vs. video, or for different apps. '
                                    'This usually results in errors in HP data processing, as the tool checks the data on record.\n\n'
                                    'If the device you\'re using has different metadata than what is on the browser for that device, add a new configuration by clicking the "Add a new configuration" button. '
                                    'You will be prompted to choose a file from that camera with the new metadata.\n\n'
                                    'Be sure to enter the media type, and if there was a particular App that was used with this media file, enter that as well in the respective field.'
                                    'Press Ok to push the changes to the browser, or Cancel to cancel the process.')

    def cancel(self):
        self.destroy()

    def get_data(self):
        """
        Parse out EXIF metadata from a sample media file.
        :return: None. Calls add_config()
        """
        self.imfile = tkFileDialog.askopenfilename(title='Select Media File', parent=self)
        if self.imfile in ('', None):
            return
        args = ['exiftool', '-f', '-j', '-Model', '-Make', '-SerialNumber', self.imfile]
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
            exifData = json.loads(p)[0]
        except:
            self.master.statusBox.println('An error ocurred attempting to pull exif data from image. Check exiftool install.')
            return
        exifData['Make'] = exifData['Make'] if exifData['Make'] != '-' else ''
        exifData['Model'] = exifData['Model'] if exifData['Model'] != '-' else ''
        exifData['SerialNumber'] = exifData['SerialNumber'] if exifData['SerialNumber'] != '-' else ''

        global exts
        if os.path.splitext(self.imfile)[1].lower() in exts['VIDEO']:
            type = 'video'
        elif os.path.splitext(self.imfile)[1].lower() in exts['AUDIO']:
            type = 'audio'
        else:
            type = 'image'

        new_config = {'exif_device_serial_number': exifData['SerialNumber'], 'exif_camera_model': exifData['Model'],
                         'exif_camera_make': exifData['Make'], 'hp_app': None, 'media_type': type,
                         'username': 'ToBeSetOnUpdate', 'created': 'ToBeSetOnUpdate'}
        self.add_config(new_config)


class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame that actually works!
    http://stackoverflow.com/questions/16188420/python-tkinter-scrollbar-for-frame
    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling

    """
    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        self.canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=self.canvas.yview)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        # reset the view
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(self.canvas)
        interior_id = self.canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            self.canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != self.canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                self.canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != self.canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                self.canvas.itemconfigure(interior_id, width=self.canvas.winfo_width())
        self.canvas.bind('<Configure>', _configure_canvas)

    def on_mousewheel(self, event):
        if sys.platform.startswith('win'):
            self.canvas.yview_scroll(-1*(event.delta/120), "units")
        else:
            self.canvas.yview_scroll(-1*(event.delta), "units")
