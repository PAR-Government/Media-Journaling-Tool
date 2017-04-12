import tarfile
import tkSimpleDialog
from Tkinter import *
import ttk
import collections
import tempfile
import boto3
import matplotlib
import requests
matplotlib.use("TkAgg")
import pandastable
import pandas
import shutil
import ttk
import tkFileDialog
import tkMessageBox
import numpy as np
import webbrowser
from hp_data import *
from HPSpreadsheet import HPSpreadsheet
from KeywordsSheet import KeywordsSheet
from prefs import Preferences

class HP_Starter(Frame):

    def __init__(self, master=None, prefs=None):
        Frame.__init__(self, master)
        self.master=master
        self.prefs = prefs
        self.prefsfilename = (os.path.join('data', 'preferences.txt'))
        self.metadatafilename = StringVar()
        self.metadatafilename.set(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'metadata.txt'))
        self.grid()
        self.oldImageNames = []
        self.newImageNames = []
        self.createWidgets()
        self.load_defaults()

    def update_defaults(self):
        tmpFileName = os.path.join('data', 'tmp.txt')
        insertInputDir = True
        insertOutputDir = True
        with open(tmpFileName, 'wb') as new:
            with open(self.prefsfilename, 'rb') as original:
                for line in original:
                    if line.startswith('inputdir'):
                        new.write('inputdir=' + self.inputdir.get() + '\n')
                        insertInputDir = False
                    elif line.startswith('outputdir'):
                        new.write('outputdir=' + self.outputdir.get() + '\n')
                        insertOutputDir = False
                    else:
                        new.write(line)
                        if not line.endswith('\n'):
                            new.write('\n')
            if insertInputDir:
                new.write('\ninputdir=' + self.inputdir.get())
            if insertOutputDir:
                new.write('\noutputdir=' + self.outputdir.get())
        os.remove(self.prefsfilename)
        shutil.move(tmpFileName, self.prefsfilename)

    def load_defaults(self):
        if self.prefs:
            if 'inputdir' in self.prefs:
                self.inputdir.insert(END, self.prefs['inputdir'])
            else:
                self.inputdir.insert(END, os.getcwd())

            if 'outputdir' in self.prefs:
                self.outputdir.insert(END, self.prefs['outputdir'])
            else:
                self.outputdir.insert(END, os.getcwd())
        else:
            self.okbutton.config(state='disabled')


    def load_input(self):
        d = tkFileDialog.askdirectory(initialdir=self.inputdir.get())
        if d:
            self.inputdir.delete(0, 'end')
            self.inputdir.insert(0, d)

    def load_output(self):
        d = tkFileDialog.askdirectory(initialdir=self.outputdir.get())
        if d:
            self.outputdir.delete(0, 'end')
            self.outputdir.insert(0, d)

    def preview_filename(self):
        testNameStr = 'Please update preferences with username and organization'
        prefs = parse_prefs(self.prefsfilename)
        if prefs and prefs.has_key('seq'):
            testNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                        prefs['organization'] + prefs['username'] + '-' + prefs['seq']
            if self.additionalinfo.get():
                testNameStr += '-' + self.additionalinfo.get()
        tkMessageBox.showinfo('Filename Preview', testNameStr)


    def go(self):
        globalFields = ['HP-CollectionRequestID', 'HP-DeviceLocalID', 'HP-LensLocalID', 'HP-HDLocation']
        kwargs = {'preferences':self.prefsfilename,
                  'metadata':self.metadatafilename.get(),
                  'imgdir':self.inputdir.get(),
                  'outputdir':self.outputdir.get(),
                  'recursive':self.recBool.get(),
                  'additionalInfo':self.additionalinfo.get(),
                  }
        for fieldNum in xrange(len(globalFields)):
            kwargs[globalFields[fieldNum]] = self.attributes[self.descriptionFields[fieldNum]].get()

        self.update_defaults()

        (self.oldImageNames, self.newImageNames) = process(**kwargs)
        if self.oldImageNames == None:
            return
        aSheet = HPSpreadsheet(dir=self.outputdir.get(), master=self.master)
        aSheet.open_spreadsheet()
        self.keywordsbutton.config(state=NORMAL)
        keySheet = self.open_keywords_sheet()
        keySheet.close()

    def open_keywords_sheet(self):
        keywords = KeywordsSheet(dir=self.outputdir.get(), master=self.master, newImageNames=self.newImageNames, oldImageNames=self.oldImageNames)
        keywords.open_spreadsheet()
        return keywords

    def open_prefs(self):
        Preferences(master=self.master)
        if parse_prefs(self.prefsfilename):
            self.okbutton.config(state='normal')

    def createWidgets(self):
        self.recBool = BooleanVar()
        self.recBool.set(False)
        self.inputSelector = Button(self, text='Input directory: ', command=self.load_input, width=20)
        self.inputSelector.grid(row=0,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.recbox = Checkbutton(self, text='Include subdirectories', variable=self.recBool)
        self.recbox.grid(row=0, column=3, ipadx=5, ipady=5, padx=5, pady=5)
        self.inputdir = Entry(self)
        self.inputdir.grid(row=0, column=1, ipadx=5, ipady=5, padx=0, pady=5, columnspan=2)

        self.outputSelector = Button(self, text='Output directory: ', command=self.load_output, width=20)
        self.outputSelector.grid(row=0, column=4, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)
        self.outputdir = Entry(self, width=20)
        self.outputdir.grid(row=0, column=6, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)

        self.additionallabel = Label(self, text='Additional Text to add at end of new filenames: ')
        self.additionallabel.grid(row=1, column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=3)
        self.additionalinfo = Entry(self, width=10)
        self.additionalinfo.grid(row=1, column=3, ipadx=5, ipady=5, padx=5, pady=5, sticky='W')

        self.previewbutton = Button(self, text='Preview filename', command=self.preview_filename, bg='cyan')
        self.previewbutton.grid(row=1, column=4)

        self.changeprefsbutton = Button(self, text='Edit Preferences', command=self.open_prefs)
        self.changeprefsbutton.grid(row=1, column=6)

        self.sep1 = ttk.Separator(self, orient=HORIZONTAL).grid(row=2, columnspan=8, sticky='EW')
        self.descriptionFields = ['Coll. Request ID', 'Local Camera ID', 'Local Lens ID', 'Hard Drive Location']

        self.descriptionlabel = Label(self, text='Enter global camera information. This information cannot be pulled '
                                                 'from exif data.')
        self.descriptionlabel.grid(row=3,columnspan=8, sticky='W')
        row = 4
        col = 0
        self.attributes = {}
        for field in self.descriptionFields:
            self.attrlabel = Label(self, text=field).grid(row=row, column=col, ipadx=5, ipady=5, padx=5, pady=5)
            self.attributes[field] = Entry(self, width=10)
            self.attributes[field].grid(row=row, column=col+1, ipadx=0, ipady=5, padx=5, pady=5)
            col += 2
            if col == 8:
                row += 1
                col = 0

        lastLoc = self.attributes['Hard Drive Location'].grid_info()
        lastRow = int(lastLoc['row'])

        self.sep2 = ttk.Separator(self, orient=HORIZONTAL).grid(row=lastRow+1, columnspan=8, sticky='EW')

        self.okbutton = Button(self, text='Run ', command=self.go, width=20, bg='green')
        self.okbutton.grid(row=lastRow+2,column=0, ipadx=5, ipady=5, sticky='E')
        self.cancelbutton = Button(self, text='Cancel', command=self.quit, width=20, bg='red')
        self.cancelbutton.grid(row=lastRow+2, column=6, ipadx=5, ipady=5, padx=5, sticky='W')

        self.keywordsbutton = Button(self, text='Enter Keywords', command=self.open_keywords_sheet, state=DISABLED, width=20)
        self.keywordsbutton.grid(row=lastRow+2, column=2, ipadx=5, ipady=5, padx=5, sticky='E')

class PRNU_Uploader(Frame):
    def __init__(self, master=None, prefs=None):
        Frame.__init__(self, master)
        self.master = master
        self.prefs=prefs
        self.root_dir = StringVar()
        self.localID = StringVar()
        self.s3path = StringVar()
        self.parse_vocab(os.path.join('data', 'prnu_vocab.csv'))
        self.create_prnu_widgets()
        if 's3prnu' in prefs:
            self.s3path.set(prefs['s3prnu'])

    def create_prnu_widgets(self):
        dirbutton = Button(self, text='Root PRNU Directory:', command=self.open_dir, width=20)
        dirbutton.grid(row=0,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.rootEntry = Entry(self, width=100, textvar=self.root_dir)
        self.rootEntry.grid(row=0, column=1, ipadx=5, ipady=5, padx=0, pady=5, columnspan=4)

        localcamlabel = Label(self, text='Local Camera ID:', width=20).grid(row=1,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.localCamEntry = Entry(self, width=40, textvar=self.localID)
        self.localCamEntry.grid(row=1, column=1, ipadx=5, ipady=5, padx=0, pady=5, columnspan=2, sticky=W)

        verifyButton = Button(self, text='Verify Directory Structure', command=self.examine_dir, width=20)
        verifyButton.grid(row=3,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)

        self.s3Label = Label(self, text='S3 bucket/path: ').grid(row=3,column=1, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=E)

        self.s3Entry = Entry(self, width=40, textvar=self.s3path)
        self.s3Entry.grid(row=3, column=2, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=W)

        self.uploadButton = Button(self, text='Start Upload', command=self.upload, width=20, state=DISABLED, bg='green')
        self.uploadButton.grid(row=4,column=2, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=W)

        self.cancelButton = Button(self, text='Cancel', command=self.cancel_upload, width=20, bg='red')
        self.cancelButton.grid(row=4, column=1, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=E)

    def parse_vocab(self, path):
        self.vocab = []
        with open(path) as v:
            rdr = csv.reader(v)
            for row in rdr:
                self.vocab.append(row[0])
                for x in range(0, 101):
                    self.vocab.append(row[0] + '_' + str(x))

    def open_dir(self):
        self.root_dir.set(tkFileDialog.askdirectory())

    def examine_dir(self):
        passed_root = False
        msg = None

        for path, dirs, files in os.walk(self.root_dir.get()):
            p, last = os.path.split(path)
            if last == self.localID.get():
                passed_root = True
                if not self.has_same_contents(dirs, ['images', 'video']):
                    msg = 'Root PRNU directory must have \"Images\" and \"Video\" folers.'
                    break
                if files:
                    for f in files:
                        if f.startswith('.'):
                            os.remove(os.path.join(path, f))
                    msg = 'There should be no files in the root directory. Only \"Images\" and \"Video\" folders.'
                    break
            elif last.lower() in ['images', 'video']:
                if not self.has_same_contents(dirs, ['primary', 'secondary']):
                    msg = 'Images and Video folders must each contain Primary and Secondary folders.'
                if files:
                    for f in files:
                        if f.startswith('.'):
                            os.remove(os.path.join(path, f))
                    msg = 'There should be no additional files in the ' + last + ' directory. Only \"Primary\" and \"Secondary\".'
            elif last.lower() == 'primary' or last.lower() == 'secondary':
                for sub in dirs:
                    if sub.lower() not in self.vocab:
                        msg = 'Invalid reference type: ' + sub
                        break
                if files:
                    for f in files:
                        if f.startswith('.'):
                            os.remove(os.path.join(path, f))
                        else:
                            msg = 'There should be no additional files in the ' + last + ' directory. Only PRNU reference type folders (White_Screen, Blue_Sky, etc).'
                            break
            elif last.lower() in self.vocab:
                if dirs:
                    msg = 'There should be no additional subfolders in folder ' + path
                if files:
                    for f in files:
                        if f.startswith('.'):
                            os.remove(os.path.join(path, f))
                else:
                    msg = 'There are no images in: ' + path

        if passed_root == False or not local_id_used(self):
            msg = 'Invalid local ID: ' + self.localID.get() + '. This field is case sensitive, and must also match the name of the directory. Would you like to add a new device?'
            if tkMessageBox.askyesno(title='Unrecognized Local ID', message=msg):
                HP_Device_Form(self, prefs=self.prefs)
            msg = 'hide'

        if msg == 'hide':
            pass
        elif msg:
            tkMessageBox.showerror(title='Error', message=msg)
        else:
            tkMessageBox.showinfo(title='Complete', message='Everything looks good. Click \"Start Upload\" to begin upload.')
            self.uploadButton.config(state=NORMAL)
            self.rootEntry.config(state=DISABLED)
            self.localCamEntry.config(state=DISABLED)

    def has_same_contents(self, list1, list2):
        # set both lists to lowercase strings and checks if they have the same items, in any order
        llist1 = [x.lower() for x in list1]
        llist2 = [y.lower() for y in list2]
        return collections.Counter(llist1) == collections.Counter(llist2)

    def upload(self):
        self.capitalize_dirs()
        val = self.s3path.get()
        if (val is not None and len(val) > 0):
            self.prefs['s3prnu'] = val
            with open(os.path.join('data', 'preferences.txt'), 'w') as f:
                for key in self.prefs:
                    f.write(key + '=' + self.prefs[key] + '\n')

        # parse path
        s3 = boto3.client('s3', 'us-east-1')
        if val.startswith('s3://'):
            val = val[5:]
        BUCKET = val.split('/')[0].strip()
        DIR = val[val.find('/') + 1:].strip()
        DIR = DIR if DIR.endswith('/') else DIR + '/'

        print 'Creating archive...'
        archive = self.archive_prnu()

        print 'Uploading ' + archive.replace('\\', '/') + ' to s3://' + val,
        s3.upload_file(archive, BUCKET, DIR + os.path.split(archive)[1])

        os.remove(archive)

        tkMessageBox.showinfo(title='PRNU Upload', message='Complete!')
        print '... done'

        # reset state of buttons and boxes
        self.cancel_upload()

    def cancel_upload(self):
        self.uploadButton.config(state=DISABLED)
        self.rootEntry.config(state=NORMAL)
        self.localCamEntry.config(state=NORMAL)

    def archive_prnu(self):
        ftar = os.path.join(os.path.split(self.root_dir.get())[0], self.localID.get() + '.tar')
        archive = tarfile.open(ftar, "w", errorlevel=2)
        archive.add(self.root_dir.get(), arcname=os.path.split(self.root_dir.get())[1])
        archive.close()
        return ftar

    def capitalize_dirs(self):
        # http://stackoverflow.com/questions/3075443/python-recursively-remove-capitalisation-from-directory-structure
        # applied title capitalization to all subforders of a root dir, not including root itself
        def rename_all(root, items):
            for name in items:
                try:
                    os.rename(os.path.join(root, name),
                              os.path.join(root, name.title()))
                except OSError:
                    pass  # just skip if can't be renamed

        # starts from the bottom so paths further up remain valid after renaming
        for root, dirs, files in os.walk(self.root_dir.get(), topdown=False):
            rename_all(root, dirs)

    def export_local(self):
        # for testing purposes
        self.capitalize_dirs()
        archive = self.archive_prnu()
        shutil.copy(archive, os.getcwd())
        os.remove(archive)
        print 'done'

class HP_Device_Form(Toplevel):
    def __init__(self, master, prefs):
        Toplevel.__init__(self, master)
        #self.geometry("%dx%d%+d%+d" % (300, 300, 250, 125))
        self.master = master
        self.prefs = prefs
        self.set_list_options()
        self.create_widgets()

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

        self.email = StringVar()
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

        head = [('Email Address*', {'description':'','type':'text', 'var':self.email}),
                       ('Device Affiliation*', {'description': 'If it is a personal device, please define the affiliation as Other, and write in your organization and your initials, e.g. RIT-TK',
                                                 'type': 'radiobutton', 'values': ['RIT', 'PAR', 'Other (please specify):'], 'var':self.affiliation}),
                       ('Define the Local ID*',{'description':'This can be a one of a few forms. The most preferable is the cage number. If it is a personal device, you can use INITIALS-MAKE, such as'
                                                             'ES-iPhone4. Please check that the local ID is not already in use.', 'type':'text', 'var':self.localID}),
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
                Label(self.f.interior, text=self.headers[h]['description']).pack()
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

        self.okbutton = Button(self.f.interior, text='Export', command=self.export_results)
        self.okbutton.pack()
        self.cancelbutton = Button(self.f.interior, text='Cancel', command=self.destroy)
        self.cancelbutton.pack()

    def export_results(self):
        msg = None
        for h in self.headers:
            if h.endswith('*') and self.headers[h]['var'].get() == '':
                msg = 'Field ' + h[:-1] + ' is a required field.'
                break

        if local_id_used(self):
            msg = 'Local ID ' + self.localID.get() + ' already in use.'

        if msg:
            tkMessageBox.showerror(title='Error', message=msg)
            return

        with tkFileDialog.asksaveasfile('w', initialfile=self.localID.get()+'.txt') as t:
            for h in self.headers:
                if h.endswith('*'):
                    h = h[:-1]
                t.write(h + ' = ' + self.headers[h]['var'].get() + '\n')
        tkMessageBox.showinfo(title='Information', message='Export Complete!')
        self.destroy()


def local_id_used(self):
    try:
        headers = {'Authorization': 'Token ' + self.prefs['apitoken'], 'Content-Type': 'application/json'}
        url = self.prefs['apiurl'] + '/api/cameras/?fields=hp_device_local_id/'
        print 'Checking external service APIs for device local ID...'
        localIDs = []
        while True:
            response = requests.get(url, headers=headers)
            if response.status_code == requests.codes.ok:
                r = json.loads(response.content)
                for item in r['results']:
                    localIDs.append(item['hp_device_local_id'])
                url = r['next']
                if url is None:
                    break
            else:
                print 'HTTP Error ' + str(response.status_code) + '. Attempting to check with local device list....'
                raise requests.HTTPError()
    except (KeyError, requests.HTTPError, requests.ConnectionError):
        df = pd.read_csv(os.path.join('data', 'Devices.csv'))
        localIDs = [y.strip() for y in df['HP-LocalDeviceID']]

    if self.localID.get().lower() in [id.lower() for id in localIDs]:
        return True
    else:
        return False


class HPGUI(Frame):
    def __init__(self, master=None, **kwargs):
        Frame.__init__(self, master, **kwargs)
        self.master = master
        self.prefsfilename = StringVar()
        self.prefsfilename.set(os.path.join('data', 'preferences.txt'))
        self.load_defaults()
        self.create_widgets()

    def create_widgets(self):
        self.menubar = Menu(self)
        self.fileMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='File', menu=self.fileMenu)
        self.fileMenu.add_command(label='Open HP Data Spreadsheet for Editing', command=self.open_old_rit_csv, accelerator='ctrl-o')
        self.fileMenu.add_command(label='Open Keywords Spreadsheet for Editing', command=self.open_old_keywords_csv)
        self.fileMenu.add_command(label='Settings...', command=self.open_prefs)
        self.fileMenu.add_command(label='API Token...', command=self.setapitoken)
        self.fileMenu.add_command(label='API URL...', command=self.setapiurl)
        self.fileMenu.add_command(label='Add a New Device', command=self.open_form)
        self.master.config(menu=self.menubar)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=BOTH, expand=1)
        f1 = HP_Starter(master=self.nb, prefs=self.prefs)
        f2 = PRNU_Uploader(master=self.nb, prefs=self.prefs)
        self.nb.add(f1, text='Process HP Data')
        self.nb.add(f2, text='Export PRNU Data')

    def open_form(self):
        h = HP_Device_Form(self, self.prefs)


    def load_defaults(self):
        self.prefs = parse_prefs(os.path.join('data', 'preferences.txt'))
        if self.prefs:
            if 'inputdir' in self.prefs:
                self.inputdir = self.prefs['inputdir']
            else:
                self.inputdir = os.getcwd()

            if 'outputdir' in self.prefs:
                self.outputdir = self.prefs['outputdir']
            else:
                self.outputdir = os.getcwd()

    def open_old_rit_csv(self):
        csv = tkFileDialog.askopenfilename(initialdir=self.outputdir)
        HPSpreadsheet(dir=self.outputdir, ritCSV=csv, master=self.master).open_spreadsheet()

    def open_old_keywords_csv(self):
        csv = tkFileDialog.askopenfilename(initialdir=self.outputdir)
        KeywordsSheet(dir=self.outputdir, keyCSV=csv, master=self.master).open_spreadsheet()

    def open_prefs(self):
        Preferences(master=self.master)

    def save_prefs(self):
        with open(os.path.join('data', 'preferences.txt'), 'w') as f:
            for key in self.prefs:
                f.write(key + '=' + self.prefs[key] + '\n')


    def setapiurl(self):
        url = self.prefs['apiurl'] if 'apiurl' in self.prefs else None
        newUrlStr = tkSimpleDialog.askstring("Set API URL", "URL", initialvalue=url)

        if newUrlStr is not None:
            self.prefs['apiurl'] = newUrlStr
            self.save_prefs()

    def setapitoken(self):
        token = self.prefs['apitoken'] if 'apitoken' in self.prefs else None

        newTokenStr = tkSimpleDialog.askstring("Set API Token", "Token", initialvalue=token)

        if newTokenStr is not None:
            self.prefs['apitoken'] = newTokenStr
            self.save_prefs()

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


def main():
    root = Tk()
    root.resizable(width=False, height=False)
    root.wm_title('HP GUI')
    HPGUI(master=root).pack(side=TOP, fill=BOTH, expand=TRUE)
    root.mainloop()

if __name__ == '__main__':
    main()