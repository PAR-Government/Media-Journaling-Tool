from Tkinter import *
import matplotlib
matplotlib.use("TkAgg")
import pandastable
import pandas
import shutil
import ttk
import tkFileDialog
import tkMessageBox
import numpy as np
from hp_data import *
from HPSpreadsheet import HPSpreadsheet
from KeywordsSheet import KeywordsSheet
from prefs import Preferences

class HPGUI(Frame):

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master=master
        self.prefsfilename = StringVar()
        self.prefsfilename.set(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'preferences.txt'))
        self.metadatafilename = StringVar()
        self.metadatafilename.set(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'metadata.txt'))
        self.grid()
        self.oldImageNames = []
        self.newImageNames = []
        self.createWidgets()
        self.load_defaults()

    def update_defaults(self):
        originalFileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'preferences.txt')
        tmpFileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'tmp.txt')
        insertInputDir = True
        insertOutputDir = True
        with open(tmpFileName, 'wb') as new:
            with open(originalFileName, 'rb') as original:
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
        os.remove(originalFileName)
        shutil.move(tmpFileName, originalFileName)

    def load_defaults(self):
        self.prefs = parse_prefs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'preferences.txt'))
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

            # if 'metadata' in self.prefs:
            #     self.metadatafilename.insert(END, self.prefs['metadata'])
            # else:
            #     self.metadatafilename.insert(END, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'metadata.txt'))

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
        prefs = parse_prefs(self.prefsfilename.get())
        if prefs and prefs.has_key('seq'):
            testNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                        prefs['organization'] + prefs['username'] + '-' + prefs['seq']
            if self.additionalinfo.get():
                testNameStr += '-' + self.additionalinfo.get()
        tkMessageBox.showinfo('Filename Preview', testNameStr)


    def go(self):
        shortFields = ['collReq', 'localcam', 'locallens', 'hd']
        kwargs = {'preferences':self.prefsfilename.get(),
                  'metadata':self.metadatafilename.get(),
                  'imgdir':self.inputdir.get(),
                  'outputdir':self.outputdir.get(),
                  'recursive':self.recBool.get(),
                  'additionalInfo':self.additionalinfo.get(),
                  }
        for fieldNum in xrange(len(shortFields)):
            kwargs[shortFields[fieldNum]] = self.attributes[self.descriptionFields[fieldNum]].get()

        self.update_defaults()

        (self.oldImageNames, self.newImageNames) = process(**kwargs)
        aSheet = HPSpreadsheet(dir=self.outputdir.get(), master=self.master)
        aSheet.open_spreadsheet()
        self.keywordsbutton.config(state=NORMAL)
        keySheet = self.open_keywords_sheet()
        keySheet.close()

    def open_keywords_sheet(self):
        keywords = KeywordsSheet(dir=self.outputdir.get(), master=self.master, newImageNames=self.newImageNames, oldImageNames=self.oldImageNames)
        keywords.open_spreadsheet()
        return keywords

    def open_old_rit_csv(self):
        csv = tkFileDialog.askopenfilename(initialdir=self.outputdir.get())
        HPSpreadsheet(dir=self.outputdir.get(), ritCSV=csv, master=self.master).open_spreadsheet()

    def open_old_keywords_csv(self):
        csv = tkFileDialog.askopenfilename(initialdir=self.outputdir.get())
        KeywordsSheet(dir=self.outputdir.get(), keyCSV=csv, master=self.master).open_spreadsheet()

    def open_prefs(self):
        Preferences(master=self.master)
        if parse_prefs(self.prefsfilename.get()):
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

        self.menubar = Menu(self)
        self.fileMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='File', menu=self.fileMenu)
        self.fileMenu.add_command(label='Open HP Data Spreadsheet for Editing', command=self.open_old_rit_csv, accelerator='ctrl-o')
        self.fileMenu.add_command(label='Open Keywords Spreadsheet for Editing', command=self.open_old_keywords_csv)
        self.fileMenu.add_command(label='Settings...', command=self.open_prefs)
        self.master.config(menu=self.menubar)

def main():
    root = Tk()
    root.resizable(width=False, height=False)
    root.wm_title('HP GUI')
    app = HPGUI(master=root)
    app.mainloop()

if __name__ == '__main__':
    main()