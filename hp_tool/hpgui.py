import tarfile
import tkSimpleDialog
from Tkinter import *
import ttk
import collections
import tempfile
import hashlib
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
import time
import numpy as np
import webbrowser
from hp_data import *
from HPSpreadsheet import HPSpreadsheet, TrelloSignInPrompt
from KeywordsSheet import KeywordsSheet
from ErrorWindow import ErrorWindow
from prefs import Preferences
from CameraForm import HP_Device_Form

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
        prefs = parse_prefs(self, self.prefsfilename)
        if prefs and prefs.has_key('seq'):
            testNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                        prefs['organization'] + prefs['username'] + '-' + prefs['seq']
            if self.additionalinfo.get():
                testNameStr += '-' + self.additionalinfo.get()
        tkMessageBox.showinfo('Filename Preview', testNameStr)


    def go(self):
        if self.camModel.get() == '':
            yes = tkMessageBox.askyesno(title='Error', message='Invalid Device Local ID. Would you like to add a new device?')
            if yes:
                v = StringVar()
                token = self.prefs['trello'] if 'trello' in self.prefs else None
                h = HP_Device_Form(self, validIDs=self.master.cameras.keys(), pathvar=v, token=token)
                h.wait_window()
                if v.get():
                    r = self.add_device(v.get())
                    if r is None:
                        tkMessageBox.showerror(title='Error', message='An error ocurred. Could not add device.')
            return

        globalFields = ['HP-CollectionRequestID', 'HP-DeviceLocalID', 'HP-CameraModel', 'HP-LensLocalID']
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

        (self.oldImageNames, self.newImageNames, errors) = process(self, self.master.cameras, **kwargs)
        if self.oldImageNames == None:
            return
        aSheet = HPSpreadsheet(dir=self.outputdir.get(), master=self.master, devices=self.master.cameras)
        aSheet.open_spreadsheet()
        if errors is not None:
            ErrorWindow(aSheet, errors)
        self.keywordsbutton.config(state=NORMAL)
        keySheet = self.open_keywords_sheet()
        keySheet.close()

    def add_device(self, path):
        local_id = None
        hp_model = None
        exif_model = None
        exif_sn = None
        make = None
        with open(path) as p:
            for line in p:
                if 'Local ID' in line:
                    local_id = line.split('=')[1].strip()
                elif 'Series Model' in line:
                    hp_model = line.split('=')[1].strip()
                elif 'Camera Model' in line:
                    exif_model = line.split('=')[1].strip()
                elif 'Serial Number' in line:
                    exif_sn = line.split('=')[1].strip()
                elif 'Manufacturer' in line:
                    make = line.split('=')[1].strip()
        if local_id and hp_model and exif_model and exif_sn:
            self.master.cameras[local_id] = {
                'hp_device_local_id': local_id,
                'hp_camera_model': hp_model,
                'exif_camera_model': exif_model,
                'exif_camera_make': make,
                'exif_device_serial_number': exif_sn
            }
            self.master.statusBox.println('Added ' + local_id + ' to camera list. This will be valid for this instance only.')
            self.update_model()
            return 1
        else:
            return None


    def open_keywords_sheet(self):
        keywords = KeywordsSheet(dir=self.outputdir.get(), master=self.master, newImageNames=self.newImageNames, oldImageNames=self.oldImageNames)
        keywords.open_spreadsheet()
        return keywords

    def open_prefs(self):
        Preferences(master=self.master)
        if parse_prefs(self, self.prefsfilename):
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
        self.descriptionFields = ['Coll. Request ID', 'Local Camera ID', 'Camera Model', 'Local Lens ID', ]

        self.descriptionlabel = Label(self, text='Enter global camera information. This information cannot be pulled '
                                                 'from exif data.')
        self.localID = StringVar()
        self.localID.trace('w', self.update_model)
        self.camModel = StringVar()
        self.descriptionlabel.grid(row=3,columnspan=8, sticky='W')
        row = 4
        col = 0
        self.attributes = {}
        for field in self.descriptionFields:
            self.attrlabel = Label(self, text=field).grid(row=row, column=col, ipadx=5, ipady=5, padx=5, pady=5)
            self.attributes[field] = Entry(self, width=10)
            self.attributes[field].grid(row=row, column=col+1, ipadx=0, ipady=5, padx=5, pady=5)

            if field == 'Local Camera ID':
                self.attributes[field].config(textvar=self.localID)
            elif field == 'Camera Model':
                self.attributes[field].config(textvar=self.camModel, state=DISABLED)
            col += 2
            if col == 8:
                row += 1
                col = 0

        lastLoc = self.attributes['Local Lens ID'].grid_info()
        lastRow = int(lastLoc['row'])

        self.sep2 = ttk.Separator(self, orient=HORIZONTAL).grid(row=lastRow+1, columnspan=8, sticky='EW')

        self.okbutton = Button(self, text='Run ', command=self.go, width=20, bg='green')
        self.okbutton.grid(row=lastRow+2,column=0, ipadx=5, ipady=5, sticky='E')
        self.cancelbutton = Button(self, text='Cancel', command=self.quit, width=20, bg='red')
        self.cancelbutton.grid(row=lastRow+2, column=6, ipadx=5, ipady=5, padx=5, sticky='W')

        self.keywordsbutton = Button(self, text='Enter Keywords', command=self.open_keywords_sheet, state=DISABLED, width=20)
        self.keywordsbutton.grid(row=lastRow+2, column=2, ipadx=5, ipady=5, padx=5, sticky='E')

    def update_model(self, *args):
        if self.localID.get() in self.master.cameras:
            self.attributes['Camera Model'].config(state=NORMAL)
            self.camModel.set(self.master.cameras[self.localID.get()]['hp_camera_model'])
            self.attributes['Camera Model'].config(state=DISABLED)
        else:
            self.attributes['Camera Model'].config(state=NORMAL)
            self.camModel.set('')
            self.attributes['Camera Model'].config(state=DISABLED)


