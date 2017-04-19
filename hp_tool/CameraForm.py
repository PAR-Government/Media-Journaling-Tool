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


class HP_Device_Form(Toplevel):
    def __init__(self, master, validIDs=None, pathvar=None, token=None):
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
        self.token = StringVar()
        self.token.set(token) if token is not None else ''

        self.create_widgets()
        self.trello_key = 'dcb97514b94a98223e16af6e18f9f99e'

    def set_list_options(self):
        df = pd.read_csv(os.path.join('data', 'db.csv'))
        self.manufacturers = [str(x).strip() for x in df['Manufacturer'] if str(x).strip() != 'nan']
        self.lens_mounts = [str(y).strip() for y in df['LensMount'] if str(y).strip() != 'nan']
        self.device_types = [str(z).strip() for z in df['DeviceType'] if str(z).strip() != 'nan']

    def create_widgets(self):
        self.f = VerticalScrolledFrame(self)
        self.f.pack(fill=BOTH, expand=TRUE)

        Label(self.f.interior, text='Add a new HP Device', font=("Courier", 20)).pack()
        Label(self.f.interior, text='Once complete, post the resulting text file to the \"New Devices to be Added\" list on the \"High Provenance\" trello board.').pack()

        Label(self.f.interior, text='Example Image', font=("Courier", 20)).pack()
        Label(self.f.interior, text='Some data on this form may be auto-populated using metadata from a sample image.').pack()
        self.imageButton = Button(self.f.interior, text='Select Image', command=self.populate_from_image)
        self.imageButton.pack()

        head = [('Device Affiliation*', {'description': 'If it is a personal device, please define the affiliation as Other, and write in your organization and your initials, e.g. RIT-TK',
                                 'type': 'radiobutton', 'values': ['RIT', 'PAR', 'Other (please specify):'], 'var':self.affiliation}),
               ('Define the Local ID*',{'description':'This can be a one of a few forms. The most preferable is the cage number. If it is a personal device, you can use INITIALS-MAKE, such as'
                                 ' ES-iPhone4. Please check that the local ID is not already in use.', 'type':'text', 'var':self.localID}),
               ('Device Serial Number',{'description':'Please enter the serial number shown in the image\'s exif data. If not available, enter the SN marked on the device body',
                                 'type':'text', 'var':self.serial}),
               ('Manufacturer*',{'description':'', 'type':'list', 'values':self.manufacturers, 'var':self.manufacturer}),
               ('Series Model*',{'description':'Please write the series or model such as it would be easily identifiable, such as Galaxy S6', 'type':'text',
                                 'var':self.series_model}),
               ('Camera Model*',{'description':'If Camera Model appears in Exif data, please enter it here (ex. SM-009', 'type':'text',
                                 'var':self.camera_model}),
               ('Edition',{'description':'If applicable', 'type':'text', 'var':self.edition}),
               ('Device Type*',{'description':'', 'type':'list', 'values':self.device_types, 'var':self.device_type}),
               ('Sensor Information',{'description':'', 'type':'text', 'var':self.sensor}),
               ('General Description',{'description':'Other specifications', 'type':'text', 'var':self.general}),
               ('Lens Mount*',{'description':'Choose \"builtin\" if the device does not have interchangeable lenses.', 'type':'list', 'values':self.lens_mounts,
                                 'var':self.lens_mount}),
               ('Firmware/OS',{'description':'Firmware/OS', 'type':'text', 'var':self.os}),
               ('Firmware/OS Version',{'description':'Firmware/OS Version', 'type':'text', 'var':self.osver})
        ]
        self.headers = collections.OrderedDict(head)

        r=0
        for h in self.headers:
            Label(self.f.interior, text=h, font=("Courier", 20)).pack()
            r+=1
            if 'description' in self.headers[h]:
                Label(self.f.interior, text=self.headers[h]['description'], wraplength=600).pack()
                r+=1
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
                    r+=1

            elif self.headers[h]['type'] == 'list':
                ttk.Combobox(self.f.interior, values=self.headers[h]['values'], textvariable=self.headers[h]['var']).pack()

            r+=1

        self.headers['Device Affiliation*']['var'].set('RIT')

        Label(self.f.interior, text='Trello Login Token*', font=("Courier", 20)).pack()
        Label(self.f.interior, text='If not supplied, you will need to manually post the output text file from this form onto the proper Trello board.').pack()
        apiTokenButton = Button(self.f.interior, text='Get Trello Token', command=self.open_trello_token)
        apiTokenButton.pack()
        tokenEntry = Entry(self.f.interior, textvar=self.token)
        tokenEntry.pack()

        self.okbutton = Button(self.f.interior, text='Complete', command=self.export_results)
        self.okbutton.pack()
        self.cancelbutton = Button(self.f.interior, text='Cancel', command=self.destroy)
        self.cancelbutton.pack()

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
            self.serial.set(exifData['SerialNUmber'])

    def export_results(self):
        msg = None
        for h in self.headers:
            if h.endswith('*') and self.headers[h]['var'].get() == '':
                msg = 'Field ' + h[:-1] + ' is a required field.'
                break
        if self.token.get() == '':
            msg = 'Trello Token is a required field.'
        if self.local_id_used():
            msg = 'Local ID ' + self.localID.get() + ' already in use.'

        if msg:
            tkMessageBox.showerror(title='Error', message=msg)
            return

        path = tkFileDialog.asksaveasfilename(initialfile=self.localID.get()+'.csv')
        with open(path, 'wb') as csvFile:
            wtr = csv.writer(csvFile)
            wtr.writerow(['Affiliation', 'HP-LocalDeviceID', 'DeviceSN', 'Manufacturer', 'CameraModel', 'HP-CameraModel', 'Edition',
                          'DeviceType', 'Sensor', 'Description', 'LensMount', 'Firmware', 'version', 'HasPRNUData'])
            wtr.writerow([self.affiliation.get(), self.localID.get(), self.serial.get(), self.manufacturer.get(), self.camera_model.get(),
                          self.series_model.get(), self.edition.get(), self.device_type.get(), self.sensor.get(), self.general.get(),
                          self.lens_mount.get(), self.os.get(), self.osver.get(), '0'])
        if self.pathvar:
            self.pathvar.set(path)

        code = self.post_to_trello(path)
        if code is not None:
            tkMessageBox.showerror('Trello Error', message='An error ocurred connecting to trello (' + str(code) + ').\nIf you\'re not sure what is causing this error, email medifor_manipulators@partech.com.')
        else:
            tkMessageBox.showinfo(title='Information', message='Complete!')

        self.destroy()

    def local_id_used(self):
        return self.localID.get().lower() in [i.lower() for i in self.validIDs]

    def open_trello_token(self):
        webbrowser.open('https://trello.com/1/authorize?key='+self.trello_key+'&scope=read%2Cwrite&name=HP_GUI&expiration=never&response_type=token')


    def post_to_trello(self, filepath):
        """create a new card in trello and attach a file to it"""

        token = self.token.get()

        # list ID for "New Devices" list
        list_id = '58ecda84d8cfce408d93dd34'

        # post the new card
        new = self.localID.get()
        resp = requests.post("https://trello.com/1/cards", params=dict(key=self.trello_key, token=token),
                             data=dict(name=new, idList=list_id))

        # attach the file, if the card was successfully posted
        if resp.status_code == requests.codes.ok:
            j = json.loads(resp.content)
            files = {'file': open(filepath, 'rb')}
            requests.post("https://trello.com/1/cards/%s/attachments" % (j['id']),
                          params=dict(key=self.trello_key, token=token), files=files)
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