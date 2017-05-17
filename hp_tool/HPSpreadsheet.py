import json
import tarfile
import ttk
from Tkinter import *
import tkFileDialog
import os
import sys
import boto3
from boto3.s3.transfer import S3Transfer
import collections
import pandas as pd
import tkMessageBox
import tkSimpleDialog
import pandastable
import csv
import webbrowser
import requests
from PIL import Image, ImageTk
from ErrorWindow import ErrorWindow
from CameraForm import HP_Device_Form
import hp_data
import datetime
import threading

RVERSION = hp_data.RVERSION

class HPSpreadsheet(Toplevel):
    def __init__(self, settings, dir=None, ritCSV=None, master=None, devices=None):
        Toplevel.__init__(self, master=master)
        self.settings = settings
        self.dir = dir
        if self.dir:
            self.imageDir = os.path.join(self.dir, 'image')
            self.videoDir = os.path.join(self.dir, 'video')
            self.audioDir = os.path.join(self.dir, 'audio')
            self.errorpath = os.path.join(self.dir, 'csv', 'errors.json')
        self.master = master
        self.ritCSV=ritCSV
        self.trello_key = 'dcb97514b94a98223e16af6e18f9f99e'
        self.saveState = True
        self.highlighted_cells = []
        self.error_cells = []
        self.create_widgets()
        self.kinematics = self.load_kinematics()
        self.devices = devices
        self.apps = self.load_apps()
        self.lensFilters = self.load_lens_filters()
        self.protocol('WM_DELETE_WINDOW', self.check_save)
        w, h = self.winfo_screenwidth()-100, self.winfo_screenheight()-100
        self.geometry("%dx%d+0+0" % (w, h))
        #self.attributes('-fullscreen', True)
        self.set_bindings()

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.topFrame = Frame(self)
        self.topFrame.pack(side=TOP, fill=X)
        self.rightFrame = Frame(self, width=480)
        self.rightFrame.pack(side=RIGHT, fill=Y)
        self.leftFrame = Frame(self)
        self.leftFrame.pack(side=LEFT, fill=BOTH, expand=1)
        self.nb = ttk.Notebook(self.leftFrame)
        self.nb.pack(fill=BOTH, expand=1)
        self.nbtabs = {'main': ttk.Frame(self.nb)}
        self.nb.add(self.nbtabs['main'], text='All Items')
        self.pt = CustomTable(self.nbtabs['main'], scrollregion=None, width=1024, height=720)
        self.pt.show()
        self.on_main_tab = True
        self.add_tabs()
        self.nb.bind('<<NotebookTabChanged>>', self.switch_tabs)

        self.currentImageNameVar = StringVar()
        self.currentImageNameVar.set('Current Image: ')
        l = Label(self.topFrame, height=1, textvariable=self.currentImageNameVar)
        l.pack(fill=BOTH, expand=1)

        image = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'RedX.png'))
        image.thumbnail((250,250))
        self.photo = ImageTk.PhotoImage(image)
        self.l2 = Button(self.rightFrame, image=self.photo, command=self.open_image)
        self.l2.image = self.photo  # keep a reference!
        self.l2.pack(side=TOP)

        self.validateFrame = Frame(self.rightFrame, width=480)
        self.validateFrame.pack(side=BOTTOM)
        self.currentColumnLabel = Label(self.validateFrame, text='Current column:')
        self.currentColumnLabel.grid(row=0, column=0, columnspan=2)
        lbl = Label(self.validateFrame, text='Valid values for cells in this column:').grid(row=1, column=0, columnspan=2)
        self.vbVertScroll = Scrollbar(self.validateFrame)
        self.vbVertScroll.grid(row=2, column=1, sticky='NS')
        self.vbHorizScroll = Scrollbar(self.validateFrame, orient=HORIZONTAL)
        self.vbHorizScroll.grid(row=3, sticky='WE')
        self.validateBox = Listbox(self.validateFrame, xscrollcommand=self.vbHorizScroll.set, yscrollcommand=self.vbVertScroll.set, selectmode=SINGLE, width=50, height=14)
        self.validateBox.grid(row=2, column=0)
        self.vbVertScroll.config(command=self.validateBox.yview)
        self.vbHorizScroll.config(command=self.validateBox.xview)

        self.menubar = Menu(self)
        self.fileMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.add_command(label='Save', command=self.exportCSV, accelerator='ctrl-s')
        self.fileMenu.add_command(label='Load image directory', command=self.load_images)
        self.fileMenu.add_command(label='Validate', command=self.validate)
        self.fileMenu.add_command(label='Export to S3...', command=self.s3export)

        self.editMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='Edit', menu=self.editMenu)
        self.editMenu.add_command(label='Copy', command=self.pt.copy_value, accelerator='ctrl-c')
        self.editMenu.add_command(label='Paste', command=self.pt.paste_value, accelerator='ctrl-v')
        self.editMenu.add_command(label='Fill Selection', command=self.pt.fill_selection, accelerator='ctrl-d')
        self.editMenu.add_command(label='Fill Column', command=self.pt.fill_column, accelerator='ctrl-g')
        self.editMenu.add_command(label='Fill True', command=self.pt.enter_true, accelerator='ctrl-t')
        self.editMenu.add_command(label='Fill False', command=self.pt.enter_false, accelerator='ctr-f')
        self.editMenu.add_command(label='Undo', command=self.undo, accelerator='ctrl-z')
        self.editMenu.add_command(label='Redo', command=self.redo, accelerator='ctrl-y')
        self.config(menu=self.menubar)

    def set_bindings(self):
        self.bind('<Key>', self.keypress)
        self.bind('<Button-1>', self.update_current_image)
        self.bind('<Left>', self.update_current_image)
        self.bind('<Right>', self.update_current_image)
        self.bind('<Return>', self.update_current_image)
        self.bind('<Up>', self.update_current_image)
        self.bind('<Down>', self.update_current_image)
        self.bind('<Tab>', self.update_current_image)
        self.bind('<Control-s>', self.exportCSV)
        self.bind('<Control-z>', self.undo)
        self.bind('<Control-y>', self.redo)

    def undo(self, event=None):
        if self.on_main_tab:
            currentTable = self.pt
        else:
            currentTable = self.tabpt
        if hasattr(currentTable, 'undo') and currentTable.undo:
            currentTable.redo = []
            # cell: tuple (value, row, column)
            for cell in currentTable.undo:
                currentTable.redo.append((currentTable.model.getValueAt(cell[1], cell[2]), cell[1], cell[2]))
                currentTable.model.setValueAt(*cell)
            currentTable.redraw()

    def redo(self, event=None):
        if self.on_main_tab:
            currentTable = self.pt
        else:
            currentTable = self.tabpt
        if hasattr(currentTable, 'redo') and currentTable.redo:
            currentTable.undo = []
            for cell in currentTable.redo:
                currentTable.undo.append((currentTable.model.getValueAt(cell[1], cell[2]), cell[1], cell[2]))
                currentTable.model.setValueAt(cell[0], cell[1], cell[2])
            currentTable.redraw()

    def keypress(self, event):
        self.saveState = False

    def open_image(self):
        image = os.path.join(self.imageDir, self.imName)
        if not os.path.exists(image):
            image = os.path.join(self.videoDir, self.imName)
            if not os.path.exists(image):
                image = os.path.join(self.audioDir, self.imName)
        if sys.platform.startswith('linux'):
            os.system('xdg-open "' + image + '"')
        elif sys.platform.startswith('win'):
            os.startfile(image)
        else:
            os.system('open "' + image + '"')

    def update_current_image(self, event=None):
        if self.on_main_tab:
            row = self.pt.getSelectedRow()
        else:
            row = self.tabpt.getSelectedRow()
        self.imName = str(self.pt.model.getValueAt(row, 0))
        self.currentImageNameVar.set('Current Image: ' + self.imName)
        maxSize = 480
        try:
            im = Image.open(os.path.join(self.imageDir, self.imName))
        except (IOError, AttributeError):
            im = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'RedX.png'))
        if im.size[0] > maxSize or im.size[1] > maxSize:
            im.thumbnail((maxSize,maxSize), Image.ANTIALIAS)
        newimg=ImageTk.PhotoImage(im)
        self.l2.configure(image=newimg)
        self.l2.image = newimg
        self.update_valid_values()

    def add_tabs(self):
        with open(os.path.join('data', 'hptabs.json')) as j:
            tabs = json.load(j, object_pairs_hook=collections.OrderedDict)
        for tab in tabs:
            self.nbtabs[tab] = ttk.Frame(self.nb)
            self.nb.add(self.nbtabs[tab], text=tab)

    def switch_tabs(self, event=None):
        with open(os.path.join('data', 'hptabs.json')) as j:
            tabs = json.load(j)
        clickedTab = self.nb.tab(event.widget.select(), 'text')
        if clickedTab == 'All Items':
            self.update_main()
            self.on_main_tab = True
        else:
            self.update_main()
            headers = tabs[clickedTab]
            self.tabpt = CustomTable(self.nbtabs[clickedTab], scrollregion=None, width=1024, height=720, rows=0, cols=0)
            for h in headers:
                self.tabpt.model.df[h] = self.pt.model.df[h]
            self.tabpt.show()
            self.tabpt.redraw()
            self.on_main_tab = False
            self.color_code_cells(self.tabpt)

    def update_main(self):
        if self.on_main_tab:
            # switching from main tab to another. don't need to do any extra prep
            pass
        else:
            # switching from an alt tab, to any other tab. need to save headers back into pt, and then del tabpt
            for h in self.tabpt.model.df:
                self.pt.model.df[h] = self.tabpt.model.df[h]
            del self.tabpt

    def update_valid_values(self):
        #self.pt.model.df.columns.get_loc('HP-OnboardFilter')
        if self.on_main_tab:
            col = self.pt.getSelectedColumn()
            cols = list(self.pt.model.df)
        else:
            col = self.tabpt.getSelectedColumn()
            cols = list(self.tabpt.model.df)
        currentCol = cols[col]
        self.currentColumnLabel.config(text='Current column: ' + currentCol)
        if currentCol in self.booleanColNames:
            validValues = ['True', 'False']
        elif currentCol == 'HP-CameraKinematics':
            validValues = self.kinematics
        elif currentCol == 'HP-JpgQuality':
            validValues = ['High', 'Medium', 'Low']
        elif currentCol == 'Type':
            validValues = ['image', 'video', 'audio']
        elif currentCol == 'CameraModel':
            validValues = self.load_device_exif('exif_camera_model')
        elif currentCol == 'HP-CameraModel':
            validValues = sorted(set([self.devices[data]['hp_camera_model'] for data in self.devices if self.devices[data]['hp_camera_model'] is not None]), key=lambda s: s.lower())
        elif currentCol == 'DeviceSN':
            validValues = sorted(set([self.devices[data]['exif_device_serial_number'] for data in self.devices if self.devices[data]['exif_device_serial_number'] is not None]), key=lambda s: s.lower())
        elif currentCol == 'HP-App':
            validValues = self.apps
        elif currentCol == 'HP-LensFilter':
            validValues = self.lensFilters
        elif currentCol == 'HP-DeviceLocalID':
            validValues = sorted(self.devices.keys())
        elif currentCol == 'HP-ProximitytoSource':
            validValues = ['close', 'medium', 'far']
        elif currentCol == 'HP-AudioChannels':
            validValues = ['stereo', 'mono']
        elif currentCol ==  "HP-BackgroundNoise":
            validValues = ["constant", "intermittant", "none"]
        elif currentCol == "HP-Description":
            validValues = ["voice", "man-made object", "weather", "environment"]
        elif currentCol == "HP-MicLocation":
            validValues = ["built in", "attached to recorder", "attached to subject", "boom pole"]
        elif currentCol == "HP-AngleofRecording":
            validValues = ["12:00", "1:00", "2:00", "3:00", "4:00", "5:00", "6:00", "7:00", "8:00", "9:00", "10:00", "11:00"]
        elif currentCol == 'HP-PrimarySecondary':
            validValues = ['primary', 'secondary']
        elif currentCol == 'HP-ZoomLevel':
            validValues = ['max optical zoom', 'max digital zoom', 'no zoom']
        elif currentCol == 'HP-Recapture':
            validValues = ['Screenshot', 'scan', 're-photograph']
        elif currentCol == 'HP-LightSource':
            validValues = ['overhead fluorescent', 'daylight', 'cloudy', 'two surrounding fluorescent lights', 'Two Impact Fluorescent Ready Cool 22 lights on each side']
        elif currentCol == 'HP-Orientation':
            validValues = ['landscape', 'portrait']
        elif currentCol == 'HP-DynamicStatic':
            validValues = ['dynamic', 'static']

        elif currentCol in ['ImageWidth', 'ImageHeight', 'BitDepth']:
            validValues = {'instructions':'Any integer value'}
        elif currentCol in ['GPSLongitude', 'GPSLatitude']:
            validValues = {'instructions':'Coodinates, specified in decimal degree format'}
        elif currentCol == 'HP-CollectionRequestID':
            validValues = {'instructions':'Request ID for this image, if applicable'}
        elif currentCol == 'CreationDate':
            validValues = {'instructions':'Date/Time, specified as \"YYYY:MM:DD HH:mm:SS\"'}
        elif currentCol == 'FileType':
            validValues = {'instructions':'Any file extension, without the dot (.) (e.g. jpg, png)'}
        elif currentCol == 'HP-LensLocalID':
            validValues = {'instructions':'Local ID number (PAR, RIT) of lens'}
        elif currentCol == 'HP-NumberOfSpeakers':
            validValues = {'instructions':'Number of people speaking in recording. Do not count background noise.'}

        else:
            validValues = {'instructions':'Any string of text'}

        self.validateBox.delete(0, END)
        if type(validValues) == dict:
            self.validateBox.insert(END, validValues['instructions'])
            self.validateBox.unbind('<<ListboxSelect>>')
        else:
            for v in validValues:
                self.validateBox.insert(END, v)
            self.validateBox.bind('<<ListboxSelect>>', self.insert_item)

    def load_device_exif(self, field):
        output = []
        for cameraID, data in self.devices.iteritems():
            for configuration in data['exif']:
                output.append(configuration[field])
        return sorted(set([x for x in output if x is not None]), key = lambda s: s.lower())

    def insert_item(self, event=None):
        selection = event.widget.curselection()
        val = event.widget.get(selection[0])
        if self.on_main_tab:
            currentTable = self.pt
        else:
            currentTable = self.tabpt
        row = currentTable.getSelectedRow()
        col = currentTable.getSelectedColumn()
        if hasattr(currentTable, 'disabled_cells') and (row, col) in currentTable.disabled_cells:
            return
        currentTable.undo = [(currentTable.model.getValueAt(row, col), row, col)]
        currentTable.model.setValueAt(val, row, col)
        currentTable.redraw()
        if hasattr(currentTable, 'cellentry'):
            currentTable.cellentry.destroy()
        currentTable.parentframe.focus_set()

    def load_images(self):
        self.imageDir = tkFileDialog.askdirectory(initialdir=self.dir)
        self.focus_set()

    def open_spreadsheet(self):
        if self.dir and not self.ritCSV:
            self.csvdir = os.path.join(self.dir, 'csv')
            for f in os.listdir(self.csvdir):
                if f.endswith('.csv') and 'rit' in f:
                    self.ritCSV = os.path.join(self.csvdir, f)
        self.title(self.ritCSV)
        self.pt.importCSV(self.ritCSV)

        self.booleanColNums = []
        self.booleanColNames = ['HP-OnboardFilter', 'HP-WeakReflection', 'HP-StrongReflection', 'HP-TransparentReflection',
                        'HP-ReflectedObject', 'HP-Shadows', 'HP-HDR', 'HP-Inside', 'HP-Outside', 'HP-MultiInput', 'HP-Echo', 'HP-Modifier']
        for b in self.booleanColNames:
            self.booleanColNums.append(self.pt.model.df.columns.get_loc(b))

        self.mandatoryImage = []
        self.mandatoryImageNames = ['HP-OnboardFilter', 'HP-WeakReflection', 'HP-StrongReflection', 'HP-TransparentReflection', 'HP-ReflectedObject',
                 'HP-Shadows', 'HP-HDR', 'HP-DeviceLocalID', 'HP-Inside', 'HP-Outside', 'HP-PrimarySecondary']
        for i in self.mandatoryImageNames:
            self.mandatoryImage.append(self.pt.model.df.columns.get_loc(i))

        self.mandatoryVideo = []
        self.mandatoryVideoNames = self.mandatoryImageNames + ['HP-CameraKinematics']
        for v in self.mandatoryVideoNames:
            self.mandatoryVideo.append(self.pt.model.df.columns.get_loc(v))

        self.mandatoryAudioNames = ['HP-DeviceLocalID', 'HP-OnboardFilter', 'HP-ProximitytoSource', 'HP-MultiInput', 'HP-AudioChannels',
                 'HP-Echo', 'HP-BackgroundNoise', 'HP-Description', 'HP-Modifier','HP-AngleofRecording', 'HP-MicLocation',
                 'HP-Inside', 'HP-Outside', 'HP-NumberOfSpeakers']
        self.mandatoryAudio = []
        for c in self.mandatoryAudioNames:
            self.mandatoryAudio.append(self.pt.model.df.columns.get_loc(c))

        self.disabledColNames = ['HP-DeviceLocalID', 'HP-CameraModel', 'CameraModel', 'DeviceSN']
        self.disabledCols = []
        for d in self.disabledColNames:
            self.disabledCols.append(self.pt.model.df.columns.get_loc(d))

        #self.mandatory = {'image':self.mandatoryImage, 'video':self.mandatoryVideo, 'audio':self.mandatoryAudio}

        self.color_code_cells()
        self.update_current_image()
        self.master.statusBox.println('Loaded data from ' + self.ritCSV)

    def color_code_cells(self, tab=None):
        if tab is None:
            tab = self.pt
            track_highlights = True
        else:
            track_highlights = False
        tab.disabled_cells = []
        if hasattr(self, 'errorpath') and os.path.exists(self.errorpath):
            with open(self.errorpath) as j:
                self.processErrors = json.load(j)
        else:
            self.processErrors = None
        notnans = tab.model.df.notnull()
        for row in range(0, tab.rows):
            for col in range(0, tab.cols):
                colName = list(tab.model.df)[col]
                currentExt = os.path.splitext(self.pt.model.getValueAt(row, 0))[1].lower()
                x1, y1, x2, y2 = tab.getCellCoords(row, col)
                if notnans.iloc[row, col]:
                    rect = tab.create_rectangle(x1, y1, x2, y2,
                                                fill='#c1c1c1',
                                                outline='#084B8A',
                                                tag='cellrect')
                    tab.disabled_cells.append((row, col))
                if (colName in self.mandatoryImageNames and currentExt in hp_data.exts['IMAGE']) or \
                        (colName in self.mandatoryVideoNames and currentExt in hp_data.exts['VIDEO']) or \
                        (colName in self.mandatoryAudioNames and currentExt in hp_data.exts['AUDIO']):
                    rect = tab.create_rectangle(x1, y1, x2, y2,
                                                fill='#f3f315',
                                                outline='#084B8A',
                                                tag='cellrect')
                    if track_highlights:
                        self.highlighted_cells.append((row, col))
                    if (row, col) in tab.disabled_cells:
                        tab.disabled_cells.remove((row, col))
                if colName in self.disabledColNames:
                    rect = tab.create_rectangle(x1, y1, x2, y2,
                                                fill='#c1c1c1',
                                                outline='#084B8A',
                                                tag='cellrect')
                    if (row, col) not in tab.disabled_cells:
                        tab.disabled_cells.append((row, col))
            image = self.pt.model.df['OriginalImageName'][row]
            if self.processErrors is not None and image in self.processErrors and self.processErrors[image]:
                for error in self.processErrors[image]:
                    errCol = error[0]
                    if errCol != 'CameraMake':
                        try:
                            col = tab.model.df.columns.get_loc(errCol)
                            x1, y1, x2, y2 = tab.getCellCoords(row, col)
                            rect = tab.create_rectangle(x1, y1, x2, y2,
                                                        fill='#ff5b5b',
                                                        outline='#084B8A',
                                                        tag='cellrect')
                            self.error_cells.append((row, col))
                        except KeyError:
                            pass

        tab.lift('cellrect')
        tab.redraw()

    def exportCSV(self, showErrors=True, quiet=False):
        if not self.on_main_tab:
            self.nb.select(self.nbtabs['main'])
            self.update_main()
            self.on_main_tab = True
        self.pt.redraw()
        self.pt.doExport(self.ritCSV)
        tmp = self.ritCSV + '-tmp.csv'
        with open(self.ritCSV, 'r') as source:
            rdr = csv.reader(source)
            with open(tmp, 'wb') as result:
                wtr = csv.writer(result, lineterminator='\n', quoting=csv.QUOTE_ALL)
                for r in rdr:
                    wtr.writerow((r[1:]))
        os.remove(self.ritCSV)
        os.rename(tmp, self.ritCSV)
        self.export_rankOne()
        self.saveState = True
        if not quiet:
            msg = tkMessageBox.showinfo('Status', 'Saved! The spreadsheet will now be validated.')
        if showErrors:
            try:
                (errors, cancelled) = self.validate()
                if cancelled == True:
                    return cancelled
            except (AttributeError, IOError):
                print 'Spreadsheet could not be validated, but will still be saved. Ensure all fields have proper data.'
        return None

    def export_rankOne(self):
        global RVERSION
        self.rankOnecsv = self.ritCSV.replace('-rit.csv', '-rankone.csv')
        with open(os.path.join('data', 'headers.json')) as j:
            headers = json.load(j)['rankone']
        with open(self.rankOnecsv, 'w') as ro:
            wtr = csv.writer(ro, lineterminator='\n', quoting=csv.QUOTE_ALL)
            wtr.writerow([RVERSION])
            now = datetime.datetime.today().strftime('%m/%d/%Y %I:%M:%S %p')
            subset = self.pt.model.df.filter(items=headers)
            importDates = []
            for row in range(0, len(subset.index)):
                importDates.append(now)
            subset['ImportDate'] = importDates
            subset.to_csv(ro, columns=headers, index=False)

    def s3export(self):
        cancelled = self.exportCSV(quiet=True)
        if cancelled:
            return

        # localIDs = set(self.pt.model.df['HP-DeviceLocalID'])
        # if not localIDs.issubset(set(self.devices.keys())):
        #     self.prompt_for_new_camera(invalids=localIDs - set(self.devices.keys()))
        initial = self.settings.get('aws', notFound='')
        val = tkSimpleDialog.askstring(title='Export to S3', prompt='S3 bucket/folder to upload to.', initialvalue=initial)

        if (val is not None and len(val) > 0):
            comment = self.check_trello_login()
            if comment is None:
                tkMessageBox.showinfo(title='Information', message='Upload canceled.')
                return
            self.settings.set('aws', val)
            print('Creating archive...')
            archive = self.create_hp_archive()
            s3 = S3Transfer(boto3.client('s3', 'us-east-1'))
            BUCKET = val.split('/')[0].strip()
            DIR = val[val.find('/') + 1:].strip()
            DIR = DIR if DIR.endswith('/') else DIR + '/'

            print('Uploading...')
            try:
                s3.upload_file(archive, BUCKET, DIR + os.path.split(archive)[1], callback=ProgressPercentage(archive))
                upload_error = False
            except:
                upload_error = True


            # print 'Uploading CSV...'
            # s3.upload_file(self.rankOnecsv, BUCKET, DIR + 'csv/' + os.path.split(self.rankOnecsv)[1])
            #
            # print 'Uploading Image Files [' + str(len(os.listdir(self.imageDir))) +']...'
            # for image in os.listdir(self.imageDir):
            #     s3.upload_file(os.path.join(self.imageDir, image), BUCKET, DIR + 'image/' + image)
            #
            # print 'Uploading Video Files [' + str(len(os.listdir(self.videoDir))) +']...'
            # for video in os.listdir(self.videoDir):
            #     s3.upload_file(os.path.join(self.videoDir, video), BUCKET, DIR + 'video/' + video)
            #
            # print 'Uploading Audio Files [' + str(len(os.listdir(self.videoDir))) +']...'
            # for audio in os.listdir(self.audioDir):
            #     s3.upload_file(os.path.join(self.audioDir, audio), BUCKET, DIR + 'audio/' + audio)

            os.remove(archive)

            if upload_error:
                msg = 'Failed to upload to S3. Make sure your upload path is correct.\nIf you are unsure why this happened, please email medifor_manipulators@partech.com.'
                self.master.statusBox.println(msg)
            else:
                err = self.notify_trello(os.path.basename(archive), comment)
                if err is not None:
                    msg = 'S3 upload completed, but failed to notify Trello (' + str(err) +').\nIf you are unsure why this happened, please email medifor_manipulators@partech.com.'
                    self.master.statusBox.println(msg)
                else:
                    msg = 'Complete!'
                    self.master.statusBox.println(
                        'Successfully uploaded HP data to S3://' + val + '.')
            d = tkMessageBox.showinfo(title='Status', message=msg)
        else:
            tkMessageBox.showinfo(title='Information', message='Upload canceled.')

    def check_trello_login(self):
        if self.settings.get('trello', notFound='') == '':
            token = self.get_trello_token()
            if token == '':
                return None
            self.settings.set('trello', token)
        comment = tkSimpleDialog.askstring(title='Trello Notification', prompt='(Optional) Enter any trello comments for this upload.')
        return comment

    def notify_trello(self, archive, comment):
        if self.settings.get('trello') is None:
            token = self.get_trello_token()
            self.settings.set('trello', token)
        else:
            token = self.settings.get('trello')

        # list ID for "New Devices" list
        list_id = '58f4e07b1d52493b1910598f'

        # post the new card
        new = str(datetime.datetime.now())
        stats = archive + '\n' + self.collect_stats() + '\n' + 'User comment: ' + comment
        resp = requests.post("https://trello.com/1/cards", params=dict(key=self.trello_key, token=token),
                             data=dict(name=new, idList=list_id, desc=stats))

        # attach the file, if the card was successfully posted
        if resp.status_code == requests.codes.ok:
            me = requests.get("https://trello.com/1/members/me", params=dict(key=self.trello_key, token=token))
            member_id = json.loads(me.content)['id']
            new_card_id = json.loads(resp.content)['id']
            resp2 = requests.post("https://trello.com/1/cards/%s/idMembers" % (new_card_id),
                                  params=dict(key=self.trello_key, token=token),
                                  data=dict(value=member_id))
            return None
        else:
            return resp.status_code

    def get_trello_token(self):
        t = TrelloSignInPrompt(self, self.trello_key)
        return t.token.get()

    def prompt_for_new_camera(self, invalids):
        h = NewCameraPrompt(self, invalids, valids=self.devices.keys(), token=self.settings.get('trello'))
        return h.pathVars

    def collect_stats(self):
        images = 0
        videos = 0
        audio = 0
        for data in self.pt.model.df['Type']:
            if data == 'video':
                videos+=1
            elif data == 'audio':
                audio+=1
            else:
                images+=1

        return 'Image Files: ' + str(images) + '\nVideo Files: ' + str(videos) + '\nAudio Files: ' + str(audio)

    def create_hp_archive(self):
        val = self.pt.model.df['HP-DeviceLocalID'][0]
        dt = datetime.datetime.now().strftime('%Y%m%d%H%M%S')[2:]
        fname = os.path.join(self.dir, val + '-' + dt + '.tgz')
        DIRNAME = self.dir
        archive = tarfile.open(fname, "w:gz", errorlevel=2)
        for item in os.listdir(DIRNAME):
            if item != fname:
                archive.add(os.path.join(DIRNAME, item), arcname=item)
        archive.close()
        return fname

    def validate(self):
        errors = []
        types = self.pt.model.df['Type']
        uniqueIDs = []
        for row in range(0, self.pt.rows):
            for col in range(0, self.pt.cols):
                currentColName = self.pt.model.df.columns[col]
                type = types[row]
                val = str(self.pt.model.getValueAt(row, col))
                if currentColName in self.booleanColNames:
                    if val.title() == 'True' or val.title() == 'False':
                        self.pt.model.setValueAt(val.title(), row, col)
                    elif type == 'image' and col in self.mandatoryImage:
                        errors.append('Invalid entry at column ' + currentColName + ', row ' + str(
                            row + 1) + '. Value must be True or False')
                    elif type == 'video' and col in self.mandatoryVideo:
                        errors.append('Invalid entry at column ' + currentColName + ', row ' + str(
                            row + 1) + '. Value must be True or False')
                    elif type == 'audio' and col in self.mandatoryAudio:
                        errors.append('Invalid entry at column ' + currentColName + ', row ' + str(
                            row + 1) + '. Value must be True or False')
            errors.extend(self.parse_process_errors(row))
            errors.extend(self.check_model(row))
            errors.extend(self.check_kinematics(row))
            errors.extend(self.check_localID(row))
            if self.pt.model.df['HP-DeviceLocalID'][row] not in uniqueIDs:
                uniqueIDs.append(self.pt.model.df['HP-DeviceLocalID'][row])

        for coord in self.highlighted_cells:
            val = str(self.pt.model.getValueAt(coord[0], coord[1]))
            if val == '':
                currentColName = list(self.pt.model.df.columns.values)[coord[1]]
                errors.append('Invalid entry at column ' + currentColName + ', row ' + str(
                            coord[0] + 1) + '. This cell is mandatory.')

        if len(uniqueIDs) > 1:
            errors.append('Multiple cameras identified. Each processed dataset should contain data from only one camera.')

        cancelPressed = None
        if errors:
            d = ErrorWindow(self, errors)
            cancelPressed = d.cancelPressed

        return errors, cancelPressed

    def parse_process_errors(self, row):
        errors = []
        imageName = self.pt.model.df['OriginalImageName'][row]
        if hasattr(self, 'processErrors') and imageName in self.processErrors:
            for err in self.processErrors[imageName]:
                errors.append(err[1] + ' (row ' + str(row) + ')')
        return errors

    def check_save(self):
        if self.saveState == False:
            message = 'Would you like to save before closing this sheet?'
            confirm = tkMessageBox.askyesnocancel(title='Save On Close', message=message, default=tkMessageBox.YES)
            if confirm:
                errs = self.exportCSV(showErrors=False)
                if not errs:
                    self.destroy()
            elif confirm is None:
                pass
            else:
                self.destroy()
        else:
            self.destroy()

    def load_kinematics(self):
        try:
            dataFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'Kinematics.csv')
            df = pd.read_csv(dataFile)
        except IOError:
            tkMessageBox.showwarning('Warning', 'Camera kinematics reference not found! (hp_tool/data/Kinematics.csv')
            return []
        return [x.strip() for x in df['Camera Kinematics']]

    def check_kinematics(self, row):
        errors = []
        kinematic = self.pt.model.df['HP-CameraKinematics'][row]
        type = self.pt.model.df['Type'][row]
        if type.lower() == 'video':
            if str(kinematic).lower() == 'nan' or str(kinematic) == '':
                imageName = self.pt.model.df['ImageFilename'][row]
                errors.append('No camera kinematic entered for ' + imageName + ' (row ' + str(row + 1) + ')')
            elif kinematic.lower() not in [x.lower() for x in self.kinematics]:
                errors.append('Invalid camera kinematic ' + kinematic + ' (row ' + str(row + 1) + ')')
        return errors

    def load_apps(self):
        try:
            dataFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'apps.csv')
            df = pd.read_csv(dataFile)
        except IOError:
            tkMessageBox.showwarning('Warning', 'HP-App reference not found! (hp_tool/data/apps.csv)')
            return
        apps = [w.strip() for w in df['AppName']]
        return sorted(list(set(apps)))

    def load_lens_filters(self):
        try:
            dataFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'LensFilters.csv')
            df = pd.read_csv(dataFile)
        except IOError:
            tkMessageBox.showwarning('Warning', 'LensFilter reference not found! (hp_tool/data/LensFilters.csv)')
            return
        filters = [w.lower().strip() for w in df['LensFilter']]
        return sorted(list(set(filters)))

    def load_devices(self):
        models = [self.devices[data]['hp_camera_model'] for data in self.devices if self.devices[data]['hp_camera_model'] is not None]
        localIDs = self.devices.items()
        return sorted(list(set(models))), localIDs

    def check_model(self, row):
        errors = []
        model = self.pt.model.df['HP-CameraModel'][row]
        if model.lower() == 'nan' or model == '':
            imageName = self.pt.model.getValueAt(row, 0)
            errors.append('No camera model entered for ' + imageName + ' (row ' + str(row + 1) + ')')
        elif model not in [self.devices[data]['hp_camera_model'] for data in self.devices if
                         self.devices[data]['hp_camera_model'] is not None]:
            errors.append('Invalid camera model ' + model + ' (row ' + str(row + 1) + ')')
        return errors

    def check_localID(self, row):
        errors = []
        localID = self.pt.model.df['HP-DeviceLocalID'][row]
        if localID.lower() == 'nan' or localID == '':
            imageName = self.pt.model.getValueAt(row, 0)
            errors.append('No Device Local ID entered for ' + imageName + ' (row' + str(row + 1) + ')')
        elif localID not in [self.devices[data]['hp_device_local_id'] for data in self.devices if
                         self.devices[data]['hp_device_local_id'] is not None]:
            errors.append('Invalid localID ' + localID + ' (row ' + str(row + 1) + ')')
        return errors

