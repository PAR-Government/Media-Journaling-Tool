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
        self.open_spreadsheet()


    def create_widgets(self):
        self.topFrame = Frame(self)
        self.topFrame.grid(row=0, column=1)
        self.bottomFrame = Frame(self)
        self.bottomFrame.grid(row=1, column=1)
        self.leftFrame = Frame(self)
        self.leftFrame.grid(row=0, column=0, rowspan=2)
        self.pt = CustomTable(self.leftFrame)
        self.pt.show()
        self.currentImageNameVar = StringVar()
        self.currentImageNameVar.set('Current Image: ')
        l = Label(self.topFrame, textvariable=self.currentImageNameVar)
        l.grid()

        image = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'RedX.png'))
        self.photo = ImageTk.PhotoImage(image)
        self.l2 = Label(self.bottomFrame, width=250, height=250, image=self.photo)
        self.l2.image = self.photo  # keep a reference!
        self.l2.grid()

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

        self.title(self.keyCSV)
        self.pt.importCSV(self.keyCSV)


    def createKeywordsCSV(self):
        keywordsName = os.path.join(self.dir, 'csv', datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + 'keywords.csv')
        if not os.path.exists(keywordsName):
            with open(keywordsName, 'wb') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(['New Filename', 'Keyword1', 'Keyword2', 'Keyword3'])
                for im in range(0, len(self.newImageNames)):
                    writer.writerow([os.path.basename(self.newImageNames[im])] + ['']*3)

        return keywordsName

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