class PRNU_Uploader(Frame):
    def __init__(self, master=None, prefs=None):
        Frame.__init__(self, master)
        self.master = master
        self.prefs=prefs
        self.root_dir = StringVar()
        self.localID = StringVar()
        self.localIDfile = StringVar()
        self.s3path = StringVar()
        self.newCam = BooleanVar()
        self.newCam.set(0)
        self.parse_vocab(os.path.join('data', 'prnu_vocab.csv'))
        self.create_prnu_widgets()
        if prefs is not None and 's3prnu' in prefs:
            self.s3path.set(prefs['s3prnu'])

    def create_prnu_widgets(self):
        r = 0
        dirbutton = Button(self, text='Root PRNU Directory:', command=self.open_dir, width=20)
        dirbutton.grid(row=r,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.rootEntry = Entry(self, width=100, textvar=self.root_dir)
        self.rootEntry.grid(row=r, column=1, ipadx=5, ipady=5, padx=0, pady=5, columnspan=4)
        r+=1

        self.newCamEntry = Entry(self, width=40, textvar=self.localIDfile, state=DISABLED)
        self.newCamEntry.grid(row=r, column=1, columnspan=2, sticky=W)
        self.newCamCheckbox = Checkbutton(self, text='I\'m using a new camera:', variable=self.newCam, command=self.set_new_cam_file)
        self.newCamCheckbox.grid(row=r, column=0, )
        r+=1

        verifyButton = Button(self, text='Verify Directory Structure', command=self.examine_dir, width=20)
        verifyButton.grid(row=r,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)

        self.s3Label = Label(self, text='S3 bucket/path: ').grid(row=r,column=1, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=E)

        self.s3Entry = Entry(self, width=40, textvar=self.s3path)
        self.s3Entry.grid(row=r, column=2, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=W)
        r+=1

        self.uploadButton = Button(self, text='Start Upload', command=self.upload, width=20, state=DISABLED, bg='green')
        self.uploadButton.grid(row=r,column=2, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=W)

        self.cancelButton = Button(self, text='Cancel', command=self.cancel_upload, width=20, bg='red')
        self.cancelButton.grid(row=r, column=1, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=E)

    def set_new_cam_file(self):
        if self.newCam.get():
            if self.localIDfile:
                ync = tkMessageBox.askyesnocancel(message='Have you already completed the New Camera Registration Form?', title='New Camera Data')
                self.newCamEntry.config(state=NORMAL)
                if ync:
                    f = tkFileDialog.askopenfilename(filetypes=[('text files', '.txt')], title='Select data file')
                    self.localIDfile.set(f)
                elif ync is None:
                    self.newCam.set(0)
                    self.newCamEntry.config(state=DISABLED)
                else:
                    self.open_new_insert_id()
        else:
            self.newCamEntry.config(state=DISABLED)

    def open_new_insert_id(self):
        self.newCam.set(1)
        token = self.prefs['trello'] if 'trello' in self.prefs else None
        d = HP_Device_Form(self, validIDs=self.master.cameras.keys(), pathvar=self.localIDfile, token=token)
        if self.localIDfile.get():
            self.newCamEntry.config(state=NORMAL)

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
        self.master.statusBox.println('Verifying...')
        self.localID.set(os.path.basename(os.path.normpath(self.root_dir.get())))
        msgs = []

        for path, dirs, files in os.walk(self.root_dir.get()):
            p, last = os.path.split(path)
            if last == self.localID.get():
                if not self.has_same_contents(dirs, ['images', 'video']):
                    msgs.append('Root PRNU directory must have \"Images\" and \"Video\" folders.')
                if files:
                    for f in files:
                        if f.startswith('.'):
                            os.remove(os.path.join(path, f))
                    msgs.append('There should be no files in the root directory. Only \"Images\" and \"Video\" folders.')
            elif last.lower() in ['images', 'video']:
                if not self.has_same_contents(dirs, ['primary', 'secondary']):
                    msgs.append('Images and Video folders must each contain Primary and Secondary folders.')
                if files:
                    for f in files:
                        if f.startswith('.'):
                            os.remove(os.path.join(path, f))
                    msgs.append('There should be no additional files in the ' + last + ' directory. Only \"Primary\" and \"Secondary\".')
            elif last.lower() == 'primary' or last.lower() == 'secondary':
                for sub in dirs:
                    if sub.lower() not in self.vocab:
                        msgs.append('Invalid reference type: ' + sub)
                if files:
                    for f in files:
                        if f.startswith('.'):
                            os.remove(os.path.join(path, f))
                        else:
                            msgs.append('There should be no additional files in the ' + last + ' directory. Only PRNU reference type folders (White_Screen, Blue_Sky, etc).')
            elif last.lower() in self.vocab:
                if dirs:
                    msgs.append('There should be no additional subfolders in folder ' + path)
                if files:
                    for f in files:
                        if f.startswith('.'):
                            os.remove(os.path.join(path, f))
                else:
                    msgs.append('There are no images in: ' + path)

        if not self.newCam.get() and not self.local_id_used():
            msgs = 'Invalid local ID: ' + self.localID.get() + '. This field is case sensitive, and must also match the name of the directory. Would you like to add a new device?'
            if tkMessageBox.askyesno(title='Unrecognized Local ID', message=msgs):
                self.open_new_insert_id()
                #HP_Device_Form(self, prefs=self.prefs)
            msgs = 'hide'

        if msgs == 'hide':
            pass
        elif msgs:
            ErrorWindow(self, errors=msgs)
            #tkMessageBox.showerror(title='Error', message=msgs)
        else:
            tkMessageBox.showinfo(title='Complete', message='Everything looks good. Click \"Start Upload\" to begin upload.')
            self.uploadButton.config(state=NORMAL)
            self.rootEntry.config(state=DISABLED)
            self.newCamCheckbox.config(state=DISABLED)
            if self.newCam:
                self.newCamEntry.config(state=DISABLED)

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

        self.master.statusBox.println('Creating archive...')
        archive = self.archive_prnu()
        md5file = self.write_md5(archive)

        self.master.statusBox.println('Uploading ' + archive.replace('\\', '/') + ' to s3://' + val)
        s3.upload_file(archive, BUCKET, DIR + os.path.split(archive)[1])
        self.master.statusBox.println('Uploading ' + md5file.replace('\\', '/') + ' to s3://' + val)
        s3.upload_file(md5file, BUCKET, DIR + os.path.split(md5file)[1])

        os.remove(archive)
        os.remove(md5file)

        err = self.notify_trello(os.path.basename(archive))
        if err is not None:
            msg = 'S3 upload completed, but failed to notify Trello (' + str(
                err) + ').\nIf you are unsure why this happened, please email medifor_manipulators@partech.com.'
        else:
            msg = 'Complete!'
        d = tkMessageBox.showinfo(title='Status', message=msg)

        # reset state of buttons and boxes
        self.cancel_upload()

    def notify_trello(self, path):
        if 'trello' not in self.prefs:
            t = TrelloSignInPrompt(self)
            token = t.token.get()
            self.prefs['trello'] = token
            with open(self.master.prefsfilename.get(), 'w') as f:
                for key in self.prefs:
                    f.write(key + '=' + self.prefs[key] + '\n')

        # post the new card
        list_id = '58dd916dee8fc7d4da953571'
        new = str(datetime.datetime.now())
        resp = requests.post("https://trello.com/1/cards", params=dict(key=self.master.trello_key, token=self.prefs['trello']),
                             data=dict(name=new, idList=list_id, desc=path))
        if resp.status_code == requests.codes.ok:
            me = requests.get("https://trello.com/1/members/me", params=dict(key=self.master.trello_key, token=self.prefs['trello']))
            member_id = json.loads(me.content)['id']
            new_card_id = json.loads(resp.content)['id']
            resp2 = requests.post("https://trello.com/1/cards/%s/idMembers" % (new_card_id),
                                  params=dict(key=self.master.trello_key, token=self.prefs['trello']),
                                  data=dict(value=member_id))
            return None
        else:
            return resp.status_code

    def cancel_upload(self):
        self.uploadButton.config(state=DISABLED)
        self.rootEntry.config(state=NORMAL)
        if self.newCam:
            self.newCamEntry.config(state=NORMAL)
        self.newCamCheckbox.config(state=NORMAL)

    def archive_prnu(self):
        ftar = os.path.join(os.path.split(self.root_dir.get())[0], self.localID.get() + '.tar')
        archive = tarfile.open(ftar, "w", errorlevel=2)
        archive.add(self.root_dir.get(), arcname=os.path.split(self.root_dir.get())[1])
        if self.newCam.get():
            archive.add(self.localIDfile.get(), arcname=os.path.split(self.localIDfile.get())[1])
        archive.close()
        return ftar

    def write_md5(self, path):
        # write md5 of archive to file
        md5filename = os.path.join(os.path.split(self.root_dir.get())[0], self.localID.get() + '.md5')
        with open(md5filename, 'w') as m:
            with open(path, 'rb') as f:
                m.write(hashlib.md5(f.read()).hexdigest())

        return md5filename

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
        self.master.statusBox.println('done')

    def local_id_used(self):
        if self.localID.get().lower() in [i.lower() for i in self.master.cameras.keys()]:
            return True
        else:
            return False


class HPGUI(Frame):
    def __init__(self, master=None, **kwargs):
        Frame.__init__(self, master, **kwargs)
        self.master = master
        self.prefsfilename = StringVar()
        self.prefsfilename.set(os.path.join('data', 'preferences.txt'))
        self.trello_key = 'dcb97514b94a98223e16af6e18f9f99e'
        self.load_defaults()
        self.create_widgets()
        self.load_ids()

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

        self.statusFrame = Frame(self)
        self.statusFrame.pack(side=BOTTOM, fill=BOTH, expand=1)
        Label(self.statusFrame, text='Status').pack()
        self.statusBox = ReadOnlyText(self.statusFrame, height=10)
        self.statusBox.pack(fill=BOTH, expand=1)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=BOTH, expand=1)
        f1 = HP_Starter(self, prefs=self.prefs)
        f2 = PRNU_Uploader(self, prefs=self.prefs)
        self.nb.add(f1, text='Process HP Data')
        self.nb.add(f2, text='Export PRNU Data')

    def open_form(self):
        token = self.prefs['trello'] if 'trello' in self.prefs else None
        h = HP_Device_Form(self, validIDs=self.cameras.keys(), token=token)

    def load_defaults(self):
        self.prefs = parse_prefs(self, os.path.join('data', 'preferences.txt'))
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

    def load_ids(self):
        try:
            cams = API_Camera_Handler(self, self.prefs['apiurl'], self.prefs['apitoken'])
            self.cameras = cams.get_all()
            if not self.cameras:
                raise
            self.statusBox.println('Camera data successfully loaded from API.')
        except:
            self.cameras = {}
            data = pd.read_csv(os.path.join('data', 'Devices.csv')).to_dict()
            for num in range(0, len(data['HP-LocalDeviceID'])):
                self.cameras[data['HP-LocalDeviceID'][num]] = {
                    'hp_device_local_id': str(data['HP-LocalDeviceID'][num]),
                    'hp_camera_model': str(data['HP-CameraModel'][num]),
                    'exif_camera_model': str(data['CameraModel'][num]),
                    'exif_camera_make': str(data['Manufacturer'][num]),
                    'exif_device_serial_number': str(data['DeviceSN'][num])
                }
            self.statusBox.println('Camera data loaded from hp_tool/data/Devices.csv.')
            self.statusBox.println(
                'It is recommended to enter your browser credentials in preferences and restart to get the most updated information.')