class NewCameraPrompt(tkSimpleDialog.Dialog):
    def __init__(self, master, invalids, valids=None, token=None):
        self.invalids = invalids
        self.master = master
        self.valids = valids if valids is not None else []
        self.pathVars = {}
        tkSimpleDialog.Dialog.__init__(self, master)
        self.token = token
        self.title('New Devices')

    def body(self, master):
        r=0
        Label(self, text='The following device local IDs are invalid. Please provide a text file with the completed "New Camera" form.').grid(row=r, columnspan=3)
        for newDevice in self.invalids:
            r+=1
            self.pathVars[newDevice] = StringVar()
            Label(self, text=newDevice).grid(row=r, column=0)
            e = Entry(self, textvar=self.pathVars[newDevice])
            e.grid(row=r, column=1)
            # b = Button(self, text='Complete form', command=lambda: self.open_form(self.pathVars[newDevice]))
            # b.grid(row=r, column=2)

    def open_form(self, pathVar):
        h = HP_Device_Form(self, self.valids, pathvar=pathVar, token=self.token)


class TrelloSignInPrompt(tkSimpleDialog.Dialog):
    def __init__(self, master, key='dcb97514b94a98223e16af6e18f9f99e'):
        self.master=master
        self.token = StringVar()
        self.trello_key = key
        tkSimpleDialog.Dialog.__init__(self, master)

    def body(self, master):
        Label(self, text='Please enter your Trello API token. If you do not know it, access it here: ').pack()
        b = Button(self, text='Get Token', command=self.open_trello_token)
        b.pack()
        e = Entry(self, textvar=self.token)
        e.pack()

    def open_trello_token(self):
        webbrowser.open('https://trello.com/1/authorize?key=' + self.trello_key + '&scope=read%2Cwrite&name=HP_GUI&expiration=never&response_type=token')


