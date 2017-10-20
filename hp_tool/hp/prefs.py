import webbrowser
from Tkinter import *
import ttk
import os
import datetime
import hp_data
import tkMessageBox
import json
import data_files

class SettingsManager():
    """
    Handles reading/writing of user settings.
    """
    def __init__(self, settingsFile=None):
        if settingsFile is None:
            self.settingsFile = os.path.join(os.path.expanduser('~'), '.hpsettings')
        else:
            self.settingsFile = settingsFile
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.settingsFile) as j:
                self.settings = json.load(j)
        except IOError:
            self.settings = {}
            self.settings['metadata'] = {}

    def get(self, key, notFound=None):
        # call with notFound param to change what value is returned if setting is not valid
        try:
            return self.settings[key]
        except KeyError:
            return notFound

    def get_m(self, key, notFound=None):
        """get metadata item"""
        try:
            return self.settings['metadata'][key]
        except KeyError:
            return notFound

    def set(self, setting, val):
        self.settings[setting] = val
        with open(self.settingsFile, 'w') as j:
            json.dump(self.settings, j, indent=4)

    def set_m(self, setting, val):
        """set metadata item"""
        self.settings['metadata'][setting] = val
        with open(self.settingsFile, 'w') as j:
            json.dump(self.settings, j, indent=4)


