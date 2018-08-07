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
        Label(master,textvariable=self.system_label_var,anchor=W, justify=LEFT,width=20).grid(row=0,column=1)
        ttk.Separator().grid(row=0,column=2)
        Label(master,textvariable=self.module_label_var,anchor=W, justify=LEFT,width=20).grid(row=0, column=3)
        ttk.Separator().grid(row=0,column=4)
        Label(master,textvariable=self.function_label_var,anchor=W, justify=LEFT,width=40).grid(row=0, column=5)
        ttk.Separator().grid(row=0,column=6)
        self.pb_status = DoubleVar()
        self.pb_status.set(0)
        self.pb = ttk.Progressbar(master,
                                  variable=self.pb_status,
                                  orient='horizontal',
                                  mode='determinate',
                                  maximum=100.001)
        self.pb.grid(row=0,column=7,sticky=E)

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


class TimeFrame(Frame):
    def __init__(self, master, microseconds=True):
        Frame.__init__(self, master)
        self.master = master
        self.entries = {}
        self.microseconds = microseconds
        self.create_widgets()

    def create_widgets(self):
        font = ("TkDefaultFont", 14)  # Increase font size

        # Setup fields
        self.entries['hour'] = w = Entry(self, width=2, font=font)
        w.insert(0, "00")
        w.bind('<KeyRelease>', lambda e: self.track('hour', 'minute', 2, 99))
        w.bind('<FocusOut>', lambda e: self.lose_focus('hour', 2))
        w.grid(row=0, column=0)

        w = Label(self, text=":", font=font, bg='white')
        w.grid(row=0, column=1)

        self.entries['minute'] = w = Entry(self, width=2, font=font)
        w.insert(0, "00")
        w.bind('<KeyRelease>', lambda e: self.track('minute', 'second', 2, 59))
        w.bind('<FocusOut>', lambda e: self.lose_focus('minute', 2))
        w.grid(row=0, column=2)

        w = Label(self, text=":", font=font, bg='white')
        w.grid(row=0, column=3)

        self.entries['second'] = w = Entry(self, width=2, font=font)
        w.insert(0, "00")
        w.bind('<KeyRelease>', lambda e: self.track('second', 'microsecond' if self.microseconds else "frame", 2, 59))
        w.bind('<FocusOut>', lambda e: self.lose_focus('second', 2))
        w.grid(row=0, column=4)

        w = Label(self, text=".", font=font, bg='white')
        w.grid(row=0, column=5)

        w = Entry(self, width=(6 if self.microseconds else len(str(sys.maxint))), font=font)
        w.insert(0, "0" * (6 if self.microseconds else len(str(sys.maxint))))
        if self.microseconds:
            self.entries['microsecond'] = w
            w.bind('<KeyRelease>', lambda e: self.track('microsecond', None, 6, 999999))
            w.bind('<FocusOut>', lambda e: self.lose_focus('microsecond', 6, prepend=False))
        else:
            self.entries['frame'] = w
            w.bind('<KeyRelease>', lambda e: self.track('frame', None, len(str(sys.maxint)), sys.maxint))
            w.bind('<FocusOut>', lambda e: self.lose_focus('frame', len(str(sys.maxint))))
        w.grid(row=0, column=6)

    def lose_focus(self, field, max_length, prepend=True):
        """
        Binding to verify that all items in the field are properly padded before saving can occur.

        :param field: Field name that lost focus
        :param max_length: Maximum length of the item in that field
        :param prepend: Add to the beginning when true (9->09), add to the end when false (9->900000)
        :return: None
        """
        curr = self.entries[field].get()

        if len(curr) == max_length:
            return

        if prepend:
            self.entries[field].insert(0, "0" * (max_length - len(curr)))
        else:
            self.entries[field].insert(END, "0" * (max_length - len(curr)))

        # Verify there are no letters within the entry
        if any([l.isalpha() for l in curr]):
            tkMessageBox.showerror("Error", "The {0}s field cannot contain letters.  Re-enter the {0}s.".format(field))
            self.entries[field].delete(0, END)
            self.entries[field].insert(0, "0" * (6 if self.microseconds else 9))

    def track(self, field, next_field, max_length, max_digit):
        """
        Binding to verify that the value within each entry is valid in terms of length, and the maximum value that can
        exist in the field.

        :param field: Current field name
        :param next_field: Field to jump to once current field is entered
        :param max_length: Maximum length of the value in the field (character count)
        :param max_digit: Maximum value that the field can hold
        :return:
        """
        def check_max(num, max_num):
            """
            Funtion to verify that the user did not exceed the maximum value.

            :param num: Number to check
            :param max_num: Maximum value of the passed number
            :return:
            """
            if max_num >= num:
                return True

            self.entries[field].delete(0, END)
            replace = ""
            for i in range(1, len(curr)):
                if int(str(max_digit)[:i]) >= int(curr[:i]):
                    replace = int(curr[:i])
                else:
                    break
            self.entries[field].insert(0, replace)
            return False

        curr = self.entries[field].get()
        pos = self.entries[field].index(INSERT)

        # Check that there is a value in the entry
        if curr == "":
            return

        # Verify it is a number
        if curr[pos-1] not in map(str, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]):
            self.entries[field].delete(pos - 1, pos)
            self.entries[field].insert(pos, 0)
            return

        # Check that there is room for the character
        elif len(curr) >= max_length:
            if check_max(int(curr[:max_length]), max_digit):
                self.entries[field].delete(0, END)
                self.entries[field].insert(0, curr[:max_length])  # [:max_length] prevents button holding that [:-1] doesn't

                # If we are at the end, go to the next cell
                if pos >= max_length and next_field:
                    self.entries[next_field].focus()
                    self.entries[next_field].icursor(0)
            self.entries[field].icursor(pos)
            return

    def __str__(self):
        return "{0}:{1}:{2}.{3}".format(self.entries['hour'].get(), self.entries['minute'].get(),
                                        self.entries['second'].get(), self.entries['microsecond'].get() if
                                        self.microseconds else self.entries['frame'].get())


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
