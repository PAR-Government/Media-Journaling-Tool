# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import time
import ttk
from Tkinter import *
import  tkSimpleDialog
import tkMessageBox
import logging
from maskgen.support import ModuleStatus


class ProgressBar(Frame):
    def __init__(self, master, **kwargs):
        Frame.__init__(self, master, **kwargs)
        self.body(self)
        self.last_time = time.time()

    def body(self,master):
        self.system_label_var = StringVar()
        self.system_label_var.set('              ')
        self.module_label_var = StringVar()
        self.module_label_var.set('              ')
        self.function_label_var = StringVar()
        self.function_label_var.set('              ')
        Label(master,textvariable=self.system_label_var,anchor=W, justify=LEFT,width=20).grid(row=0,column=0)
        ttk.Separator().grid(row=0,column=1)
        Label(master,textvariable=self.module_label_var,anchor=W, justify=LEFT,width=20).grid(row=0, column=2)
        ttk.Separator().grid(row=0,column=3)
        Label(master,textvariable=self.function_label_var,anchor=W, justify=LEFT,width=40).grid(row=0, column=4)
        ttk.Separator().grid(row=0,column=5)
        self.pb_status = DoubleVar()
        self.pb_status.set(0)
        self.pb = ttk.Progressbar(master,
                                  variable=self.pb_status,
                                  orient='horizontal',
                                  mode='determinate',
                                  maximum=100.001)
        self.pb.grid(row=0,column=6,sticky=E)

    def postChange(self,module_status):
        """

        :param module_status:
        :return:
        @type module_status: ModuleStatus
        """
        current_time = time.time()
        # update if the system changes or the last update occurred more than the prior 1.2
        # seconds or the percentage is effectively complete.
        if module_status.system_name != self.system_label_var.get() or \
                                current_time - self.last_time > 1.2 or \
                        module_status.percentage >= 99.9999:
            logging.getLogger('maskgen').info('%s %s %s %2.3f' % (module_status.system_name,
                                                                  module_status.module_name,
                                                               module_status.component,
                                                               module_status.percentage))
            self.system_label_var.set(module_status.system_name)
            self.module_label_var.set(module_status.module_name)
            self.function_label_var.set(module_status.component)
            delta = module_status.percentage - self.pb_status.get()
            self.pb.step(delta)
            self.pb_status.set(module_status.percentage)
            if module_status.percentage >= 99.9999:
                self.pb_status.set(0)
            self.last_time = current_time
            self.pb.update_idletasks()

class SelectDialog(tkSimpleDialog.Dialog):
    cancelled = True

    def __init__(self, parent, name, description, values, initial_value=None, information=None, callback=None):
        self.description = description
        self.values = values
        self.parent = parent
        self.initial_value = initial_value
        self.name = name
        self.information = information
        self.callback = callback
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        self.desc_lines = '\n'.join(self.description.split('.'))
        self.desc_label = Label(master, text=self.desc_lines, wraplength=400)
        self.desc_label.grid(row=0, sticky=N, columnspan=(3 if self.information else 1))
        self.var1 = StringVar()
        self.var1.set(self.values[0] if self.initial_value is None or self.initial_value not in self.values else self.initial_value)
        self.e1 = OptionMenu(master, self.var1, *self.values)
        self.e1.grid(row=1, column=0, sticky=N, columnspan=3 if self.information else 1)
        if self.information:
            from maskgen.ui.help_tools import HelpFrame
            fr = HelpFrame(master, self.information, self.var1)
            fr.grid(row=2, column=0, columnspan=3)

    def cancel(self):
        if self.cancelled:
            self.choice = None
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.choice = self.var1.get()
        if self.callback is not None:
            self.callback(self.var1.get())


class AddRemove(SelectDialog):
    def __init__(self, parent, name, description, values, initial_value=None, information=None):
        SelectDialog.__init__(self, parent, name, description, values, initial_value, information)

    def buttonbox(self):
        box = Frame(self)

        self.add_button = Button(box, text="Add", width=10, command=self.add, default=ACTIVE)
        self.add_button.pack(side=LEFT, padx=5, pady=5)
        self.remove_button = Button(box, text="Remove", width=10, command=self.remove)
        self.remove_button.pack(side=LEFT, padx=5, pady=5)
        self.cancel_button = Button(box, text="Cancel", width=10, command=self.cancel)
        self.cancel_button.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Escape>", self.cancel)

        box.pack()

    def add(self):
        self.cancelled = False
        self.ok()
        self.choice = (self.var1.get(), "add")

    def remove(self):
        self.cancelled = False
        self.ok()
        self.choice = (self.var1.get(), "remove")

class EntryDialog(tkSimpleDialog.Dialog):
    cancelled = True

    def __init__(self, parent, name, description, validateFunc, initialvalue=None):
        self.description = description
        self.validateFunc = validateFunc
        self.parent = parent
        self.name = name
        self.initialvalue = initialvalue
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        Label(master, text=self.description).grid(row=0, sticky=W)
        self.e1 = Entry(master, takefocus=True)
        if self.initialvalue:
            self.e1.insert(0, self.initialvalue)
        self.e1.grid(row=1, column=0)
        self.lift()

    def cancel(self):
        if self.cancelled:
            self.choice = None
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.choice = self.e1.get()

    def validate(self):
        v = self.e1.get()
        if self.validateFunc and not self.validateFunc(v):
            tkMessageBox.showwarning(
                "Bad input",
                "Illegal values, please try again"
            )
            return 0
        return 1


class ScrollableListbox(Frame):
    def __init__(self, master, height, width):
        Frame.__init__(self, master)
        self.master = master
        self.height = height
        self.width = width
        self.create_widgets()

    def create_widgets(self):
        self.lb = Listbox(self, height=self.height, width=self.width)
        self.lb.grid(row=0, column=0, sticky=N + S)
        sb = Scrollbar(self, orient=VERTICAL)
        sb.grid(row=0, column=1, sticky=N + S)
        self.lb.config(yscrollcommand=sb.set)
        sb.config(command=self.lb.yview)

    def get_listbox(self):
        return self.lb
