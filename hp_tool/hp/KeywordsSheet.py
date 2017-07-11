import json
from Tkinter import *
import os
import pandas as pd
import numpy as np
import tkMessageBox
import csv
import shutil
import datetime
from ErrorWindow import ErrorWindow
from HPSpreadsheet import HPSpreadsheet, CustomTable
from PIL import Image, ImageTk
import data_files
import hp_data

RVERSION = hp_data.RVERSION

class KeywordsSheet(HPSpreadsheet):
    """
    Class for managing keyword data entry. Simply overrides most of HPSpreadsheet, main difference being the lack of
    tabs. 
    """
    def __init__(self, settings, dir=None, keyCSV=None, master=None, oldImageNames=[], newImageNames=[]):
        self.keywords = self.load_keywords()
        self.settings = settings
        HPSpreadsheet.__init__(self, settings, dir=dir, master=master)
        self.oldImageNames = oldImageNames
        self.newImageNames = newImageNames
        self.dir = dir
        if self.dir:
            self.imageDir = os.path.join(self.dir, 'image')
        self.on_main_tab = True
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

        image = Image.open(data_files._REDX)
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
        self.fileMenu.add_command(label='Validate', command=self.validate)

        self.editMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='Edit', menu=self.editMenu)
        self.editMenu.add_command(label='Fill Down', command=self.pt.fill_selection, accelerator='ctrl-d')
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
            im = Image.open(data_files._REDX)
        if im.size[0] > maxSize or im.size[1] > maxSize:
            im.thumbnail((maxSize,maxSize), Image.ANTIALIAS)
        newimg=ImageTk.PhotoImage(im)
        self.l2.configure(image=newimg)
        self.l2.image = newimg
        self.update_valid_values()

    def load_keywords(self):
        try:
            df = pd.read_csv(data_files._IMAGEKEYWORDS)
        except IOError:
            tkMessageBox.showwarning('Warning', 'Keywords list not found!', parent=self)
            return []
        return [x.strip() for x in df['keywords']]

    def update_valid_values(self):
        pass

    def validate(self):
        """check with master list to ensure all keywords are valid"""
        try:
            with open(data_files._IMAGEKEYWORDS) as keys:
                keywords = keys.readlines()
        except IOError:
            tkMessageBox.showwarning('Warning', 'Keywords reference not found!', parent=self)
            return

        keywords = [x.strip() for x in keywords]
        errors = []
        for row in range(0, self.pt.rows):
            for col in range(1, self.pt.cols):
                val = str(self.pt.model.getValueAt(row, col))
                if val != 'nan' and val != '' and val not in keywords:
                    errors.append('Invalid keyword for ' + str(self.pt.model.getValueAt(row, 0)) + ' (Row ' + str(row+1) + ', Keyword' + str(col) + ', Value: ' + val + ')')

        if errors:
            ErrorWindow(self, errors)
        else:
            tkMessageBox.showinfo('Spreadsheet Validation', 'All keywords are valid.', parent=self)

    def add_column(self):
        numCols = self.pt.cols
        new = np.empty(self.pt.rows)
        new[:] = np.NAN
        self.pt.model.df['keyword' + str(numCols)] = pd.Series(new, index=self.pt.model.df.index)
        self.pt.redraw()


    def exportCSV(self, showErrors=True, quiet=False):
        self.pt.redraw()
        self.pt.doExport(self.keyCSV)
        tmp = self.keyCSV + '-tmp.csv'
        with open(self.keyCSV, 'rb') as source:
            rdr = csv.reader(source)
            with open(tmp, 'wb') as result:
                wtr = csv.writer(result)
                for r in rdr:
                    wtr.writerow((r[1:]))
        os.remove(self.keyCSV)
        shutil.move(tmp, self.keyCSV)
        self.save_to_rankone()
        self.saveState = True
        if not quiet and showErrors:
            tkMessageBox.showinfo('Status', 'Saved! The spreadsheet will now be validated.', parent=self)
        if showErrors:
            self.validate()

    def save_to_rankone(self):
        """parses and inserts the keywords into rankone csv"""
        global RVERSION
        rankone_file = self.keyCSV.replace('keywords', 'rankone')
        with open(self.keyCSV) as keywords:
            rdr = csv.reader(keywords)
            next(rdr)  # skip header row
            rankone_data = pd.read_csv(rankone_file, header=1)
            idx = 0
            for row in rdr:
                row_no_empty = filter(lambda a: a != '', row)  # remove empty strings
                rankone_data.loc[idx, 'HP-Keywords'] = '\t'.join(row_no_empty[1:])
                idx+=1
        with open(rankone_file, 'w') as ro:
            wtr = csv.writer(ro, lineterminator='\n', quoting=csv.QUOTE_ALL)
            wtr.writerow([RVERSION])
            rankone_data.to_csv(ro, index=False, quoting=csv.QUOTE_ALL)


    def close(self):
        self.destroy()
