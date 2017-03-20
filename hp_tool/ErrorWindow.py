from Tkinter import *
from tkSimpleDialog import Dialog

class ErrorWindow(Dialog):
    def __init__(self, master, errors):
        self.errors = errors
        self.cancelPressed = True
        Dialog.__init__(self, master, title='Spreadsheet Validation')


    def body(self, master):
        scrollbar = Scrollbar(self)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = Listbox(self, width=80, height=15)
        listbox.pack()

        for i in self.errors:
            listbox.insert(END, i)

        # attach listbox to scrollbar
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

    def apply(self):
        self.cancelPressed = False