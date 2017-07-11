from Tkinter import *
from tkSimpleDialog import Dialog
import json
import csv
import tkFileDialog

class ErrorWindow(Dialog):
    """
    Provided a list of error messages, shows them in a simple pop-up window.
    """
    def __init__(self, master, errors):
        self.errors = errors
        self.cancelPressed = True
        Dialog.__init__(self, master, title='Validation')


    def body(self, master):
        frame = Frame(self, bd=2, relief=SUNKEN)
        frame.pack(fill=BOTH, expand=TRUE)
        yscrollbar = Scrollbar(frame)
        yscrollbar.pack(side=RIGHT, fill=Y)
        xscrollbar = Scrollbar(frame, orient=HORIZONTAL)
        xscrollbar.pack(side=BOTTOM, fill=X)

        self.listbox = Listbox(frame, width=80, height=15)
        self.listbox.pack(fill=BOTH, expand=1)

        if type(self.errors) == str:
            with open(self.errors) as j:
                self.errors = json.load(j)

        if type(self.errors) == dict:
            for i in self.errors:
                for message in self.errors[i]:
                    self.listbox.insert(END, message[1])
        else:
            for i in self.errors:
                self.listbox.insert(END, i)

        # attach listbox to scrollbar
        self.listbox.config(yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set)
        yscrollbar.config(command=self.listbox.yview)
        xscrollbar.config(command=self.listbox.xview)



    def buttonbox(self):
        box = Frame(self)

        exportButton = Button(self, text='Export', width=10, command=self.export)
        exportButton.pack(side=RIGHT, padx=5, pady=5)
        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)


        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def export(self):
        with tkFileDialog.asksaveasfile(mode='w', defaultextension='.txt') as f:
            f.write('\n'.join(self.listbox.get(0, END)))
            f.write('\n')

    def apply(self):
        self.cancelPressed = False