# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import collections
import json
import os
import tkSimpleDialog

import maskgen.plugins
import maskgen.software_loader
from maskgen.group_filter import GroupOperationsLoader
from maskgen.ui.autocomplete_it import *


class PluginBuilder(tkSimpleDialog.Dialog):
    def __init__(self, master, gopLoader):
        """
        :param master:
        :param gopLoader:
        @type gopLoader: GroupOperationsLoader
        """
        self.gopLoader = gopLoader
        self.softwareLoader = maskgen.software_loader.SoftwareLoader()
        self.sourcefiletype = 'image'
        self.targetfiletype = 'image'
        self.master = master
        self.arguments = []
        tkSimpleDialog.Dialog.__init__(self, master)

    def body(self, master):
        nameLabel = Label(master, text='Plugin Name: ')
        nameLabel.grid(row=0, column=0)
        self.nameEntry = Entry(master, width=40)
        self.nameEntry.grid(row=0, column=1, sticky='EW')

        descriptionLabel = Label(master, text='Description: ')
        descriptionLabel.grid(row=1, column=0)
        self.descriptionEntry = Text(master, width=40, height=3)
        self.descriptionEntry.grid(row=1, column=1, sticky='EW')

        cats = self.organizeOperationsByCategory()
        catlist = list(cats.keys())
        catlist.sort()
        oplist = cats[catlist[0]] if len(cats) > 0 else []
        self.opCatEntry = AutocompleteEntryInText(master, values=catlist, takefocus=False, width=40, state='readonly')
        self.opNameEntry = AutocompleteEntryInText(master, values=oplist, takefocus=False, width=40, state='readonly')
        self.softwareNameEntry = AutocompleteEntryInText(master, values=sorted(self.softwareLoader.get_names(self.sourcefiletype), key=str.lower), takefocus=False,
                                          width=40,state='readonly')
        self.softwareVersionEntry = AutocompleteEntryInText(master, values=self.softwareLoader.get_versions(self.softwareNameEntry.get(),software_type=self.sourcefiletype),
                                    initialValue=self.softwareLoader.get_preferred_version(name=self.softwareNameEntry.get()), takefocus=False, width=40)
        self.opCatEntry.bind("<Return>", self.newcategory)
        self.opCatEntry.bind("<<ComboboxSelected>>", self.newcategory)
        self.opNameEntry.bind("<Return>", self.newcommand)
        self.opNameEntry.bind("<<ComboboxSelected>>", self.newcommand)
        self.softwareNameEntry.bind("<Return>", self.newsoftware)
        self.softwareNameEntry.bind("<<ComboboxSelected>>", self.newsoftware)

        opCatLabel = Label(master, text='Operation Category: ')
        opCatLabel.grid(row=2, column=0)
        self.opCatEntry.grid(row=2, column=1, sticky='EW')

        opNameLabel = Label(master, text='Operation Name: ')
        opNameLabel.grid(row=3, column=0)
        self.opNameEntry.grid(row=3, column=1, sticky='EW')

        softwareNameLabel = Label(master, text='Software Name: ')
        softwareNameLabel.grid(row=4, column=0)
        self.softwareNameEntry.grid(row=4, column=1, sticky='EW')

        softwareVersionLabel = Label(master, text='Software Version: ')
        softwareVersionLabel.grid(row=5, column=0)
        self.softwareVersionEntry.grid(row=5, column=1, sticky='EW')

        # suffixLabel = Label(master, text='Suffix: ')
        # suffixLabel.grid(row=6, column=0)
        # self.suffixEntry = Entry(master, width=40)
        # self.suffixEntry.grid(row=6, column=1, sticky='EW')

        commandLabel1 = Label(master, text='Command (exactly as it would be typed in command line):')
        commandLabel1.grid(row=7, column=0, columnspan=8)
        self.commandEntry = Entry(master, width=40)
        self.commandEntry.grid(row=8, column=0, columnspan=8, sticky='EW')

        commandLabel2 = Label(master, text='Use \"{inputimage}\" and \"{outputimage}\" in place of input and output images, respectively.\n'
                                          'If omitted, \"{inputimage}\" and \"{outputimage}\" will be appended to end of command.')
        commandLabel2.grid(row=9, column=0, columnspan=8)

        Label(master, text='Additional Arguments (optional):').grid(row=10)

        self.argFrame = Frame(master)
        self.argFrame.grid(row=11, column=0, columnspan=8)

        self.add_argument_row(row=0, col=0, initialize=True)


    def add_argument_row(self, row, col, initialize=False, event=None):
        if initialize == False:
            self.addArgButton.grid_forget()

        Label(self.argFrame, text='Arg Name: ').grid(row=row, column=col)
        argNameEntry = Entry(self.argFrame)
        argNameEntry.grid(row=row, column=col+1, sticky='EW')
        col+=2

        Label(self.argFrame, text='Arg Type: ').grid(row=row, column=col)
        typeBox = ttk.Combobox(self.argFrame, values=['String', 'ImageFile', 'XMPFile', 'Donor', 'Float', 'Int', 'List', 'YesNo', 'Time', 'Coordinates'])
        typeBox.set('String')
        typeBox.grid(row=row, column=col+1, sticky='EW')
        col+=2

        Label(self.argFrame, text='Default Value: ').grid(row=row, column=col)
        defaultValueBox = Entry(self.argFrame)
        defaultValueBox.grid(row=row, column=col+1, sticky='EW')

        row+=1
        col=0

        Label(self.argFrame, text='Description: ').grid(row=row, column=col)
        descriptionBox = Entry(self.argFrame)
        descriptionBox.grid(row=row, column=col+1, sticky='EW')

        col+=2

        Label(self.argFrame, text='List Values: ').grid(row=row, column=col)
        valuesBox = Entry(self.argFrame, state='disabled')
        valuesBox.grid(row=row, column=col+1, sticky='EW')
        typeBox.correspondingValues = valuesBox
        typeBox.bind("<<ComboboxSelected>>", self.set_valuesbox_state)

        col+=2
        insertButton = Button(self.argFrame, text='Insert', command=lambda:self.insert_arg(argNameEntry))
        insertButton.grid(row=row, column=col, columnspan=2, sticky='EW')

        row+=1
        col=0
        ttk.Separator(self.argFrame, orient=HORIZONTAL).grid(row=row, column=col, columnspan=8, sticky='EW')

        row+=1
        col=0
        self.addArgButton = Button(self.argFrame, text='Add another argument', command=lambda: self.add_argument_row(row=row, col=col))
        self.addArgButton.grid(row=row, column=col, columnspan=2)

        Fields = collections.namedtuple('Fields', 'argname, type, defaultvalue, description, values')
        f = Fields(argname=argNameEntry, type=typeBox, defaultvalue=defaultValueBox, description=descriptionBox, values=valuesBox)
        self.arguments.append(f)


    def insert_arg(self, entry):
        idx = self.commandEntry.index(INSERT)
        currentCommand = self.commandEntry.get()
        try:
            if currentCommand[idx-1] != ' ':
                self.commandEntry.insert(idx, ' ')
                idx+=1
        except IndexError:
            pass

        self.commandEntry.insert(idx, '{' + entry.get().replace(' ', '') + '}') if len(entry.get()) >0 else ''

        idx = self.commandEntry.index(INSERT)
        currentCommand = self.commandEntry.get()
        try:
            if currentCommand[idx+1] != ' ':
                self.commandEntry.insert(idx, ' ')
        except IndexError:
            pass


    def set_valuesbox_state(self, event=None):
        if event is not None:
            val = event.widget.get()
            value_entry = event.widget.correspondingValues
            if val == 'List':
                value_entry.config(state='normal')
            else:
                value_entry.config(state='disabled')


    def apply(self):
        self.pluginName = self.nameEntry.get().replace(' ', '')
        opName = self.opNameEntry.get()
        opCat = self.opCatEntry.get()
        description = self.descriptionEntry.get("1.0",END).strip()
        softwareName = self.softwareNameEntry.get()
        softwareVersion = self.softwareVersionEntry.get()
        #suffix = self.suffixEntry.get()
        command = self.commandEntry.get().split(' ')
        if '{inputimage}' not in command:
            command.append('{inputimage}')
        if '{outputimage}' not in command:
            command.append('{outputimage}')
        platform = sys.platform
        self.data = {"name": self.pluginName,
                    "operation": {
                        "name": opName,
                        "category": opCat,
                        "description": description,
                        "software": softwareName,
                        "version": softwareVersion,
                        "arguments": {},
                        "transitions": ['image.image']
                    },
                    #"suffix": suffix
                    "command": {
                        "default": command,
                        platform: command
                    }
        }

        self.export_arguments()

        self.path = os.path.join('plugins', 'Custom', self.pluginName) + '.json'
        # need to step up a directory to save the json
        with open(os.path.join('.', self.path), 'w') as newJSON:
            json.dump(self.data, newJSON, indent=4)

        maskgen.plugins.loadPlugins().loadCustom(self.pluginName, self.path)

    def cancel(self, event=None):
        self.destroy()

    def export_arguments(self):
        for argument in self.arguments:
            self.data['operation']['arguments'][argument.argname.get().replace(' ', '')] = {
                'type':argument.type.get().lower(),
                'defaultvalue':argument.defaultvalue.get(),
                'description':argument.description.get(),
            }
            if argument.type.get() == 'List':
                vals = argument.values.get().replace(', ', ',').split(',')
                self.data['operation']['arguments'][argument.argname.get().replace(' ', '')]['values'] = vals

    """
    the below functions are taken from the DescriptionCaptureDialog class in description_dialog.py
    (much of the code in this class has been borrowed from here)
    """
    def newcategory(self, event):
        opByCat = self.organizeOperationsByCategory()
        if self.opCatEntry.get() in opByCat:
            oplist = opByCat[self.opCatEntry.get()]
            self.opNameEntry.set_completion_list(oplist)
            self.newcommand(event)
        else:
            self.opNameEntry.set_completion_list([])

    def newcommand(self, event):
        op = self.gopLoader.getOperationWithGroups(self.opNameEntry.get())

    def organizeOperationsByCategory(self):
        return self.gopLoader.getOperationsByCategoryWithGroups(self.sourcefiletype, self.targetfiletype)

    def newsoftware(self, event):
        sname = self.softwareNameEntry.get()
        self.softwareVersionEntry.set_completion_list(self.softwareLoader.get_versions(sname,software_type=self.sourcefiletype),
                                    initialValue=self.softwareLoader.get_preferred_version(name=sname))

def main():
    maskgen.plugins.loadPlugins()
    root = Tk()
    root.withdraw()
    d = PluginBuilder(root)
    d.mainloop()

if __name__ == '__main__':
    main()

