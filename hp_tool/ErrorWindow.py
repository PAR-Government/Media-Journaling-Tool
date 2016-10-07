from Tkinter import *

class ErrorWindow(Toplevel):
    def __init__(self, errors, master=None):
        Toplevel.__init__(self, master)
        self.wm_title('Spreadsheet Validation')
        self.errors = errors

    def show_errors(self):
        scrollbar = Scrollbar(self)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = Listbox(self, width=80, height=15)
        listbox.pack()

        for i in self.errors:
            listbox.insert(END, i)

        # attach listbox to scrollbar
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)