class ProgressPercentage(object):
    """
    http://boto3.readthedocs.io/en/latest/_modules/boto3/s3/transfer.html
    """
    def __init__(self, filename, total_files=None, count=None):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        if total_files and count:
            self.percent_of_total = (count / total_files) * 100

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            p = '[%.2f%% of total files uploaded.]' % self.percent_of_total if hasattr(self, 'percent_of_total') else ''
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%) " % (
                    self._filename, self._seen_so_far, self._size,
                    percentage) + p)
            sys.stdout.flush()


class CustomTable(pandastable.Table):
    def __init__(self, master, **kwargs):
        pandastable.Table.__init__(self, parent=master, **kwargs)
        self.copied_val = None

    def doBindings(self):
        """Bind keys and mouse clicks, this can be overriden"""

        self.bind("<Button-1>", self.handle_left_click)
        self.bind("<Double-Button-1>", self.handle_double_click)
        self.bind("<Control-Button-1>", self.handle_left_ctrl_click)
        self.bind("<Shift-Button-1>", self.handle_left_shift_click)

        self.bind("<ButtonRelease-1>", self.handle_left_release)
        if self.ostyp == 'mac':
            # For mac we bind Shift, left-click to right click
            self.bind("<Button-2>", self.handle_right_click)
            self.bind('<Shift-Button-1>', self.handle_right_click)
        else:
            self.bind("<Button-3>", self.handle_right_click)

        self.bind('<B1-Motion>', self.handle_mouse_drag)
        # self.bind('<Motion>', self.handle_motion)

        self.bind("<Control-c>", self.copy)
        # self.bind("<Control-x>", self.deleteRow)
        # self.bind_all("<Control-n>", self.addRow)
        self.bind("<Delete>", self.clearData)
        self.bind("<Control-v>", self.paste)
        self.bind("<Control-a>", self.selectAll)

        self.bind("<Right>", self.handle_arrow_keys)
        self.bind("<Left>", self.handle_arrow_keys)
        self.bind("<Up>", self.handle_arrow_keys)
        self.bind("<Down>", self.handle_arrow_keys)
        self.bind("<Tab>", self.handle_tab)
        self.parentframe.master.bind_all("<Return>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<KP_8>", self.handle_arrow_keys)
        # if 'windows' in self.platform:
        self.bind("<MouseWheel>", self.mouse_wheel)
        self.bind('<Button-4>', self.mouse_wheel)
        self.bind('<Button-5>', self.mouse_wheel)

        #######################################
        self.bind('<Control-Key-t>', self.enter_true)
        self.bind('<Control-Key-f>', self.enter_false)
        self.bind('<Control-Key-d>', self.fill_selection)
        self.bind('<Control-Key-g>', self.fill_column)
        self.bind('<Control-Key-c>', self.copy_value)
        self.bind('<Control-Key-v>', self.paste_value)
        #self.bind('<Return>', self.handle_double_click)
        ########################################

        self.focus_set()
        return

    def enter_true(self, event=None):
        self.fill_selection(val='True')

    def enter_false(self, event=None):
        self.fill_selection(val='False')

    def fill_selection(self, event=None, val=None):
        if hasattr(self, 'disabled_cells'):
            if not self.check_disabled_cells(range(self.startrow,self.endrow+1),
                                             range(self.startcol, self.endcol+1)):
                return
        self.undo = []
        self.focus_set()
        col = self.getSelectedColumn()
        row = self.getSelectedRow()
        val = val if val is not None else self.model.getValueAt(row, col)
        for row in range(self.startrow,self.endrow+1):
            for col in range(self.startcol, self.endcol+1):
                if hasattr(self, 'disabled_cells') and (row, col) in self.disabled_cells:
                    continue
                self.undo.append((self.model.getValueAt(row, col), row, col))
                self.model.setValueAt(val, row, col)
        self.redraw()
        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()

    def fill_column(self, event=None):
        col = self.getSelectedColumn()
        rowList = range(0, self.rows)
        if hasattr(self, 'disabled_cells'):
            if not self.check_disabled_cells(rowList, [col]):
                return
        self.focus_set()
        self.undo = []
        row = self.getSelectedRow()
        val = self.model.getValueAt(row, col)
        for row in rowList:
            if hasattr(self, 'disabled_cells') and (row, col) in self.disabled_cells:
                continue
            self.undo.append((self.model.getValueAt(row, col), row, col))
            self.model.setValueAt(val, row, col)
        self.redraw()
        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()

    def check_disabled_cells(self, rows, columns):
        for row in rows:
            for col in columns:
                if (row, col) in self.disabled_cells:
                    return tkMessageBox.askyesno(title='Error',
                                          message='Some cells in column are disabled. Would you like to fill the valid ones?')
        return True

    def copy_value(self, event=None):
        self.focus_set()
        col = self.getSelectedColumn()
        row = self.getSelectedRow()
        self.copied_val = self.model.getValueAt(row, col)
        self.redraw()

    def paste_value(self, event=None):
        self.focus_set()
        col = self.getSelectedColumn()
        row = self.getSelectedRow()
        if hasattr(self, 'disabled_cells') and (row, col) in self.disabled_cells:
            return
        if self.copied_val is not None:
            self.undo = [(self.model.getValueAt(row, col), row, col)]
            self.model.setValueAt(self.copied_val, row, col)
        self.redraw()

    def move_selection(self, event, direction='down', entry=False):
        row = self.getSelectedRow()
        col = self.getSelectedColumn()
        if direction == 'down':
            self.currentrow += 1
        elif direction == 'up':
            self.currentrow -= 1
        elif direction == 'left':
            self.currentcol -= 1
        else:
            self.currentcol += 1

        if entry:
            self.drawCellEntry(self.currentrow, self.currentcol)

    def handle_tab(self, event=None):
        self.handle_arrow_keys(direction='Right')

    def handle_arrow_keys(self, event=None, direction=None):
        """Handle arrow keys press"""
        # print event.keysym

        # row = self.get_row_clicked(event)
        # col = self.get_col_clicked(event)
        x, y = self.getCanvasPos(self.currentrow, 0)
        if x == None:
            return
        if event is not None:
            direction = event.keysym

        if direction == 'Up':
            if self.currentrow == 0:
                return
            else:
                # self.yview('moveto', y)
                # self.rowheader.yview('moveto', y)
                self.currentrow = self.currentrow - 1
        elif direction == 'Down':
            if self.currentrow >= self.rows - 1:
                return
            else:
                # self.yview('moveto', y)
                # self.rowheader.yview('moveto', y)
                self.currentrow = self.currentrow + 1
        elif direction == 'Right' or direction == 'Tab':
            if self.currentcol >= self.cols - 1:
                if self.currentrow < self.rows - 1:
                    self.currentcol = 0
                    self.currentrow = self.currentrow + 1
                else:
                    return
            else:
                self.currentcol = self.currentcol + 1
        elif direction == 'Left':
            if self.currentcol == 0:
                if self.currentrow > 0:
                    self.currentcol = self.cols - 1
                    self.currentrow = self.currentrow - 1
                else:
                    return
            else:
                self.currentcol = self.currentcol - 1
        self.drawSelectedRect(self.currentrow, self.currentcol)
        self.startrow = self.currentrow
        self.endrow = self.currentrow
        self.startcol = self.currentcol
        self.endcol = self.currentcol
        self.handle_left_click()
        self.handle_double_click()
        return

    def drawCellEntry(self, row, col, text=None):
        """When the user single/double clicks on a text/number cell,
          bring up entry window and allow edits."""

        if self.editable == False:
            return
        if hasattr(self, 'disabled_cells') and (row, col) in self.disabled_cells:
            return

        h = self.rowheight
        model = self.model
        text = self.model.getValueAt(row, col)
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        w=x2-x1
        self.cellentryvar = txtvar = StringVar()
        txtvar.set(text)

        self.cellentry = Entry(self.parentframe,width=20,
                        textvariable=txtvar,
                        takefocus=1,
                        font=self.thefont)
        self.cellentry.icursor(END)
        self.cellentry.bind('<Return>', lambda x: self.cellentryCallback(row,col, direction='Down'))
        self.cellentry.bind("<Right>", lambda x: self.cellentryCallback(row,col, direction='Right'))
        self.cellentry.bind("<Left>", lambda x: self.cellentryCallback(row,col, direction='Left'))
        self.cellentry.bind("<Up>", lambda x: self.cellentryCallback(row,col, direction='Up'))
        self.cellentry.bind("<Down>", lambda x: self.cellentryCallback(row,col, direction='Down'))
        self.cellentry.bind("<Tab>", lambda x: self.cellentryCallback(row,col, direction='Right'))

        self.cellentry.bind('<Control-Key-t>', self.enter_true)
        self.cellentry.bind('<Control-Key-f>', self.enter_false)
        self.cellentry.bind('<Control-Key-d>', self.fill_selection)
        self.cellentry.bind('<Control-Key-g>', self.fill_column)
        self.cellentry.bind('<Control-Key-c>', self.copy_value)
        self.cellentry.bind('<Control-Key-v>', self.paste_value)
        self.cellentry.focus_set()
        self.entrywin = self.create_window(x1,y1,
                                width=w,height=h,
                                window=self.cellentry,anchor='nw',
                                tag='entry')
        return

    def cellentryCallback(self, row, col, direction=None):
        """Callback for cell entry"""

        value = self.cellentryvar.get()
        self.model.setValueAt(value,row,col)
        self.redraw()
        #self.drawText(row, col, value, align=self.align)
        #self.delete('entry')
        self.gotonextCell(direction)
        return

    def handle_left_click(self, event=None):
        """Respond to a single press"""

        self.clearSelected()
        self.allrows = False
        #which row and column is the click inside?
        if event is not None:
            rowclicked = self.get_row_clicked(event)
            colclicked = self.get_col_clicked(event)
        else:
            rowclicked = self.startrow
            colclicked = self.startcol
        if colclicked == None:
            return
        try:
            self.focus_set()
        except:
            pass

        if hasattr(self, 'cellentry'):
            #self.cellentryCallback()
            self.cellentry.destroy()
        #ensure popup menus are removed if present
        if hasattr(self, 'rightmenu'):
            self.rightmenu.destroy()
        if hasattr(self.tablecolheader, 'rightmenu'):
            self.tablecolheader.rightmenu.destroy()

        self.startrow = rowclicked
        self.endrow = rowclicked
        self.startcol = colclicked
        self.endcol = colclicked
        #reset multiple selection list
        self.multiplerowlist=[]
        self.multiplerowlist.append(rowclicked)
        if 0 <= rowclicked < self.rows and 0 <= colclicked < self.cols:
            self.setSelectedRow(rowclicked)
            self.setSelectedCol(colclicked)
            self.drawSelectedRect(self.currentrow, self.currentcol)
            self.drawSelectedRow()
            self.rowheader.drawSelectedRows(rowclicked)
            self.tablecolheader.delete('rect')
        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        return

    def handle_double_click(self, event=None):
        """Do double click stuff. Selected row/cols will already have
           been set with single click binding"""

        if event is not None:
            rowclicked = self.get_row_clicked(event)
            colclicked = self.get_col_clicked(event)
        else:
            rowclicked = self.startrow
            colclicked = self.startcol
        self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def gotonextCell(self, direction=None):
        """Move highlighted cell to next cell in row or a new col"""
        if direction is None:
            direction = 'right'
        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()

        self.handle_arrow_keys(direction=direction)
        # self.currentrow = self.currentrow+1
        # if self.currentcol >= self.cols-1:
        #     self.currentcol = self.currentcol+1
        #self.drawSelectedRect(self.currentrow, self.currentcol)
        # self.handle_left_click()
        # self.handle_double_click()
        return

    def clearSelected(self):
        """Clear selections"""
        try:
            self.delete('rect')
            self.delete('entry')
            self.delete('tooltip')
            self.delete('searchrect')
            self.delete('colrect')
            self.delete('multicellrect')
        except TclError:
            pass
        return

    def importCSV(self, filename=None, dialog=False):
        """Import from csv file"""

        if self.importpath == None:
            self.importpath = os.getcwd()
        if filename == None:
            filename = tkFileDialog.askopenfilename(parent=self.master,
                                                          defaultextension='.csv',
                                                          initialdir=self.importpath,
                                                          filetypes=[("csv","*.csv"),
                                                                     ("tsv","*.tsv"),
                                                                     ("txt","*.txt"),
                                                            ("All files","*.*")])
        if not filename:
            return
        if dialog == True:
            df = None
        else:
            df = pd.read_csv(filename, dtype=str, quoting=1)
        model = pandastable.TableModel(dataframe=df)
        self.updateModel(model)
        self.redraw()
        self.importpath = os.path.dirname(filename)
        return


    # right click menu!
    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        defaultactions = {
                        "Copy" : self.copy_value,
                        "Paste" : self.paste_value,
                        "Fill Selection" : self.fill_selection,
                        "Fill True" : self.enter_true,
                        "Fill False" : self.enter_false,
                        #"Fill Down" : lambda: self.fillDown(rows, cols),
                        #"Fill Right" : lambda: self.fillAcross(cols, rows),
                        #"Add Row(s)" : lambda: self.addRows(),
                        #"Delete Row(s)" : lambda: self.deleteRow(),
                        #"Add Column(s)" : lambda: self.addColumn(),
                        #"Delete Column(s)" : lambda: self.deleteColumn(),
                        "Clear Data" : lambda: self.deleteCells(rows, cols),
                        "Select All" : self.selectAll,
                        #"Auto Fit Columns" : self.autoResizeColumns,
                        #"Table Info" : self.showInfo,
                        #"Show as Text" : self.showasText,
                        #"Filter Rows" : self.queryBar,
                        #"New": self.new,
                        #"Load": self.load,
                        # "Save": self.save,
                        # "Save as": self.saveAs,
                        # "Import csv": lambda: self.importCSV(dialog=True),
                        # "Export": self.doExport,
                        # "Plot Selected" : self.plotSelected,
                        # "Hide plot" : self.hidePlot,
                        # "Show plot" : self.showPlot,
                        # "Preferences" : self.showPrefs
            }

        main = ["Copy", "Paste", "Fill Selection", "Fill True", "Fill False", "Clear Data", "Select All"]
        general = []

        filecommands = []
        plotcommands = []

        def createSubMenu(parent, label, commands):
            menu = Menu(parent, tearoff = 0)
            popupmenu.add_cascade(label=label,menu=menu)
            for action in commands:
                menu.add_command(label=action, command=defaultactions[action])
            return menu

        def add_commands(fieldtype):
            """Add commands to popup menu for column type and specific cell"""
            functions = self.columnactions[fieldtype]
            for f in list(functions.keys()):
                func = getattr(self, functions[f])
                popupmenu.add_command(label=f, command= lambda : func(row,col))
            return

        popupmenu = Menu(self, tearoff = 0)
        def popupFocusOut(event):
            popupmenu.unpost()

        if outside == None:
            #if outside table, just show general items
            row = self.get_row_clicked(event)
            col = self.get_col_clicked(event)
            coltype = self.model.getColumnType(col)
            def add_defaultcommands():
                """now add general actions for all cells"""
                for action in main:
                    if action == 'Fill Down' and (rows == None or len(rows) <= 1):
                        continue
                    if action == 'Fill Right' and (cols == None or len(cols) <= 1):
                        continue
                    else:
                        popupmenu.add_command(label=action, command=defaultactions[action])
                return

            if coltype in self.columnactions:
                add_commands(coltype)
            add_defaultcommands()

        for action in general:
            popupmenu.add_command(label=action, command=defaultactions[action])

        #popupmenu.add_separator()
        # createSubMenu(popupmenu, 'File', filecommands)
        # createSubMenu(popupmenu, 'Plot', plotcommands)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        return popupmenu
