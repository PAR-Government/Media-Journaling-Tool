import tarfile
from Tkinter import *
import ttk
import collections
import tempfile
import boto3
import matplotlib
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
                    msg = 'There should be no files in the root directory. Only \"Images\" and \"Video\" folders.'
                    break

            elif last.lower() in ['images', 'video']:
                if not self.has_same_contents(dirs, ['primary', 'secondary']):
                    msg = 'Images and Video folders must each contain Primary and Secondary folders.'
                if files:
                    msg = 'There should be no additional files in the ' + last + ' directory. Only \"Primary\" and \"Secondary\".'
            elif last.lower() == 'primary' or last.lower() == 'secondary':
                for sub in dirs:
                    if sub.lower() not in self.vocab:
                        msg = 'Invalid reference type: ' + sub
                        break
                if files:
                    msg = 'There should be no additional files in the ' + last + ' directory. Only PRNU reference type folders (White_Screen, Blue_Sky, etc).'
                    break
            elif last.lower() in self.vocab:
                if dirs:
                    msg = 'There should be no additional subfolders in folder ' + path

        if passed_root == False:
            msg = 'Device local ID does not match reference. If this is a new camera, please register it with the Google form by clicking below.'
            link = 'http://bit.ly/2ogxwWu'
            bt = 'Take me to the form! (Opens your default web browser).'
            w = WeblinkMessageBox(self, msg=msg, link=link, buttonText=bt)
            w.show_message()
            msg = 'hide'

        if msg == 'hide':
            pass
        elif msg:
            tkMessageBox.showerror(title='Error', message=msg)
        else:
            tkMessageBox.showinfo(title='Complete', message='Everything looks good. Click ok to begin upload.')
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

        self.uploadButton.config(state=DISABLED)
        tkMessageBox.showinfo(title='PRNU Upload', message='Complete!')
        print '... done'

    def cancel_upload(self):
        self.uploadButton.config(state=DISABLED)
        self.rootEntry.config(state=NORMAL)
        self.localCamEntry.config(state=NORMAL)

    def archive_prnu(self):
        fd, zf = tempfile.mkstemp(suffix='.tar')
        archive = tarfile.open(zf, "w", errorlevel=2)
        archive.add(self.root_dir.get(), arcname=os.path.split(self.root_dir.get())[1])
        archive.close()
        os.close(fd)
        return zf

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

class WeblinkMessageBox(Toplevel):
    def __init__(self, master, msg, link, buttonText='Ok'):
        Toplevel.__init__(self, master)
        self.msg = msg
        self.link = link
        self.bt = buttonText

    def show_message(self):
        label = Label(self, text=self.msg).grid(row=0,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=11)
        ok = Button(self, text=self.bt, command=self.open_link)
        ok.grid(row=1,column=5, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        cl = Button(self, text='Cancel', command=self.cancel)
        cl.grid(row=1, column=6, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)

    def open_link(self):
        webbrowser.open_new(self.link)

    def cancel(self):
        self.destroy()

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
        self.master.config(menu=self.menubar)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=BOTH, expand=1)
        f1 = HP_Starter(master=self.nb, prefs=self.prefs)
        f2 = PRNU_Uploader(master=self.nb, prefs=self.prefs)
        self.nb.add(f1, text='Process HP Data')
        self.nb.add(f2, text='Export PRNU Data')

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


def main():
    root = Tk()
    root.resizable(width=False, height=False)
    root.wm_title('HP GUI')
    HPGUI(master=root).pack(side=TOP, fill=BOTH, expand=TRUE)
    root.mainloop()

if __name__ == '__main__':
    main()