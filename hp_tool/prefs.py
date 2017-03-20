from Tkinter import *
import ttk
import os
import datetime
import hp_data
import change_all_metadata

class Preferences(Toplevel):
    def __init__(self, master=None):
        Toplevel.__init__(self, master=master)
        self.master=master
        self.title('Preferences')
        self.set_text_vars()
        self.prefsFrame = Frame(self, width=300, height=300)
        self.prefsFrame.pack(side=TOP)
        self.buttonFrame = Frame(self, width=300, height=300)
        self.buttonFrame.pack(side=BOTTOM)
        self.metaFrame = Frame(self, width=300, height=300)
        self.metaFrame.pack(side=BOTTOM)
        self.prefsFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'preferences.txt')
        self.metaFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'metadata.txt')
        p = hp_data.parse_prefs(self.prefsFile)
        if p:
            self.prefs = p
        else:
            self.prefs = {}

        m = change_all_metadata.parse_file(self.metaFile)
        if m:
            self.metadata = m
        else:
            self.metadata = {}

        self.create_widgets()
        self.set_defaults()
        self.orgVar.trace('r', self.update_org)

    def set_text_vars(self):
        self.prevVar = StringVar()
        self.usrVar = StringVar()
        self.usrVar.set('XX')
        self.seqVar = StringVar()
        self.seqVar.set('00000')
        self.orgVar = StringVar()
        self.orgVar.set('RIT (R)')
        self.orgVar.trace('w', self.update_preview)
        self.orgVar.trace('w', self.update_metadata)
        self.orgVar.trace('w', self.update_org)
        self.usrVar.trace('w', self.update_preview)
        self.usrVar.trace('w', self.update_metadata)
        self.seqVar.trace('w', self.update_preview)

        self.s3var = StringVar()

        self.copyrightVar = StringVar()
        self.bylineVar = StringVar()
        self.creditVar = StringVar()
        self.usageVar = StringVar()

    def set_defaults(self):

        if self.prefs:
            if self.prefs.has_key('prefsFile'):
                self.prefs = hp_data.parse_prefs(self.prefs['prefsFile'])
            self.usrVar.set(self.prefs['username'])
            try:
                self.orgVar.set(self.prefs['fullorgname'])
            except KeyError:
                self.orgVar.set(self.prefs['organization'])

            if self.prefs.has_key('seq'):
                self.seqVar.set(self.prefs['seq'])
            else:
                self.prefs['seq'] = '00000'

            if self.prefs.has_key('aws'):
                self.s3var.set(self.prefs['aws'])

        if self.metadata:
            self.copyrightVar.set(self.metadata['copyrightnotice'])
            self.bylineVar.set(self.metadata['by-line'])
            self.creditVar.set(self.metadata['credit'])

        self.usageVar.set('CC0 1.0 Universal. https://creativecommons.org/publicdomain/zero/1.0/')

    def create_widgets(self):
        r = 0
        self.usrLabel = Label(self.prefsFrame, text='Initials: ')
        self.usrLabel.grid(row=r, column=0)
        self.usrEntry = Entry(self.prefsFrame, textvar=self.usrVar, width=5)
        self.usrEntry.grid(row=r, column=1)
        self.orgLabel = Label(self.prefsFrame, text='Organization: ')
        self.orgLabel.grid(row=r, column=2)
        self.boxItems = [key + ' (' + hp_data.orgs[key] + ')' for key in hp_data.orgs]

        self.orgBox = ttk.Combobox(self.prefsFrame, values=self.boxItems, textvariable=self.orgVar, state='readonly')
        self.orgBox.grid(row=0, column=3, columnspan=4)

        r+=3
        self.descrLabel1 = Label(self.prefsFrame, textvar=self.prevVar)
        self.descrLabel1.grid(row=r, column=0, columnspan=8)

        r+=1
        self.s3Label = Label(self.prefsFrame, text='S3 bucket/path: ')
        self.s3Label.grid(row=r, column=0, columnspan=4)

        self.s3Box = Entry(self.prefsFrame, textvar=self.s3var)
        self.s3Box.grid(row=r, column=4)


        r+=1
        self.metalabel1 = Label(self.metaFrame, text='Metadata tags:\n(to be applied to copies only. Original images are unaffected.)')
        self.metalabel1.grid(row=r, column=0, columnspan=8)

        r+=1
        self.copyrightLabel = Label(self.metaFrame, text='CopyrightNotice: ')
        self.copyrightLabel.grid(row=r)
        self.copyrightEntry = Entry(self.metaFrame, textvar=self.copyrightVar)
        self.copyrightEntry.grid(row=r, column=1)

        r+=1
        self.bylineLabel = Label(self.metaFrame, text='By-Line: ')
        self.bylineLabel.grid(row=r)
        self.bylineEntry = Entry(self.metaFrame, textvar=self.bylineVar)
        self.bylineEntry.grid(row=r, column=1)

        r+=1
        self.creditLabel = Label(self.metaFrame, text='Credit: ')
        self.creditLabel.grid(row=r)
        self.creditEntry = Entry(self.metaFrame, textvar=self.creditVar)
        self.creditEntry.grid(row=r, column=1)

        r+=1
        self.usageLabel = Label(self.metaFrame, text='UsageTerms: ')
        self.usageLabel.grid(row=r)
        self.usageEntry = Entry(self.metaFrame, textvar=self.usageVar)
        self.usageEntry.grid(row=r, column=1)

        self.applyButton = Button(self.buttonFrame, text='Save & Close', command=self.save_prefs)
        self.applyButton.grid(padx=5)
        self.cancelButton = Button(self.buttonFrame, text='Cancel', command=self.destroy)
        self.cancelButton.grid(row=0, column=1, padx=5)

    def update_preview(self, *args):
        try:
            org = self.orgVar.get()[-2]
        except IndexError:
            org = self.orgVar.get()
        self.prevVar.set('*New filenames will appear as:\n' + datetime.datetime.now().strftime('%Y%m%d')[
                                                              2:] + '-' + org + self.usrVar.get() + '-' + self.seqVar.get())
    def update_org(self, *args):
        self.prefs['fullorgname'] = self.orgVar.get()
        try:
            self.prefs['organization'] = self.orgVar.get()[-2]
        except IndexError:
            self.prefs['organization'] = self.orgVar.get()

    def update_metadata(self, *args):
        initials = self.usrVar.get()
        org = self.orgVar.get()
        self.copyrightEntry.delete(0, END)
        self.bylineEntry.delete(0, END)
        self.creditEntry.delete(0, END)

        if org == 'U of M (M)':
            org = 'University of Michigan'
        elif org == 'PAR (P)':
            org = 'PAR Government Systems'
        elif org == 'RIT (R)':
            org = 'Rochester Institute of Technology'
        elif org == 'Drexel (D)':
            org = 'Drexel University'
        elif org == 'CU Denver (C)':
            org = 'University of Colorado, Denver'

        self.copyrightEntry.insert(0, '(c) 2016 ' + org + ' - Under contract of MediFor')
        self.bylineEntry.insert(0, initials)
        self.creditEntry.insert(0, org)

    def save_prefs(self):
        if self.usrEntry.get():
            self.prefs['username'] = self.usrVar.get()

        update = self.orgVar.get()
        self.prefs['seq'] = self.seqVar.get()

        self.prefs['aws'] = self.s3var.get()

        with open(self.prefsFile, 'w') as f:
            for key in self.prefs:
                f.write(key + '=' + self.prefs[key] + '\n')

        self.metadata['copyrightnotice'] = self.copyrightVar.get()
        self.metadata['by-line'] = self.bylineVar.get()
        self.metadata['credit'] = self.creditVar.get()
        self.metadata['usageterms'] = self.usageVar.get()
        self.metadata['copyright'] = ''
        self.metadata['artist'] = ''

        with open(self.metaFile, 'w') as f:
            for key in self.metadata:
                f.write(key + '=' + self.metadata[key] + '\n')
        self.destroy()


