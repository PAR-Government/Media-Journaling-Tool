from Tkinter import *
from tkSimpleDialog import Dialog

class ErrorWindow(Dialog):
    def __init__(self, master, errors):
        self.errors = errors
        self.cancelPressed = True
        Dialog.__init__(self, master, title='Validation')


    def body(self, master):
        yscrollbar = Scrollbar(self)
        yscrollbar.pack(side=RIGHT, fill=Y)
        xscrollbar = Scrollbar(self, orient=HORIZONTAL)
        xscrollbar.pack(side=BOTTOM, fill=X)

        listbox = Listbox(self, width=80, height=15)
        listbox.pack(fill=BOTH, expand=1)

        if type(self.errors) == dict:
            for i in self.errors:
                for message in self.errors[i]:
                    listbox.insert(END, message[1])

        else:
            for i in self.errors:
                listbox.insert(END, i)

        # attach listbox to scrollbar
        listbox.config(yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set)
        yscrollbar.config(command=listbox.yview)
        xscrollbar.config(command=listbox.xview)

    def apply(self):
        self.cancelPressed = False