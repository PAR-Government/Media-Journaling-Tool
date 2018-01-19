import ttk
from Tkinter import *
import tkFileDialog
import tkSimpleDialog
import tkMessageBox
import os
import sys
from PIL import Image
from bitstring import BitArray
import subprocess
import csv
from maskgen.exif import getexif

class QTManager(Frame):
    def __init__(self, master):
        self.master = master
        Frame.__init__(self, master)
        self.grid()
        self.load_body()

    def load_body(self):
        self.loadbutton = Button(self, text='Add from JPG... ', command=self.load_image, bg='green', width=15, font='arial 20 bold')
        self.loadbutton.grid(row=5, column=3, ipadx=5, ipady=5, padx=15, pady=1)

        self.deletebutton = Button(self, text='Delete Selected', command=self.delete_selected, bg='red', width=15, font='arial 20 bold')
        self.deletebutton.grid(row=10, column=3, ipadx=5, ipady=5, padx=5, pady=1)

        self.vertscrollbar = Scrollbar(self)
        self.vertscrollbar.grid(row=0, column=1, sticky='NS', rowspan=20)
        self.horscrollbar = Scrollbar(self, orient=HORIZONTAL)
        self.horscrollbar.grid(row=21, sticky='WE')

        self.filelist = Listbox(self, xscrollcommand=self.horscrollbar.set, yscrollcommand=self.vertscrollbar.set, selectmode=EXTENDED, width=50, height=40)
        self.filelist.grid(row=0, column=0, rowspan=20)
        for f in os.listdir(os.path.join('plugins', 'JpgFromCamera', 'QuantizationTables')):
            self.filelist.insert(END, f)
        self.filelist.bind('<Double-1>', self.open_file)

        self.vertscrollbar.config(command=self.filelist.yview)
        self.horscrollbar.config(command=self.filelist.xview)

    def load_image(self):
        imageFile = tkFileDialog.askopenfilename(filetypes=[('JPEG','*.jpg')])
        exifData = getexif(imageFile, args=['-f', '-args', '-CameraMake', '-CameraModel'], separator='=')

        self.make = exifData['-CameraMake']
        self.model = exifData['-CameraModel']

        if self.make == '-' or self.model == '-':
            cancel = self.prompt_for_info()
            if cancel is True:
                return

        im = Image.open(imageFile)
        (width, height) = im.size
        self.size = '['+str(width)+'x'+str(height)+']'

        tables = self.parse_tables(imageFile)
        finalTables = self.sort_tables(tables)

        thumbTable = []
        prevTable = []
        if len(finalTables) == 6:
            thumbTable = finalTables[0:2]
            prevTable = finalTables[2:4]
            finalTable = finalTables[4:6]
        elif len(finalTables) > 2 and len(finalTables) < 6:
            thumbTable = finalTables[0:2]
            finalTable = finalTables[-2:]
        elif len(finalTables) < 2:
            finalTable = [finalTables, finalTables]
        else:
            finalTable = finalTables

        qtfilename = os.path.join('plugins', 'JpgFromCamera', 'QuantizationTables', self.make + '-' + self.model + '-' + self.size + '-QT.txt')
        duplicateCount = None
        if os.path.isfile(qtfilename):
            duplicateCount = '1'
            qtfilename = qtfilename.replace('-QT.txt', '('+duplicateCount+')-QT.txt')
            while os.path.isfile(qtfilename):
                prevCount = duplicateCount
                duplicateCount = str(int(duplicateCount)+1)
                qtfilename = qtfilename.replace('('+prevCount+')-QT.txt', '('+duplicateCount+')-QT.txt')

        with open(qtfilename, 'w') as qtf:
            for table in finalTable:
                count = 1
                for value in table:
                    qtf.write(str(value)+'\t')
                    if count % 8 == 0:
                        qtf.write('\n')
                    count += 1
        self.filelist.insert(-1, os.path.basename(qtfilename))

        if prevTable:
            prfilename = os.path.join('plugins', 'JpgFromCamera', 'QuantizationTables',
                                      self.make + '-' + self.model + '-' + self.size + '-preview.txt')
            if duplicateCount is not None:
                prfilename = prfilename.replace('-preview.txt', '(' + duplicateCount + ')-preview.txt')
            with open(prfilename, 'w') as qtf:
                for table in prevTable:
                    count = 1
                    for value in table:
                        qtf.write(str(value) + '\t')
                        if count % 8 == 0:
                            qtf.write('\n')
                        count += 1
            self.filelist.insert(-1, os.path.basename(prfilename))
        else:
            prfilename = ''

        if thumbTable:
            thfilename = os.path.join('plugins', 'JpgFromCamera', 'QuantizationTables', self.make + '-' + self.model + '-' + self.size + '-thumbnail.txt')
            if duplicateCount is not None:
                thfilename = thfilename.replace('-thumbnail.txt', '('+duplicateCount+')-thumbnail.txt')
            with open(thfilename, 'w') as qtf:
                for table in thumbTable:
                    count = 1
                    for value in table:
                        qtf.write(str(value) + '\t')
                        if count % 8 == 0:
                            qtf.write('\n')
                        count += 1
            self.filelist.insert(-1, os.path.basename(thfilename))
        else:
            thfilename = ''

        mfilename = os.path.join('plugins', 'JpgFromCamera', 'QuantizationTables',
                                self.make + '-' + self.model + '-' + self.size + '-metadata.csv')
        if duplicateCount is not None:
            mfilename = mfilename.replace('-metadata.csv', '('+duplicateCount+')-metadata.csv')
        mfilename = self.save_metadata(imageFile, mfilename)
        if mfilename is not None:
            self.filelist.insert(-1, os.path.basename(mfilename))
        else:
            mfilename = 'Metadata file was not written.'

        prfilename = prfilename + '\n' if prfilename != '' else prfilename
        thfilename = thfilename + '\n' if thfilename!='' else thfilename

        tkMessageBox.showinfo('New Tables', 'The following files were added:\n' + os.path.basename(qtfilename) + '\n' +
                              os.path.basename(prfilename) + os.path.basename(thfilename) + os.path.basename(mfilename))

    def prompt_for_info(self):
        prompter = InfoPrompt(self)
        return prompter.cancelled

    def save_metadata(self, imageFile, filename):
        m = MetadataHandler(self, input=imageFile, output=filename)
        m.wait()
        if not m.file_written:
            filename = None
        return filename

    def delete_selected(self):
        toDelete = [(x, self.filelist.get(x)) for x in self.filelist.curselection()]
        toDelete.reverse()
        for f in toDelete:
            os.remove(os.path.join('plugins', 'JpgFromCamera', 'QuantizationTables', f[1]))
            self.filelist.delete(f[0])

    def open_file(self, event):
        """
        code from maskgen.tool_set.py
        """
        import os
        import sys
        fileName = self.filelist.get(self.filelist.curselection())
        path = os.path.join('plugins', 'JpgFromCamera', 'QuantizationTables', fileName)
        if sys.platform.startswith('linux'):
            os.system('xdg-open "' + path + '"')
        elif sys.platform.startswith('win'):
            os.startfile(path)
        else:
            os.system('open "' + path + '"')

    def parse_tables(self, imageFile):
        """
        Grab all quantization tables from jpg header
        :param imageFile: string containing jpg image filename
        :return: list of lists of unsorted quantization tables
        """

        # open the image and scan for q table marker "FF DB"
        s = open(imageFile, 'rb')
        b = BitArray(s)
        ffdb = b.findall('0xffdb', bytealigned=True)

        # grab the tables, based on format
        tables = []
        for start in ffdb:
            subset = b[start + 5 * 8:start + 134 * 8]
            check = subset.find('0xff', bytealigned=True)
            if check:
                subsubset = subset[0:check[0]]
                tables.append(subsubset)
            else:
                tables.append(subset[0:64 * 8])
                tables.append(subset[65 * 8:])

        # concatenate the tables, and convert them from bitarray to list
        finalTable = []
        for table in tables:
            tempTable = []

            bi = table.bin
            for i in xrange(0, len(bi), 8):
                byte = bi[i:i + 8]
                val = int(byte, 2)
                tempTable.append(val)
            finalTable.append(tempTable)
        s.close()
        return finalTable

    def sort_tables(self, tablesList):
        """
        Un-zigzags a list of quantization tables
        :param tablesList: list of lists of unsorted quantization tables
        :return: list of lists of sorted quantization tables
        """

        # hardcode order, since it will always be length 64
        indices = [0, 1, 5, 6, 14, 15, 27, 28, 2, 4, 7, 13, 16, 26, 29, 42, 3, 8, 12, 17, 25, 30, 41, 43,
                   9, 11, 18, 24, 31, 40, 44, 53, 10, 19, 23, 32, 39, 45, 52, 54, 20, 22, 33, 38, 46,
                   51, 55, 60, 21, 34, 37, 47, 50, 56, 59, 61, 35, 36, 48, 49, 57, 58, 62, 63]

        newTables = []
        for listIdx in xrange(len(tablesList)):
            if len(tablesList[listIdx]) == 64:
                tempTable = []
                for elmIdx in xrange(0, 64):
                    tempTable.append(tablesList[listIdx][indices[elmIdx]])
                newTables.append(tempTable)
        return newTables