class SettingsWindow(Toplevel):
    """
    Defines the user settings window.
    """
    def __init__(self, settings, master=None):
        Toplevel.__init__(self, master=master)
        self.master=master
        self.settings = settings
        self.title('Setings')
        self.trello_key = data_files._TRELLO['app_key']
        self.set_text_vars()
        self.prefsFrame = Frame(self, width=300, height=300)
        self.prefsFrame.pack(side=TOP)
        self.buttonFrame = Frame(self, width=300, height=300)
        self.buttonFrame.pack(side=BOTTOM)
        self.metaFrame = Frame(self, width=300, height=300)
        self.metaFrame.pack(side=BOTTOM)

        self.create_widgets()
        self.set_defaults()
        self.orgVar.trace('r', self.update_org)
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

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
        self.usrVar.trace('w', self.limit_length)
        self.seqVar.trace('w', self.update_preview)

        self.s3Var = StringVar()
        self.s3VarPRNU = StringVar()
        self.urlVar = StringVar()
        self.urlVar.set('https://medifor.rankone.io')
        self.tokenVar = StringVar()
        self.trelloVar = StringVar()

        self.imageVar = StringVar()
        self.videoVar = StringVar()
        self.audioVar = StringVar()

        self.copyrightVar = StringVar()
        self.bylineVar = StringVar()
        self.creditVar = StringVar()
        self.usageVar = StringVar()

    def set_defaults(self):
        self.usrVar.set(self.settings.get('username', notFound=''))
        try:
            self.orgVar.set(self.settings.get('fullorgname', notFound=''))
        except KeyError:
            self.orgVar.set(self.settings.get('organization'))

        if self.settings.get('seq'):
            self.seqVar.set(self.settings.get('seq'))
        else:
            self.settings.set('seq', '00000')

        defaults = {'aws':self.s3Var, 'aws-prnu':self.s3VarPRNU, 'imagetypes':self.imageVar, 'videotypes':self.videoVar,
                    'audiotypes':self.audioVar,'apiurl':self.urlVar, 'apitoken':self.tokenVar, 'trello':self.trelloVar}
        for s in defaults:
            if self.settings.get(s):
                defaults[s].set(self.settings.get(s))

        metadata = {'copyrightnotice':self.copyrightVar, 'by-line':self.bylineVar, 'credit':self.creditVar}
        for m in metadata:
            if self.settings.get_m(m):
                metadata[m].set(self.settings.get_m(m))
        self.update_metadata()

        self.usageVar.set('CC0 1.0 Universal. https://creativecommons.org/publicdomain/zero/1.0/')

    def create_widgets(self):
        r = 0
        Label(self.prefsFrame, text='* indicates a required field.')
        self.usrLabel = Label(self.prefsFrame, text='Initials*: ')
        self.usrLabel.grid(row=r, column=0)
        self.usrEntry = Entry(self.prefsFrame, textvar=self.usrVar, width=5)
        self.usrEntry.grid(row=r, column=1)
        self.orgLabel = Label(self.prefsFrame, text='Organization*: ')
        self.orgLabel.grid(row=r, column=2)
        self.boxItems = [key + ' (' + hp_data.orgs[key] + ')' for key in hp_data.orgs]

        self.orgBox = ttk.Combobox(self.prefsFrame, values=self.boxItems, textvariable=self.orgVar, state='readonly')
        self.orgBox.grid(row=0, column=3, columnspan=4)

        r+=3
        self.descrLabel1 = Label(self.prefsFrame, textvar=self.prevVar)
        self.descrLabel1.grid(row=r, column=0, columnspan=8)

        r+=1
        self.s3Label = Label(self.prefsFrame, text='S3 bucket/path (HP Data): ')
        self.s3Label.grid(row=r, column=0, columnspan=4)

        self.s3Box = Entry(self.prefsFrame, textvar=self.s3Var)
        self.s3Box.grid(row=r, column=4)

        r+=1
        self.s3PRNULabel = Label(self.prefsFrame, text='S3 bucket/path (PRNU Data): ')
        self.s3PRNULabel.grid(row=r, column=0, columnspan=4)

        self.s3PRNUBox = Entry(self.prefsFrame, textvar=self.s3VarPRNU)
        self.s3PRNUBox.grid(row=r, column=4)

        r+=1
        self.urlLabel = Label(self.prefsFrame, text='Browser API URL: ')
        self.urlLabel.grid(row=r, column=0, columnspan=4)

        self.urlBox = Entry(self.prefsFrame, textvar=self.urlVar, state=DISABLED)
        self.urlBox.grid(row=r, column=4)

        r+=1
        medi_link = 'https://medifor.rankone.io/api/login'
        self.browserButton = Button(self.prefsFrame, text='Medifor Browser Token: ', command=lambda:self.open_website(medi_link))
        self.browserButton.grid(row=r, column=0, columnspan=4)

        self.browserBox = Entry(self.prefsFrame, textvar=self.tokenVar)
        self.browserBox.grid(row=r, column=4)

        r+=1
        trello_link = 'https://trello.com/1/authorize?key=' + self.trello_key + '&scope=read%2Cwrite&name=HP_GUI&expiration=never&response_type=token'
        self.trelloButton = Button(self.prefsFrame, text='Trello Token: ', command=lambda:self.open_website(trello_link))
        self.trelloButton.grid(row=r, column=0, columnspan=4)

        self.trelloBox = Entry(self.prefsFrame, textvar=self.trelloVar)
        self.trelloBox.grid(row=r, column=4)

        types = {'Image':self.imageVar, 'Video':self.videoVar, 'Audio':self.audioVar}
        self.extensions = {}
        for t in types.keys():
            r+=1
            but = Button(self.prefsFrame, text='Additional ' + t + ' Filetypes: ', command=self.show_default_types)
            but.grid(row=r, column=0, columnspan=4)
            self.extensions[t] = Entry(self.prefsFrame, textvar=types[t])
            self.extensions[t].grid(row=r, column=4)

        r+=1
        self.metalabel1 = Label(self.metaFrame, text='Metadata tags:\n(to be applied to copies only. Original images are unaffected.)')
        self.metalabel1.grid(row=r, column=0, columnspan=8)

        r+=1
        self.copyrightLabel = Label(self.metaFrame, text='CopyrightNotice: ')
        self.copyrightLabel.grid(row=r)
        self.copyrightEntry = Entry(self.metaFrame, textvar=self.copyrightVar, state='readonly')
        self.copyrightEntry.grid(row=r, column=1)

        r+=1
        self.bylineLabel = Label(self.metaFrame, text='By-Line: ')
        self.bylineLabel.grid(row=r)
        self.bylineEntry = Entry(self.metaFrame, textvar=self.bylineVar, state='readonly')
        self.bylineEntry.grid(row=r, column=1)

        r+=1
        self.creditLabel = Label(self.metaFrame, text='Credit: ')
        self.creditLabel.grid(row=r)
        self.creditEntry = Entry(self.metaFrame, textvar=self.creditVar, state='readonly')
        self.creditEntry.grid(row=r, column=1)

        r+=1
        self.usageLabel = Label(self.metaFrame, text='UsageTerms: ')
        self.usageLabel.grid(row=r)
        self.usageEntry = Entry(self.metaFrame, textvar=self.usageVar, state='readonly')
        self.usageEntry.grid(row=r, column=1)

        self.applyButton = Button(self.buttonFrame, text='Save & Close', command=self.save_prefs)
        self.applyButton.grid(padx=5)
        self.cancelButton = Button(self.buttonFrame, text='Cancel', command=self.destroy)
        self.cancelButton.grid(row=0, column=1, padx=5)

    def open_website(self, link):
        webbrowser.open(link)

    def show_default_types(self):
        imExts = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.nef', '.crw', '.cr2', '.dng', '.arw', '.srf', '.raf']
        vidExts = ['.avi', '.mov', '.mp4', '.mpg', '.mts', '.asf', '.mxf']
        audExts = ['.wav', '.mp3', '.flac', '.webm', '.aac', '.amr', '.3ga']
        tkMessageBox.showinfo('File Types', message='File extensions accepted by default: \n' +
                                                    'Image: ' + ', '.join(imExts) + '\n' +
                                                    'Video: ' + ', '.join(vidExts) + '\n' +
                                                    'Audio: ' + ', '.join(audExts))

    def limit_length(self, *args):
        s = self.usrVar.get()
        if len(s) > 3:
            self.usrVar.set(s[0:3])

    def update_preview(self, *args):
        try:
            org = self.orgVar.get()[-2]
        except IndexError:
            org = self.orgVar.get()
        self.prevVar.set('*New filenames will appear as:\n' + datetime.datetime.now().strftime('%Y%m%d')[
                                                              2:] + '-' + org + self.usrVar.get() + '-' + self.seqVar.get())
    def update_org(self, *args):
        self.settings.set('fullorgname', self.orgVar.get())
        try:
            self.settings.set('organization', self.orgVar.get()[-2])
        except IndexError:
            self.settings.set('organization', self.orgVar.get())

    def update_metadata(self, *args):
        initials = self.usrVar.get()
        org = self.orgVar.get()

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
        year = datetime.datetime.today().strftime('%Y')
        self.copyrightVar.set('(c) ' + year + ' ' + org + ' - Under contract of MediFor')
        self.bylineVar.set(initials)
        self.creditVar.set(org)

    def save_prefs(self):
        """
        Write out settings
        """
        if self.usrEntry.get():
            self.settings.set('username', self.usrVar.get().upper())
        else:
            tkMessageBox.showerror(title='Error', message='Initials must be specified.')
            return

        update = self.orgVar.get()
        self.settings.set('seq', self.seqVar.get())
        self.settings.set('aws', self.s3Var.get())
        self.settings.set('aws-prnu', self.s3VarPRNU.get())
        self.settings.set('apiurl', self.urlVar.get())
        self.settings.set('apitoken', self.tokenVar.get())
        self.settings.set('trello', self.trelloVar.get())
        self.settings.set('imagetypes', self.imageVar.get())
        self.settings.set('videotypes', self.videoVar.get())
        self.settings.set('audiotypes', self.audioVar.get())
        self.settings.set('trello_login_url', 'https://trello.com/1/authorize?key='+self.trello_key+'&scope=read%2Cwrite&name=HP_GUI&expiration=never&response_type=token')
        self.settings.set('browser_login_url', 'https://medifor.rankone.io/api/login')

        self.settings.set_m('copyrightnotice', self.copyrightVar.get())
        self.settings.set_m('by-line', self.bylineVar.get())
        self.settings.set_m('credit', self.creditVar.get())
        self.settings.set_m('usageterms', self.usageVar.get())
        self.settings.set_m('copyright', '')
        self.settings.set_m('artist', '')

        self.destroy()
