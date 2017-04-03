from Tkinter import *
import os
import pandas as pd
import numpy as np
import tkMessageBox
import pandastable
import csv
import datetime
from ErrorWindow import ErrorWindow
from HPSpreadsheet import HPSpreadsheet, CustomTable
from PIL import Image, ImageTk

class KeywordsSheet(HPSpreadsheet):
    def __init__(self, dir=None, keyCSV=None, master=None, oldImageNames=[], newImageNames=[]):
        self.keywords = self.load_keywords()
        HPSpreadsheet.__init__(self, dir=dir, master=master)
        self.oldImageNames = oldImageNames
        self.newImageNames = newImageNames
        self.dir = dir
        if self.dir:
            self.imageDir = os.path.join(self.dir, 'image')
        self.master = master
        self.keyCSV = keyCSV
        self.saveState = True
        self.protocol("WM_DELETE_WINDOW", self.check_save)

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.topFrame = Frame(self)
        self.topFrame.pack(side=TOP, fill=X)
        self.rightFrame = Frame(self, width=480)
        self.rightFrame.pack(side=RIGHT, fill=Y)
        self.leftFrame = Frame(self)
        self.leftFrame.pack(side=LEFT, fill=BOTH, expand=1)
        self.pt = CustomTable(self.leftFrame, scrollregion=None, width=1024, height=720)
        self.leftFrame.pack(fill=BOTH, expand=1)
        self.pt.show()
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

        for v in self.keywords:
            self.validateBox.insert(END, v)
        self.validateBox.bind('<<ListboxSelect>>', self.insert_item)

        self.menubar = Menu(self)
        self.fileMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.add_command(label='Save', command=self.exportCSV, accelerator='ctrl-s')
        self.fileMenu.add_command(label='Load image directory', command=self.load_images)
        self.fileMenu.add_command(label='Validate', command=self.validate)

        self.editMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='Edit', menu=self.editMenu)
        self.editMenu.add_command(label='Fill Down', command=self.fill_down, accelerator='ctrl-d')
        self.editMenu.add_command(label='Fill True', command=self.pt.enter_true, accelerator='ctrl-t')
        self.editMenu.add_command(label='Fill False', command=self.pt.enter_false, accelerator='ctr-f')

        self.editMenu.add_command(label='Add Column', command=self.add_column)
        self.config(menu=self.menubar)

    def open_spreadsheet(self):
        if self.dir and not self.keyCSV:
            self.csvdir = os.path.join(self.dir, 'csv')
            for f in os.listdir(self.csvdir):
                if f.endswith('.csv') and 'keywords' in f:
                    self.keyCSV = os.path.join(self.csvdir, f)

        if self.keyCSV == None:
            self.keyCSV = self.createKeywordsCSV()
        else:
            self.build_keywords_csv()

        self.title(self.keyCSV)
        self.pt.importCSV(self.keyCSV)

    def update_current_image(self, event):
        row = self.pt.getSelectedRow()
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

    def load_keywords(self):
        try:
            dataFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'ImageKeywords.csv')
            df = pd.read_csv(dataFile)
        except IOError:
            tkMessageBox.showwarning('Warning', 'Keywords list not found! (hp_tool/data/ImageKeywords.csv')
            return []
        return [x.strip() for x in df['keywords']]

    def update_valid_values(self):
        pass

    def createKeywordsCSV(self):
        keywordsName = os.path.join(self.dir, 'csv', datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + 'keywords.csv')
        if not os.path.exists(keywordsName):
            with open(keywordsName, 'wb') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(['New Filename', 'Keyword1', 'Keyword2', 'Keyword3'])
                for im in range(0, len(self.newImageNames)):
                    writer.writerow([os.path.basename(self.newImageNames[im])] + ['']*3)

        return keywordsName

    def build_keywords_csv(self):
        writtenImages = []
        with open(self.keyCSV) as csvFile:
            reader = csv.reader(csvFile)
            for row in reader:
                writtenImages.append(row[0])
            writtenImages.pop(0)
        with open(self.keyCSV, 'ab') as csvFile:
            writer = csv.writer(csvFile)
            for im in range(0, len(self.newImageNames)):
                if os.path.basename(self.newImageNames[im]) not in writtenImages:
                    writer.writerow([os.path.basename(self.newImageNames[im])])

    def validate(self):
        try:
            keysFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'ImageKeywords.csv')
            with open(keysFile) as keys:
                keywords = keys.readlines()
        except IOError:
            tkMessageBox.showwarning('Warning', 'Keywords reference not found!')
            return

        keywords = [x.strip() for x in keywords]
        errors = []
        for row in range(0, self.pt.rows):
            for col in range(2, self.pt.cols):
                val = str(self.pt.model.getValueAt(row, col))
                if val != 'nan' and val != '' and val not in keywords:
                    errors.append('Invalid keyword for ' + str(self.pt.model.getValueAt(row, 0)) + ' (Row ' + str(row+1) + ', Keyword ' + str(col-1) + ', Value: ' + val + ')')

        if errors:
            ErrorWindow(errors).show_errors()
        else:
            tkMessageBox.showinfo('Spreadsheet Validation', 'Nice work! All entries are valid.')

    def add_column(self):
        numCols = self.pt.cols
        new = np.empty(self.pt.rows)
        new[:] = np.NAN
        self.pt.model.df['Keyword ' + str(self.pt.cols - 1)] = pd.Series(new, index=self.pt.model.df.index)
        self.pt.redraw()


    def exportCSV(self, showErrors=True):
        self.pt.redraw()
        if showErrors:
            self.validate()
        self.pt.doExport(self.keyCSV)
        tmp = self.keyCSV + '-tmp.csv'
        with open(self.keyCSV, 'rb') as source:
            rdr = csv.reader(source)
            with open(tmp, 'wb') as result:
                wtr = csv.writer(result)
                for r in rdr:
                    wtr.writerow((r[1:]))
        os.remove(self.keyCSV)
        os.rename(tmp, self.keyCSV)
        self.saveState = True
        tkMessageBox.showinfo('Status', 'Saved!')

    def close(self):
        self.destroy()