class InfoPrompt(tkSimpleDialog.Dialog):
    def __init__(self, master):
        self.master = master
        self.cancelled = True
        tkSimpleDialog.Dialog.__init__(self, master)

    def body(self, master):
        Label(master, text="The following will be used only for naming files, and will not be inserted into image metadata.").grid(row=0, columnspan=2)
        Label(master, text="Camera Make:").grid(row=1)
        Label(master, text="Camera Model:").grid(row=2)

        self.e1 = Entry(master)
        self.e2 = Entry(master)

        self.e1.grid(row=1, column=1)
        self.e2.grid(row=2, column=1)

        self.e1.insert(END, self.master.make)
        self.e2.insert(END, self.master.model)

    def apply(self):
        self.master.make = self.e1.get()
        self.master.model = self.e2.get()
        self.cancelled = False


class MetadataHandler(Toplevel):
    def __init__(self, master, input, output):
        self.master = master
        self.inputFilename = input
        self.outputFilename = output
        self.extract_metadata()
        self.file_written = False

        Toplevel.__init__(self, master)
        self.body()

    def extract_metadata(self):
        fieldsToNotCopy = ['-x','ExifToolVersion', '-x','FileName', '-x','Directory',         '-x','FileSize', '-x','FileCreateDate',
                           '-x','FilePermissions', '-x','FileType', '-x','FileTypeExtension', '-x','MIMEType', '-x','XMPToolkit',
                           '-x','FileModifyDate',  '-x','FileAccessDate']

        self.newExifData = getexif(self.inputFilename, args=['-all'] + fieldsToNotCopy + ['-args', '-a', '-e', '-G1'], separator='=')

    def body(self):
        dataframe = ScrollableFrame(self)
        dataframe.pack(side='top', fill='both', expand=True)
        self.labels = []
        self.entries = []
        self.radVars = []

        descr = Label(dataframe.frame, text='Select metadata source for future use. \nDatabase: metadata tags will be set based '
                                            'on the values entered below.\nSource: metadata tags will be set based on source node\'s image metadata.\n'
                                            'Computed: metadata tag will attempt to be calculated for the new image.').grid(columnspan=8)

        headers = ['Database', 'Source', 'Computed', 'Tag Name', 'Tag Value']
        col = 0
        for header in headers:
            lab = Label(dataframe.frame, text=header)
            if header == 'Tag Name':
                lab.grid(row=1, column=col, columnspan=2)
                col+=1
            else:
                lab.grid(row=1, column=col)
            col+=1

        row = 2
        defaults = {}
        with open(os.path.join('plugins', 'JpgFromCamera', 'defaults.csv')) as csvFile:
            reader = csv.reader(csvFile)
            for line in reader:
                defaults[line[0].strip()] = {'default':line[1].strip().lower(), 'state':line[2].strip().lower()}

        for key, val in iter(sorted(self.newExifData.iteritems())):
            if key.startswith('-File'):
                continue
            radVar = StringVar()
            radVar.set('database')
            but1 = Radiobutton(dataframe.frame, variable=radVar, value='database')
            but2 = Radiobutton(dataframe.frame, variable=radVar, value='source')
            but3 = Radiobutton(dataframe.frame, variable=radVar, value='compute')
            but1.grid(row=row, column=0)
            but2.grid(row=row, column=1)
            but3.grid(row=row, column=2)
            but1.bind("<Button-1>", self.enable_entry)
            but2.bind("<Button-1>", self.enable_entry)
            but3.bind("<Button-1>", self.ask_param)


            l = Label(dataframe.frame, text=key+':')
            e = Entry(dataframe.frame)
            but1.correspondingEntry = e
            but2.correspondingEntry = e
            but3.correspondingEntry = e
            but1.correspondingVar = radVar
            but2.correspondingVar = radVar
            but3.correspondingVar = radVar

            l.grid(row=row, column=3, columnspan=2)
            e.grid(row=row, column=5, columnspan=3, sticky=W+E)
            e.insert(END, val)
            if key in defaults.keys():
                radDefault = defaults[key]['default']
                state = defaults[key]['state']
                radVar.set(radDefault)
                but1.config(state=state)
                but2.config(state=state)
                but3.config(state=state)
                e.config(state=state)

            self.labels.append(l)
            self.entries.append(e)
            self.radVars.append(radVar)

            row+=1

        okbutton = Button(dataframe.frame, text='OK', command=self.apply, bg='green', width=5)
        okbutton.grid(row=row, column=3, columnspan=2,  ipadx=5, ipady=5, padx=5, pady=5)

    def apply(self):
        # get tags from entry fields and write file
        with open(self.outputFilename, 'w') as csvFile:
            writer = csv.writer(csvFile)
            for idx in xrange(0, len(self.labels)):
                try:
                    writer.writerow([self.radVars[idx].get(), self.labels[idx].cget('text')[:-1], self.entries[idx].get()])
                except UnicodeEncodeError:
                    bad = self.entries[idx].get()
                    good = bad.replace(u'\xa9', '(c)')
                    writer.writerow([self.radVars[idx].get(), self.labels[idx].cget('text')[:-1], good])
        self.file_written = True
        self.destroy()

    def wait(self):
        self.wait_window()

    def ask_param(self, event):
        state = event.widget.cget('state')
        if state == 'normal':
            d = SelectorDialog(self)
            if d.result is not None and d.cancelled is False:
                event.widget.correspondingVar.set('compute')
                entr = event.widget.correspondingEntry
                entr.delete(0, END)
                entr.insert(0, d.result)
                entr.config(state='disabled')
            event.widget.config(state='normal')

    def enable_entry(self, event):
        if event.widget.cget('state') == 'normal':
            event.widget.correspondingEntry.config(state='normal')

