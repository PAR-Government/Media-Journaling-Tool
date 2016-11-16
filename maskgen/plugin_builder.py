import tkSimpleDialog
from tkinter import *

class PluginBuilder(tkSimpleDialog.Dialog):
    def __init__(self, master):
        tkSimpleDialog.Dialog.__init__(self, master)
        self.master=master

    def body(self, master):
        nameLabel = Label(master, text='Plugin Name: ')
        nameLabel.grid(row=0, column=0)
        self.nameEntry = Entry(master, width=40)
        self.nameEntry.grid(row=0, column=1, sticky='EW')
        descriptionLabel = Label(master, text='Description: ')
        descriptionLabel.grid(row=1, column=0)
        self.descriptionEntry = Text(master, width=40, height=3)
        self.descriptionEntry.grid(row=1, column=1, sticky='EW')
        softwareNameLabel = Label(master, text='Software Name: ')
        softwareNameLabel.grid(row=2, column=0)
        self.softwareNameEntry = Entry(master, width=40)
        self.softwareNameEntry.grid(row=2, column=1, sticky='EW')
        softwareVersionLabel = Label(master, text='Software Version: ')
        softwareVersionLabel.grid(row=3, column=0)
        self.softwareVersionEntry = Entry(master, width=40)
        self.softwareVersionEntry.grid(row=3, column=1, sticky='EW')
        commandLabel1 = Label(master, text='Command (exactly as it would be typed in command line):')
        commandLabel1.grid(row=4, column=0, columnspan=8)
        self.commandEntry = Entry(master, width=40)
        self.commandEntry.grid(row=5, column=0, columnspan=8, sticky='EW')
        commandLabel2 = Label(master, text='Use \"inputimage\" and \"outputimage\" in place of input and output images, respectively.\n'
                                          'If omitted, \"inputimage\" and \"outputimage\" will be appended to end of command.')
        commandLabel2.grid(row=6, column=0, columnspan=8)

    def apply(self):
        return

    def cancel(self, event=None):
        self.destroy()