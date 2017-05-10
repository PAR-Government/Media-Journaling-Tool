import csv
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

class HP_Device_Form(Toplevel):
    def __init__(self, master, validIDs=None, pathvar=None, token=None, browser=None):
        Toplevel.__init__(self, master)
        self.geometry("%dx%d%+d%+d" % (800, 800, 250, 125))
        self.master = master
        self.pathvar = pathvar # use this to set a tk variable to the path of the output txt file
        self.validIDs = validIDs if validIDs is not None else []
        self.set_list_options()

        self.affiliation = StringVar()
        self.localID = StringVar()
        self.serial = StringVar()
        self.manufacturer = StringVar()
        self.series_model = StringVar()
        self.camera_model = StringVar()
        self.edition = StringVar()
        self.device_type = StringVar()
        self.sensor = StringVar()
        self.general = StringVar()
        self.lens_mount = StringVar()
        self.os = StringVar()
        self.osver = StringVar()
        self.trello_token = StringVar()
        self.trello_token.set(token) if token is not None else ''
        self.browser_token = StringVar()
        self.browser_token.set(browser) if browser is not None else ''

        self.trello_key = 'dcb97514b94a98223e16af6e18f9f99e'
        self.create_widgets()


    def set_list_options(self):
        df = pd.read_csv(os.path.join('data', 'db.csv'))
        self.manufacturers = [str(x).strip() for x in df['Manufacturer'] if str(x).strip() != 'nan']
        self.lens_mounts = [str(y).strip() for y in df['LensMount'] if str(y).strip() != 'nan']
        self.device_types = [str(z).strip() for z in df['DeviceType'] if str(z).strip() != 'nan']

    def create_widgets(self):
        self.f = VerticalScrolledFrame(self)
        self.f.pack(fill=BOTH, expand=TRUE)

        Label(self.f.interior, text='Add a new HP Device', font=('bold', 20)).pack()
        Label(self.f.interior, text='Once complete, post the resulting text file to the \"New Devices to be Added\" list on the \"High Provenance\" trello board.').pack()

        Label(self.f.interior, text='Example Image', font=(20)).pack()
        Label(self.f.interior, text='Some data on this form may be auto-populated using metadata from a sample image.').pack()
        self.imageButton = Button(self.f.interior, text='Select Image', command=self.populate_from_image)
        self.imageButton.pack()

        head = [('Device Affiliation*', {'description': 'If it is a personal device, please define the affiliation as Other, and write in your organization and your initials, e.g. RIT-TK',
                                 'type': 'radiobutton', 'values': ['RIT', 'PAR', 'Other (please specify):'], 'var':self.affiliation}),
               ('Define the Local ID*',{'description':'This can be a one of a few forms. The most preferable is the cage number. If it is a personal device, you can use INITIALS-MAKE, such as'
                                 ' ES-iPhone4. Please check that the local ID is not already in use.', 'type':'text', 'var':self.localID}),
               ('Device Serial Number',{'description':'Please enter the serial number shown in the image\'s exif data. If not available, enter the SN marked on the device body',
                                 'type':'text', 'var':self.serial}),
               ('Manufacturer*',{'description':'Device make.', 'type':'list', 'values':self.manufacturers, 'var':self.manufacturer}),
               ('Series Model*',{'description':'Please write the series or model such as it would be easily identifiable, such as Galaxy S6.', 'type':'text',
                                 'var':self.series_model}),
               ('Camera Model',{'description':'If Camera Model appears in image/video exif data from this camera, please enter it here (ex. SM-009). If there is no model listed in exif data, leave blank.', 'type':'text',
                                 'var':self.camera_model}),
               ('Edition',{'description':'If applicable', 'type':'text', 'var':self.edition}),
               ('Device Type*',{'description':'', 'type':'readonlylist', 'values':self.device_types, 'var':self.device_type}),
               ('Sensor Information',{'description':'Sensor size/dimensions/other sensor info.', 'type':'text', 'var':self.sensor}),
               ('General Description',{'description':'Other specifications', 'type':'text', 'var':self.general}),
               ('Lens Mount*',{'description':'Choose \"builtin\" if the device does not have interchangeable lenses.', 'type':'list', 'values':self.lens_mounts,
                                 'var':self.lens_mount}),
               ('Firmware/OS',{'description':'Firmware/OS', 'type':'text', 'var':self.os}),
               ('Firmware/OS Version',{'description':'Firmware/OS Version', 'type':'text', 'var':self.osver})
        ]
        self.headers = collections.OrderedDict(head)

        for h in self.headers:
            Label(self.f.interior, text=h, font=(20)).pack()
            if 'description' in self.headers[h]:
                Label(self.f.interior, text=self.headers[h]['description'], wraplength=600).pack()
            if self.headers[h]['type'] == 'text':
                e = Entry(self.f.interior, textvar=self.headers[h]['var'])
                e.pack()
            elif self.headers[h]['type'] == 'radiobutton':
                for v in self.headers[h]['values']:
                    if v.lower().startswith('other'):
                        Label(self.f.interior, text='Other - Please specify below: ').pack()
                        e = Entry(self.f.interior, textvar=self.headers[h]['var'])
                        e.pack()
                    else:
                        Radiobutton(self.f.interior, text=v, variable=self.headers[h]['var'], value=v).pack()

            elif 'list' in self.headers[h]['type']:
                c = ttk.Combobox(self.f.interior, values=self.headers[h]['values'], textvariable=self.headers[h]['var'])
                c.pack()
                c.bind('<MouseWheel>', self.remove_bind)
                if 'readonly' in self.headers[h]['type']:
                    c.config(state='readonly')

        self.headers['Device Affiliation*']['var'].set('RIT')

        Label(self.f.interior, text='Trello Login Token*', font=(20)).pack()
        Label(self.f.interior, text='This is required to send a notification of the new device.').pack()
        trello_link = 'https://trello.com/1/authorize?key=' + self.trello_key + '&scope=read%2Cwrite&name=HP_GUI&expiration=never&response_type=token'
        trelloTokenButton = Button(self.f.interior, text='Get Trello Token', command=lambda: self.open_link(trello_link))
        trelloTokenButton.pack()
        tokenEntry = Entry(self.f.interior, textvar=self.trello_token)
        tokenEntry.pack()

        Label(self.f.interior, text='Browser Login Token*', font=(20)).pack()
        Label(self.f.interior, text='This allows for the creation of the new device.').pack()
        browser_link = 'https://medifor.rankone.io/api/login/'
        browserTokenButton = Button(self.f.interior, text='Get Trello Token', command=lambda: self.open_link(browser_link))
        browserTokenButton.pack()
        browserEntry = Entry(self.f.interior, textvar=self.browser_token)
        browserEntry.pack()

        self.okbutton = Button(self.f.interior, text='Complete', command=self.export_results)
        self.okbutton.pack()
        self.cancelbutton = Button(self.f.interior, text='Cancel', command=self.destroy)
        self.cancelbutton.pack()

    def remove_bind(self, event):
        return 'break'

    def populate_from_image(self):
        self.imfile = tkFileDialog.askopenfilename(title='Select Image File')
        self.imageButton.config(text=os.path.basename(self.imfile))
        args = ['exiftool', '-f', '-j', '-Model', '-Make', '-SerialNumber', self.imfile]
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
            exifData = json.loads(p)[0]
        except:
            self.master.statusBox.println('An error ocurred attempting to pull exif data from image.')
            return
        if exifData['Make'] != '-':
            self.manufacturer.set(exifData['Make'])
        if exifData['Model']:
            self.camera_model.set(exifData['Model'])
        if exifData['SerialNumber'] != '-':
            self.serial.set(exifData['SerialNumber'])

    def export_results(self):
        msg = None
        for h in self.headers:
            if h.endswith('*') and self.headers[h]['var'].get() == '':
                msg = 'Field ' + h[:-1] + ' is a required field.'
                break
        if self.trello_token.get() == '':
            msg = 'Trello Token is a required field.'
        if self.browser_token.get() == '':
            msg = 'Browser Token is a required field.'
        check = self.local_id_used()
        msg = msg if check is None else check

        if msg:
            tkMessageBox.showerror(title='Error', message=msg)
            return

        browser_resp = self.post_to_browser()
        if browser_resp.status_code == requests.codes.ok:
            tkMessageBox.showinfo(title='Complete', message='Successfully posted new camera information! Press Okay to continue.')
        else:
            tkMessageBox.showerror(title='Error', message='An error ocurred posting the new camera information to the MediBrowser. (' + str(browser_resp.status_code)) + ')'

        path = tkFileDialog.asksaveasfilename(initialfile=self.localID.get()+'.csv')
        if self.pathvar:
            self.pathvar.set(path)
        with open(path, 'wb') as csvFile:
            wtr = csv.writer(csvFile)
            wtr.writerow(['Affiliation', 'HP-LocalDeviceID', 'DeviceSN', 'Manufacturer', 'CameraModel', 'HP-CameraModel', 'Edition',
                          'DeviceType', 'Sensor', 'Description', 'LensMount', 'Firmware', 'version', 'HasPRNUData'])
            wtr.writerow([self.affiliation.get(), self.localID.get(), self.serial.get(), self.manufacturer.get(), self.camera_model.get(),
                          self.series_model.get(), self.edition.get(), self.device_type.get(), self.sensor.get(), self.general.get(),
                          self.lens_mount.get(), self.os.get(), self.osver.get(), '0'])

        code = self.post_to_trello(path)
        if code is not None:
            tkMessageBox.showerror('Trello Error', message='An error ocurred connecting to trello (' + str(code) + ').\nIf you\'re not sure what is causing this error, email medifor_manipulators@partech.com.')
        else:
            tkMessageBox.showinfo(title='Information', message='Complete!')

        self.destroy()

    def post_to_browser(self):
        url = 'https://medifor.rankone.io/api/cameras/'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token ' + self.browser_token.get(),
        }
        data = { 'hp_device_local_id': self.localID.get(),
                 'affiliation': self.affiliation.get(),
                 'hp_camera_model': self.series_model.get(),
                 'exif_device_serial_number': self.serial.get(),
                 'exif_camera_make': self.manufacturer.get(),
                 'exif_camera_model': self.camera_model.get(),
                 'camera_edition': self.edition.get(),
                 'camera_type': self.device_type.get(),
                 'camera_sensor': self.sensor.get(),
                 'camera_description': self.general.get(),
                 'camera_lens_mount': self.lens_mount.get(),
                 'camera_firmware': self.os.get(),
                 'camera_version': self.osver.get()
        }
        data = self.json_string(data)

        return requests.post(url, headers=headers, data=data)

    def json_string(self, data):
        for key, val in data.iteritems():
            if val == '':
                data[key] = None
        return json.dumps(data)

    def local_id_used(self):
        print 'Verifying local ID is not already in use...'
        c = API_Camera_Handler(self, token=self.browser_token.get(), url='https://medifor.rankone.io')
        local_id_reference = c.get_local_ids()
        if not local_id_reference:
            return 'Could not successfully connect to Medifor browser. Please check credentials.'
        elif self.localID.get().lower() in [i.lower() for i in local_id_reference]:
            return 'Local ID ' + self.localID.get() + ' already in use.'

    def open_link(self, link):
        webbrowser.open(link)

    def post_to_trello(self, filepath):
        """create a new card in trello and attach a file to it"""

        token = self.trello_token.get()

        # list ID for "New Devices" list
        list_id = '58ecda84d8cfce408d93dd34'

        # post the new card
        new = self.localID.get()
        resp = requests.post("https://trello.com/1/cards", params=dict(key=self.trello_key, token=token),
                             data=dict(name=new, idList=list_id))

        # attach the file and user, if the card was successfully posted
        if resp.status_code == requests.codes.ok:
            j = json.loads(resp.content)
            files = {'file': open(filepath, 'rb')}
            requests.post("https://trello.com/1/cards/%s/attachments" % (j['id']),
                          params=dict(key=self.trello_key, token=token), files=files)

            me = requests.get("https://trello.com/1/members/me", params=dict(key=self.trello_key, token=token))
            member_id = json.loads(me.content)['id']
            new_card_id = j['id']
            resp2 = requests.post("https://trello.com/1/cards/%s/idMembers" % (new_card_id),
                                  params=dict(key=self.trello_key, token=token),
                                  data=dict(value=member_id))
            return None
        else:
            return resp.status_code


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
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

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