class SelectorDialog(tkSimpleDialog.Dialog):
    def __init__(self, master):
        self.master=master
        tkSimpleDialog.Dialog.__init__(self, master)

    def body(self, master):
        options = ['Width', 'Height', 'Size (pixels)','Size (WidthxHeight)']
        self.box = ttk.Combobox(self, values=options, state='readonly')
        self.box.pack()
        self.box.set(options[0])

    def ok(self, event=None):
        self.cancelled = False
        res = self.box.get()
        if res == 'Width':
            self.result = '#CalcWidth'
        elif res == 'Height':
            self.result = '#CalcHeight'
        elif res == 'Size (pixels)':
            self.result = '#CalcSizePixels'
        elif res == 'Size (WidthxHeight)':
            self.result = '#CalcSizeWxH'
        self.result = self.box.get()
        self.destroy()

    def cancel(self, event=None):
        self.cancelled = True
        self.destroy()

class ScrollableFrame(Frame):
    # scrollable frame implementation from http://stackoverflow.com/questions/3085696/adding-a-scrollbar-to-a-group-of-widgets-in-tkinter
    def __init__(self, root):
        Frame.__init__(self, root)
        self.canvas = Canvas(root, borderwidth=0, width=600)
        self.frame = Frame(self.canvas)
        self.vsb = Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.hsb = Scrollbar(root, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.vsb.pack(side="right", fill="y")
        self.hsb.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4,4), window=self.frame, anchor="nw",
                                  tags="self.frame")
        self.frame.bind("<Configure>", self.onFrameConfigure)
        self.canvas.bind_all("<MouseWheel>", self.onMouseWheel)

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def onMouseWheel(self, event):
        self.canvas.yview_scroll(-1*(event.delta/120), "units")


def main():
    root = Tk()
    root.wm_title('QT Manager')
    qt = QTManager(root)
    qt.mainloop()

if __name__ == '__main__':
    main()