class ReadOnlyText(Text):
    def __init__(self, master, **kwargs):
        Text.__init__(self, master, **kwargs)
        self.master=master
        self.config(state='disabled')

    def println(self, text):
        self.config(state='normal')
        self.insert(END, text + '\n')
        self.see('end')
        self.config(state='disabled')

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
            print 'Checking external service APIs for device local ID...'

            while True:
                response = requests.get(url, headers=headers)
                if response.status_code == requests.codes.ok:
                    r = json.loads(response.content)
                    for item in r['results']:
                        self.all[item['hp_device_local_id']] = item
                        self.localIDs.append(item['hp_device_local_id'])
                        self.models_hp.append(item['hp_camera_model'])
                        self.models_exif.append(item['exif_camera_model'])
                        self.makes_exif.append(item['exif_camera_make'])
                        self.sn_exif.append(item['exif_device_serial_number'])
                    url = r['next']
                    if url is None:
                        break
                else:
                    raise requests.HTTPError()
        except (requests.HTTPError, requests.ConnectionError):
            print 'An error ocurred connecting to API (' + str(response.status_code) + ').\n Devices will be loaded from hp_tool/data.'
        except KeyError:
            tkMessageBox.showerror(title='Information', message='Could not find API credentials in preferences. Please '
                                                               'add them via preferences or the File menu.')

def main():
    root = Tk()
    root.resizable(width=False, height=False)
    root.wm_title('HP GUI')
    HPGUI(master=root).pack(side=TOP, fill=BOTH, expand=TRUE)
    root.mainloop()

if __name__ == '__main__':
    main()