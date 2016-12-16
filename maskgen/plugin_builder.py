import tkSimpleDialog
import os
import json
import software_loader
from group_filter import getOperationWithGroups,getOperationsByCategoryWithGroups,getCategoryForOperation
from autocomplete_it import *
import plugins

class PluginBuilder(tkSimpleDialog.Dialog):
    def __init__(self, master):
        self.softwareLoader = software_loader.SoftwareLoader()
        self.sourcefiletype = 'image'
        self.targetfiletype = 'image'
        self.master = master
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
        self.opCatEntry = AutocompleteEntryInText(master, values=catlist, takefocus=False, width=40)
        self.opNameEntry = AutocompleteEntryInText(master, values=oplist, takefocus=False, width=40)
        self.softwareNameEntry = AutocompleteEntryInText(master, values=sorted(self.softwareLoader.get_names(self.sourcefiletype), key=str.lower), takefocus=False,
                                          width=40)
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

        data = {"name": self.pluginName,
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
                "command": command
        }

        self.path = os.path.join('plugins', 'Custom', self.pluginName) + '.json'
        # need to step up a directory to save the json
        with open(os.path.join('.', self.path), 'w') as newJSON:
            json.dump(data, newJSON)

        plugins.loadCustom(self.pluginName, self.path)

    def cancel(self, event=None):
        self.destroy()

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
        op = getOperationWithGroups(self.opNameEntry.get())

    def organizeOperationsByCategory(self):
        return getOperationsByCategoryWithGroups(self.sourcefiletype, self.targetfiletype)

    def newsoftware(self, event):
        sname = self.softwareNameEntry.get()
        self.softwareVersionEntry.set_completion_list(self.softwareLoader.get_versions(sname,software_type=self.sourcefiletype),
                                    initialValue=self.softwareLoader.get_preferred_version(name=sname))

def main():
    plugins.loadPlugins()
    software_loader.loadOperations(os.path.join('.', 'resources', 'operations.json'))
    software_loader.loadSoftware(os.path.join('.', 'resources', 'software.csv'))
    root = Tk()
    root.withdraw()
    d = PluginBuilder(root)
    d.mainloop()

if __name__ == '__main__':
    main()

