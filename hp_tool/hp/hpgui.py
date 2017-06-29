import tarfile
import threading
from Tkinter import *
import collections
import boto3
import rawpy
from boto3.s3.transfer import S3Transfer
import matplotlib
import requests
matplotlib.use("TkAgg")
import ttk
import tkFileDialog
import tkMessageBox
import tkSimpleDialog
from hp_data import *
from HPSpreadsheet import HPSpreadsheet, TrelloSignInPrompt, ProgressPercentage
from KeywordsSheet import KeywordsSheet
from ErrorWindow import ErrorWindow
from prefs import SettingsWindow, SettingsManager
from CameraForm import HP_Device_Form, Update_Form
from camera_handler import API_Camera_Handler
from data_files import *

class HP_Starter(Frame):

    def __init__(self, settings, master=None):
        Frame.__init__(self, master)
        self.master=master
        self.settings = settings
        self.grid()
        self.oldImageNames = []
        self.newImageNames = []
        self.collections = load_json_dictionary(data_files._COLLECTIONS)
        self.createWidgets()
        self.load_defaults()
        self.bindings()

    def bindings(self):
        self.bind('<Return>', self.go)

    def update_defaults(self):
        self.settings.set('inputdir', self.inputdir.get())
        self.settings.set('outputdir', self.outputdir.get())

    def load_defaults(self):
        if self.settings.get('inputdir') is not None:
            self.inputdir.insert(END, self.settings.get('inputdir'))

        if self.settings.get('outputdir') is not None:
            self.outputdir.insert(END, self.settings.get('outputdir'))

    def load_input(self):
        initial = self.inputdir.get() if self.inputdir.get() else os.getcwd()
        d = tkFileDialog.askdirectory(initialdir=initial)
        if d:
            self.inputdir.delete(0, 'end')
            self.inputdir.insert(0, d)

    def load_output(self):
        initial = self.inputdir.get() if self.inputdir.get() else os.getcwd()
        d = tkFileDialog.askdirectory(initialdir=initial)
        if d:
            self.outputdir.delete(0, 'end')
            self.outputdir.insert(0, d)

    def preview_filename(self):
        testNameStr = 'Please update settings with username and organization.'
        if self.settings.get('seq') is not None:
            testNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                          self.settings.get('organization') + self.settings.get('username') + '-' + self.settings.get('seq')
            if self.additionalinfo.get():
                testNameStr += '-' + self.additionalinfo.get()
        tkMessageBox.showinfo('Filename Preview', testNameStr)

    def go(self, event=None):
        if not self.settings.get('username') or not self.settings.get('organization'):
            tkMessageBox.showerror(title='Error', message='Please enter initials and organization in settings before running.')
            return

        if self.inputdir.get() == '':
            tkMessageBox.showerror(title='Error', message='Please specify an input directory. This should contain data from only one camera.')
            return
        elif self.outputdir.get() == '':
                self.outputdir.insert(0, os.path.join(self.inputdir.get(), 'hp-output'))

        if self.camModel.get() == '':
            yes = tkMessageBox.askyesno(title='Error', message='Invalid Device Local ID. Would you like to add a new device?')
            if yes:
                self.master.open_form()
                self.update_model()
            return

        globalFields = ['HP-Collection', 'HP-DeviceLocalID', 'HP-CameraModel', 'HP-LensLocalID']
        kwargs = {'settings':self.settings,
                  'imgdir':self.inputdir.get(),
                  'outputdir':self.outputdir.get(),
                  'recursive':self.recBool.get(),
                  'additionalInfo':self.additionalinfo.get(),
                  }
        for fieldNum in xrange(len(globalFields)):
            val = self.attributes[self.descriptionFields[fieldNum]].get()
            if val == 'None':
                val = ''
            kwargs[globalFields[fieldNum]] = val

        self.update_defaults()

        (self.oldImageNames, self.newImageNames) = process(self, self.master.cameras, **kwargs)
        if self.oldImageNames == None:
            return
        aSheet = HPSpreadsheet(self.settings, dir=self.outputdir.get(), master=self.master, devices=self.master.cameras)
        aSheet.open_spreadsheet()
        self.keywordsbutton.config(state=NORMAL)
        keySheet = self.open_keywords_sheet()
        keySheet.close()

    def open_keywords_sheet(self):
        keywords = KeywordsSheet(self.settings, dir=self.outputdir.get(), master=self.master, newImageNames=self.newImageNames, oldImageNames=self.oldImageNames)
        keywords.open_spreadsheet()
        return keywords

    def open_settings(self):
        SettingsWindow(self.settings, master=self.master)

    def createWidgets(self):
        r=0
        Label(self, text='***ONLY PROCESS DATA FROM ONE DEVICE PER RUN***', font=('bold', 16)).grid(row=r, columnspan=8, pady=2)
        r+=1
        Label(self, text='Specify a different output directory for each different device.').grid(row=r, columnspan=8, pady=2)
        r += 1
        self.recBool = BooleanVar()
        self.recBool.set(False)
        self.inputSelector = Button(self, text='Input directory: ', command=self.load_input, width=20)
        self.inputSelector.grid(row=r, column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.recbox = Checkbutton(self, text='Include subdirectories', variable=self.recBool)
        self.recbox.grid(row=r, column=3, ipadx=5, ipady=5, padx=5, pady=5)
        self.inputdir = Entry(self)
        self.inputdir.grid(row=r, column=1, ipadx=5, ipady=5, padx=0, pady=5, columnspan=2)

        self.outputSelector = Button(self, text='Output directory: ', command=self.load_output, width=20)
        self.outputSelector.grid(row=r, column=4, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)
        self.outputdir = Entry(self, width=20)
        self.outputdir.grid(row=r, column=6, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)
        r+=1

        self.additionallabel = Label(self, text='Additional Text to add at end of new filenames: ')
        self.additionallabel.grid(row=r, column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=3)
        self.additionalinfo = Entry(self, width=10)
        self.additionalinfo.grid(row=r, column=3, ipadx=5, ipady=5, padx=5, pady=5, sticky='W')

        self.previewbutton = Button(self, text='Preview filename', command=self.preview_filename, bg='cyan')
        self.previewbutton.grid(row=r, column=4)

        self.changeprefsbutton = Button(self, text='Edit Settings', command=self.open_settings)
        self.changeprefsbutton.grid(row=r, column=6)
        r+=1

        self.sep1 = ttk.Separator(self, orient=HORIZONTAL).grid(row=r, columnspan=8, sticky='EW')
        self.descriptionFields = ['HP-Collection', 'Local Camera ID', 'Camera Model', 'Local Lens ID']
        r+=1

        Label(self, text='Enter collection information. Local Camera ID is REQUIRED. If you enter a valid ID (case sensitive), the corresponding '
                         'model will appear in the camera model box.\nIf you enter an invalid ID and Run, it is assumed '
                         'that this is a new device, and you will be prompted to enter the new device\'s information.').grid(row=r,columnspan=8)
        r+=1

        self.localID = StringVar()
        self.localID.trace('w', self.update_model)
        self.camModel = StringVar()
        col = 0
        self.attributes = {}
        for field in self.descriptionFields:
            attrlabel = Label(self, text=field)
            attrlabel.grid(row=r, column=col, ipadx=5, ipady=5, padx=5, pady=5)
            if field == 'HP-Collection':
                self.attributes[field] = ttk.Combobox(self, width=20, values=self.collections.keys(), state='readonly')
                self.attributes[field].set('None')
            else:
                self.attributes[field] = Entry(self, width=10)
            self.attributes[field].grid(row=r, column=col+1, ipadx=0, ipady=5, padx=5, pady=5)

            if field == 'Local Camera ID':
                self.attributes[field].config(textvar=self.localID)
            elif field == 'Camera Model':
                self.attributes[field].config(textvar=self.camModel, state=DISABLED)
            col += 2
            if col == 8:
                r += 1
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
    def __init__(self, settings, master=None):
        Frame.__init__(self, master)
        self.master = master
        self.settings = settings
        self.root_dir = StringVar()
        self.localID = StringVar()
        self.s3path = StringVar()
        self.newCam = BooleanVar()
        self.newCam.set(0)
        self.parse_vocab(data_files._PRNUVOCAB)
        self.create_prnu_widgets()
        self.s3path.set(self.settings.get('aws-prnu', notFound=''))

    def create_prnu_widgets(self):
        r = 0
        Label(self, text='Enter the absolute path of the main PRNU directory here. You can click the button to open a file select dialog.').grid(
            row=r,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=8)
        r+=1

        dirbutton = Button(self, text='Root PRNU Directory:', command=self.open_dir, width=20)
        dirbutton.grid(row=r,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.rootEntry = Entry(self, width=100, textvar=self.root_dir)
        self.rootEntry.grid(row=r, column=1, ipadx=5, ipady=5, padx=0, pady=5, columnspan=4)
        r+=1

        sep1 = ttk.Separator(self, orient=HORIZONTAL).grid(row=r, columnspan=6, sticky='EW', pady=5)
        r+=1

        sep2 = ttk.Separator(self, orient=VERTICAL).grid(row=r, column=2, sticky='NS', padx=5, rowspan=3)

        Label(self, text='You must successfully verify the directory structure by clicking below before you can upload.\n'
                         'If any errors are found, they must be corrected.').grid(row=r,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)

        Label(self, text='After successful verification, specify the upload location and click Start Upload.\n'
                         'Make sure you have specified your Trello token in Settings as well.').grid(
            row=r,column=3, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)
        r+=1

        verifyButton = Button(self, text='Verify Directory Structure', command=self.examine_dir, width=20)
        verifyButton.grid(row=r,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)

        self.s3Label = Label(self, text='S3 bucket/path: ').grid(row=r,column=3, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.s3Entry = Entry(self, width=40, textvar=self.s3path)
        self.s3Entry.grid(row=r, column=4, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2, sticky=W)
        r+=1

        self.changeprefsbutton = Button(self, text='Edit Settings', command=self.open_settings)
        self.changeprefsbutton.grid(row=r, column=0, columnspan=2)

        self.uploadButton = Button(self, text='Start Upload', command=self.upload, width=20, state=DISABLED, bg='green')
        self.uploadButton.grid(row=r,column=3, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=W)

        self.cancelButton = Button(self, text='Cancel', command=self.cancel_upload, width=20, bg='red')
        self.cancelButton.grid(row=r, column=4, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1, sticky=E)

    def open_settings(self):
        SettingsWindow(self.settings, master=self.master)
        self.s3path.set(self.settings.get('aws-prnu', notFound=''))

    def open_new_insert_id(self):
        d = HP_Device_Form(self, validIDs=self.master.cameras.keys(), token=self.settings.get('trello'), browser=self.settings.get('apitoken'))
        self.master.reload_devices()

    def parse_vocab(self, path):
        self.vocab = []
        with open(path) as v:
            rdr = csv.reader(v)
            for row in rdr:
                self.vocab.append(row[0])
                for x in range(0, 101):
                    self.vocab.append(row[0] + '_' + str(x))

    def open_dir(self):
        d = tkFileDialog.askdirectory()
        if d is not None:
            self.root_dir.set(d)

    def examine_dir(self):
        print('Verifying PRNU directory')
        self.localID.set(os.path.basename(os.path.normpath(self.root_dir.get())))
        msgs = []

        for path, dirs, files in os.walk(self.root_dir.get()):
            p, last = os.path.split(path)
            if last == self.localID.get():
                if not self.has_same_contents(dirs, ['images', 'video']):
                    msgs.append('Root PRNU directory must have \"Images\" and \"Video\" folders.')
                if files:
                    for f in files:
                        if f.startswith('.') or f.lower() == 'thumbs.db':
                            try:
                                os.remove(os.path.join(path, f))
                            except OSError:
                                pass
                        else:
                            msgs.append('There should be no files in the root directory. Only \"Images\" and \"Video\" folders.')
                            break
            elif last.lower() in ['images', 'video']:
                if not self.has_same_contents(dirs, ['primary', 'secondary']):
                    msgs.append('Images and Video folders must each contain Primary and Secondary folders.')
                if files:
                    for f in files:
                        if f.startswith('.') or f.lower() == 'thumbs.db':
                            try:
                                os.remove(os.path.join(path, f))
                            except OSError:
                                pass
                        else:
                            msgs.append('There should be no additional files in the ' + last + ' directory. Only \"Primary\" and \"Secondary\".')
                            break
            elif last.lower() == 'primary' or last.lower() == 'secondary':
                for sub in dirs:
                    if sub.lower() not in self.vocab:
                        msgs.append('Invalid reference type: ' + sub)
                    elif sub.lower().startswith('rgb_no_lens'):
                        msgs.extend(self.check_luminance(os.path.join(path, sub)))
                if files:
                    for f in files:
                        if f.startswith('.') or f.lower() == 'thumbs.db':
                            try:
                                os.remove(os.path.join(path, f))
                            except OSError:
                                pass
                        else:
                            msgs.append('There should be no additional files in the ' + last + ' directory. Only PRNU reference type folders (White_Screen, Blue_Sky, etc).')
                            break
            elif last.lower() in self.vocab:
                if dirs:
                    msgs.append('There should be no additional subfolders in folder ' + path)
                if files:
                    for f in files:
                        if f.startswith('.') or f.lower() == 'thumbs.db':
                            try:
                                os.remove(os.path.join(path, f))
                            except OSError:
                                pass
                else:
                    msgs.append('There are no images or videos in: ' + path + '. If this is intentional, delete the folder.')

        if not self.newCam.get() and not self.local_id_used():
            msgs = 'Invalid local ID: ' + self.localID.get() + '. This field is case sensitive, and must also match the name of the directory. Would you like to add a new device?'
            if tkMessageBox.askyesno(title='Unrecognized Local ID', message=msgs):
                self.open_new_insert_id()
            msgs = 'hide'

        if msgs == 'hide':
            pass
        elif msgs:
            ErrorWindow(self, errors=msgs)
            self.master.statusBox.println('PRNU directory validation failed for ' + self.root_dir.get())
        else:
            tkMessageBox.showinfo(title='Complete', message='Everything looks good. Click \"Start Upload\" to begin upload.')
            self.uploadButton.config(state=NORMAL)
            self.rootEntry.config(state=DISABLED)
            self.master.statusBox.println('PRNU directory successfully validated: ' + self.root_dir.get())

    def check_luminance(self, foldername):
        """
        Verifies luminance of PRNU data folder
        :param foldername: Full absolute path of folder to check. Last 
        :return: list of error messages
        """
        results = []
        standard_files = ['png', 'jpg', 'jpeg', 'tif', 'tiff']
        raw_files = ['cr2', 'nef', 'raf', 'crw', 'dng', 'arw', 'srf', 'raf']
        reds = []
        greens = []
        blues = []

        target = int(foldername.split("_")[-1])
        min_value = target-5
        max_value = target+5

        for f in os.listdir(foldername):
            if f.lower().split(".")[-1] in standard_files:
                with Image.open(os.path.join(foldername, f)) as image:
                    data = np.asarray(image)
            if f.lower().split(".")[-1] in raw_files:
                with rawpy.imread(os.path.join(foldername, f)) as image:
                    data = image.postprocess()
            red = data[:, :, 0]
            green = data[:, :, 1]
            blue = data[:, :, 2]
            reds.append((np.mean(red) / 255) * 100)
            greens.append((np.mean(green) / 255) * 100)
            blues.append((np.mean(blue) / 255) * 100)
        red_per = int(np.mean(reds))
        green_per = int(np.mean(greens))
        blue_per = int(np.mean(blues))

        if (red_per, green_per, blue_per) not in range(min_value, max_value):
            relative_path = foldername.split("\\")[-3:]
            results.append("{0} has incorrect luminance values of R:{1}, G:{2}, B:{3} where the target was {4}".format(foldername, red_per, green_per, blue_per, target))

        return results


    def has_same_contents(self, list1, list2):
        # set both lists to lowercase strings and checks if they have the same items, in any order
        llist1 = [x.lower() for x in list1]
        llist2 = [y.lower() for y in list2]
        return collections.Counter(llist1) == collections.Counter(llist2)

    def upload(self):
        self.capitalize_dirs()
        val = self.s3path.get()
        if (val is not None and len(val) > 0):
            self.settings.set('aws-prnu', val)

        # parse path
        s3 = S3Transfer(boto3.client('s3', 'us-east-1'))
        if val.startswith('s3://'):
            val = val[5:]
        BUCKET = val.split('/')[0].strip()
        DIR = val[val.find('/') + 1:].strip()
        DIR = DIR if DIR.endswith('/') else DIR + '/'

        print('Uploading...')
        total = sum([len(files) for r, d, files in os.walk(self.root_dir.get())])
        ct = 0.0
        upload_error = False
        retry = []
        for root, dirs, files in os.walk(self.root_dir.get()):
            for f in files:
                local_path = os.path.join(root, f)
                upload_path = local_path[local_path.lower().index(self.localID.get().lower()):]
                try:
                    s3.upload_file(local_path, BUCKET, os.path.join(DIR, upload_path).replace('\\', '/'),
                                   callback=ProgressPercentage(local_path, total, ct))
                    ct += 1
                except Exception as e:
                    print '\n' + str(e) + '...Upload will continue, and this file will re-attempt upload again at the end...'
                    retry.append({'local_path':local_path, 'upload_path': upload_path})
                    upload_error = True
        failed = []
        msg = []
        if upload_error:
            print '\n Retrying Failed Files...\n'
            for f in retry:
                try:
                    s3.upload_file(f['local_path'], BUCKET, os.path.join(DIR, f['upload_path']).replace('\\', '/'),
                                   callback=ProgressPercentage(f['local_path'], total, ct))
                    ct+=1
                except Exception as e:
                    s = 'Failed to upload '+ f['local_path']
                    print s +'\n'
                    failed.append(s)
            if failed:
                msg.append('Failed to upload all files to S3. Make sure your S3 upload path is correct.\nReach out to medifor_manipulators@partech.com or Trello for assistance.')

        err = self.notify_trello_prnu('s3://' + os.path.join(val, self.root_dir.get()), failed)
        if err is not None:
            msg.append('S3 upload completed, but failed to notify Trello (' + str(
                err) + ').\nReach out to medifor_manipulators@partech.com or Trello for assistance.')
            self.master.statusBox.println(msg)
        else:
            msg.append('Complete!')
            self.master.statusBox.println('Successfully uploaded PRNU data for ' + self.localID.get() + ' to S3://' + val + '.')
        d = tkMessageBox.showinfo(title='Status', message='\n'.join(msg))

        # reset state of buttons and boxes
        self.cancel_upload()

    def notify_trello_prnu(self, path, errors):
        if self.settings.get('trello') is None:
            t = TrelloSignInPrompt(self)
            token = t.token.get()
            self.settings.set('trello', token)

        # post the new card
        list_id = '58dd916dee8fc7d4da953571'
        new = str(datetime.datetime.now())
        desc = path + '\n' + '\n'.join(errors) if errors else path
        resp = requests.post("https://trello.com/1/cards", params=dict(key=self.master.trello_key, token=self.settings.get('trello')),
                             data=dict(name=new, idList=list_id, desc=desc))
        if resp.status_code == requests.codes.ok:
            me = requests.get("https://trello.com/1/members/me", params=dict(key=self.master.trello_key, token=self.settings.get('trello')))
            member_id = json.loads(me.content)['id']
            new_card_id = json.loads(resp.content)['id']
            resp2 = requests.post("https://trello.com/1/cards/%s/idMembers" % (new_card_id),
                                  params=dict(key=self.master.trello_key, token=self.settings.get('trello')),
                                  data=dict(value=member_id))
            return None
        else:
            return resp.status_code

    def cancel_upload(self):
        self.uploadButton.config(state=DISABLED)
        self.rootEntry.config(state=NORMAL)

    def archive_prnu(self):
        ftar = os.path.join(os.path.split(self.root_dir.get())[0], self.localID.get() + '.tar')
        archive = tarfile.open(ftar, "w", errorlevel=2)
        archive.add(self.root_dir.get(), arcname=os.path.split(self.root_dir.get())[1])
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
                    shutil.move(os.path.join(root, name), os.path.join(root, name.title()))
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
        self.trello_key = 'dcb97514b94a98223e16af6e18f9f99e'
        self.settings = SettingsManager()
        self.create_widgets()
        self.load_ids()
        self.statusBox.println('See terminal/command prompt window for progress while processing.')

    def create_widgets(self):
        self.menubar = Menu(self)
        self.fileMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='File', menu=self.fileMenu)
        self.fileMenu.add_command(label='Open HP Data Spreadsheet for Editing', command=self.open_old_rit_csv, accelerator='ctrl-o')
        self.fileMenu.add_command(label='Open Keywords Spreadsheet for Editing', command=self.open_old_keywords_csv)
        self.fileMenu.add_command(label='Settings...', command=self.open_settings)
        self.fileMenu.add_command(label='Add a New Device', command=self.open_form)
        self.fileMenu.add_command(label='Update a Device', command=self.edit_device)
        self.master.config(menu=self.menubar)

        self.statusFrame = Frame(self)
        self.statusFrame.pack(side=BOTTOM, fill=BOTH, expand=1)
        Label(self.statusFrame, text='Notifications').pack()
        self.statusBox = ReadOnlyText(self.statusFrame, height=10)
        self.statusBox.pack(fill=BOTH, expand=1)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=BOTH, expand=1)
        f1 = HP_Starter(self.settings, master=self)
        f2 = PRNU_Uploader(self.settings, master=self)
        self.nb.add(f1, text='Process HP Data')
        self.nb.add(f2, text='Export PRNU Data')

    def open_form(self):
        if self.settings.get('trello') in (None, ''):
            tkMessageBox.showerror(title='Error', message='Trello login is required to use this feature. Enter this in settings.')
            return
        elif self.settings.get('apitoken') in (None, ''):
            tkMessageBox.showerror(title='Error', message='Browser login is required to use this feature. Enter this in settings.')
            return
        new_device = StringVar()
        h = HP_Device_Form(self, validIDs=self.cameras.keys(), pathvar=new_device, token=self.settings.get('trello'), browser=self.settings.get('apitoken'))
        h.wait_window()
        if new_device.get():
            r = self.add_device(new_device.get())

    def edit_device(self):
        token = self.settings.get('apitoken')
        trello = self.settings.get('trello')
        if token is None:
            tkMessageBox.showerror(title='Error', message='You must be logged into browser to use this feature. Please enter your browser token in settings.')
            return
        if trello is None:
            tkMessageBox.showerror(title='Error',
                                   message='You must be logged into trello to use this feature. Please enter your trello token in settings.')
            return

        device_id = tkSimpleDialog.askstring(title='Device ID', prompt='Please enter device local ID:')
        if device_id in ('', None):
            return

        source = self.reload_ids()
        if source == 'local':
            tkMessageBox.showerror(title='Error', message='Could not update camera list from browser.')
            return
        else:
            try:
                d = Update_Form(self, device_data=self.cameras[device_id], browser=token, trello=self.settings.get('trello'))
                self.wait_window(d)
                if d.updated:
                    self.reload_ids()
            except KeyError:
                tkMessageBox.showerror(title='Error', message='Invalid Device ID (case-sensitive).')
                return

    def open_old_rit_csv(self):
        open_data = tkMessageBox.askokcancel(title='Data Selection', message='Select data to open. Select the root OUTPUT directory - the one with csv, image, etc. folders.')
        if open_data:
            d = tkFileDialog.askdirectory(title='Select Root Data Folder')
            if d is None:
                return
            else:
                try:
                    csv = None
                    for f in os.listdir(os.path.join(d, 'csv')):
                        if f.endswith('rit.csv'):
                            csv = os.path.join(d, 'csv', f)
                            break
                    if csv is None or True not in (os.path.exists(os.path.join(d, 'image')),
                                                   os.path.exists(os.path.join(d, 'video')),
                                                   os.path.exists(os.path.join(d, 'audio'))):
                        raise OSError()
                except OSError as e:
                    tkMessageBox.showerror(title='Error', message='Directory must contain csv directory and at least one of image, video, or audio directories. The csv folder must contain the data file (*rit.csv).')
                    return
                check_outdated(csv, d)
                h = HPSpreadsheet(self.settings, dir=d, ritCSV=csv, master=self, devices=self.cameras)
                h.open_spreadsheet()
        else:
            return

    def open_old_keywords_csv(self):
        open_data = tkMessageBox.askokcancel(title='Data Selection', message='Select data to edit keywords. Select the root OUTPUT directory - the one with csv, image, etc. folders.')
        if open_data:
            d = tkFileDialog.askdirectory(title='Select Root Data Folder')
            if d is None:
                return
            else:
                try:
                    csv = None
                    for f in os.listdir(os.path.join(d, 'csv')):
                        if f.endswith('keywords.csv'):
                            csv = os.path.join(d, 'csv', f)
                            break
                    if csv is None or True not in (os.path.exists(os.path.join(d, 'image')),
                                                   os.path.exists(os.path.join(d, 'video')),
                                                   os.path.exists(os.path.join(d, 'audio'))):
                        raise OSError()
                except OSError as e:
                    tkMessageBox.showerror(title='Error', message='Directory must contain csv directory and at least one of image, video, or audio directories. The csv folder must contain the data file (*keywords.csv).')
                    return

                k = KeywordsSheet(self.settings, dir=d, keyCSV=csv, master=self)
                k.open_spreadsheet()
        else:
            return


    def open_settings(self):
        SettingsWindow(master=self.master, settings=self.settings)

    def load_ids(self):
        cams = API_Camera_Handler(self, self.settings.get('apiurl'), self.settings.get('apitoken'))
        self.cameras = cams.get_all()
        if cams.get_source() == 'remote':
            self.statusBox.println('Camera data successfully loaded from API.')
        else:
            self.statusBox.println('Camera data loaded from hp_tool/data/devices.json.')
            self.statusBox.println(
                'It is recommended to enter your browser credentials in settings and restart to get the most updated information.')
        return cams.source

    def reload_ids(self):
        self.cameras = None
        return self.load_ids()

    def add_device(self, path):
        df = pd.read_csv(path)
        fields = {}
        for heading in ['HP-LocalDeviceID', 'DeviceSN', 'CameraModel', 'Manufacturer', 'HP-CameraModel']:
            fields[heading] = df[heading][0] if str(df[heading][0]) != 'nan' else ''

        self.cameras[fields['HP-LocalDeviceID']] = {
            'hp_device_local_id': fields['HP-LocalDeviceID'],
            'hp_camera_model': fields['HP-CameraModel'],
            'exif': [{'exif_camera_model': fields['CameraModel'],
                      'exif_camera_make': fields['Manufacturer'],
                      'exif_device_serial_number': fields['DeviceSN']}],
        }
        self.statusBox.println('Added ' + fields['HP-LocalDeviceID'] + ' to camera list.')


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


def main():
    root = Tk()
    root.resizable(width=False, height=False)
    root.wm_title('HP GUI')
    HPGUI(master=root).pack(side=TOP, fill=BOTH, expand=TRUE)
    root.mainloop()

if __name__ == '__main__':
    main()