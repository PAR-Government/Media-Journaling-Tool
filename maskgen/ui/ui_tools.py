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


class TimeWidget(Frame):
    def __init__(self, master, textvariable):
        self.time_text_variable = textvariable
        Frame.__init__(self, master)
        self.master = master
        self.entries = {}
        self.create_widgets()
        self.bind_all("<Control-v>", lambda e: self.paste())

    def create_widgets(self):
        initialvalues = self.time_text_variable.get().split(':')
        if len(initialvalues) > 2:
            micro = 0 if '.' not in initialvalues[-1] else initialvalues[-1].split('.')[1]
            second  = int(initialvalues[-1]) if  '.' not in initialvalues[-1] else initialvalues[-1].split('.')[0]
            minute = initialvalues[1]
            hour = initialvalues[0]
        else:
            micro  = "micros"
            second = "SS"
            minute = "MM"
            hour   = "HH"

        font = ("TkDefaultFont", 10)  # Increase font size

        # Setup fields
        self.entries['hour'] = w = Entry(self, width=3, font=font)
        w.insert(0, hour)
        w.bind('<KeyRelease>', lambda e: self.track('hour', 'minute', 2, 23))
        w.bind('<FocusIn>', lambda e: self.get_focus('hour'))
        w.bind('<FocusOut>', lambda e: self.lose_focus('hour', 2))
        w.grid(row=0, column=0)

        w = Label(self, text=":", font=font, bg='white')
        w.grid(row=0, column=1)

        self.entries['minute'] = w = Entry(self, width=3, font=font)
        w.insert(0, minute)
        w.bind('<KeyRelease>', lambda e: self.track('minute', 'second', 2, 59))
        w.bind('<FocusIn>', lambda e: self.get_focus('minute'))
        w.bind('<FocusOut>', lambda e: self.lose_focus('minute', 2))
        w.grid(row=0, column=2)

        w = Label(self, text=":", font=font, bg='white')
        w.grid(row=0, column=3)

        self.entries['second'] = w = Entry(self, width=3, font=font)
        w.insert(0, second)
        w.bind('<KeyRelease>', lambda e: self.track('second', 'microsecond', 2, 59))
        w.bind('<FocusIn>', lambda e: self.get_focus('second'))
        w.bind('<FocusOut>', lambda e: self.lose_focus('second', 2))
        w.grid(row=0, column=4)

        w = Label(self, text=".", font=font, bg='white')
        w.grid(row=0, column=5)

        self.entries['microsecond'] = w = Entry(self, width=10, font=font)
        w.insert(0, micro)
        w.bind('<KeyRelease>', lambda e: self.track('microsecond', None, 6, 999999))
        w.bind('<FocusIn>', lambda e: self.get_focus('microsecond'))
        w.bind('<FocusOut>', lambda e: self.lose_focus('microsecond', 6, prepend=False))
        w.grid(row=0, column=6)

    def get_focus(self, field):
        """
        Binding to clear field on first entry.  Allows for guidance on what units go where when tool launches

        :param field: Field name that gained focus
        :return:
        """
        # Clear default text, if any, and unbind this function
        if any([l.isalpha() for l in self.entries[field].get()]):
            self.entries[field].delete(0, END)
        self.entries[field].unbind('<FocusIn>')

    def lose_focus(self, field, max_length, prepend=True):
        """
        Binding to verify that all items in the field are properly padded before saving can occur.

        :param field: Field name that lost focus
        :param max_length: Maximum length of the item in that field
        :param prepend: Add to the beginning when true (9->09), add to the end when false (9->900000)
        :return: None
        """
        curr = self.entries[field].get()

        if len(curr) != 0 and len(curr) < max_length:
            if prepend:
                self.entries[field].insert(0, "0" * (max_length - len(curr)))
            else:
                self.entries[field].insert(END, "0" * (max_length - len(curr)))

        # Verify there are no letters
        if any([l.isalpha() for l in curr]):
            tkMessageBox.showerror("Error", "The {0}s field cannot contain letters.  Re-enter the {0}s.".format(field))
            self.entries[field].delete(0, END)
            self.entries[field].insert(0, "0" * max_length)
        else:
            self.update_variable()

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

        curr = self.entries[field].get()
        pos = self.entries[field].index(INSERT)

        # Check that there is a value in the entry
        if curr == "":
            return

        # Verify it is a number
        if not curr[pos-1].isdigit():
            first = pos-1
            last = pos

            for i in range(len(curr)):
                if not curr[i].isdigit():
                    first = i
                    break
            for i in range(0, len(curr), -1):
                if not curr[i].isdigit():
                    last = i
                    break

            self.entries[field].delete(first, last)
            return

        # enforce length restriction
        if len(curr) > max_length:
            self.entries[field].delete(0, END)
            self.entries[field].insert(0, curr[:max_length])
            self.update_variable()
            return

        # limit the value entered to the maximum
        if int(curr[:max_length]) > max_digit:
            self.entries[field].delete(0, END)
            self.entries[field].insert(0, max_digit)
            self.update_variable()
        # If we are at the end, go to the next cell
        if pos >= max_length and next_field:
            self.entries[next_field].focus()
            self.entries[next_field].icursor(0)
            self.update_variable()
            return

        self.entries[field].icursor(pos)

    def paste(self):
        """
        Handle pasting data into time boxes
        :return:
        """
        time = self.clipboard_get()

        try:
            hr, mins, sfm = time.split(":")
            s, fm = sfm.split(".")
        except ValueError:
            return

        # Run through focus gain so text boxes wont self delete
        self.get_focus("hour")
        self.get_focus("minute")
        self.get_focus("second")
        self.get_focus("microsecond")

        # Insert data and verify that it is valid
        self.entries['hour'].delete(0, END)
        self.entries['hour'].insert(0, hr)
        self.lose_focus("hour", 2)
        self.track("hour", None, 2, 23)

        self.entries['minute'].delete(0, END)
        self.entries['minute'].insert(0, mins)
        self.lose_focus("minute", 2)
        self.track("minute", None, 2, 59)

        self.entries['second'].delete(0, END)
        self.entries['second'].insert(0, s)
        self.lose_focus("second", 2)
        self.track("second", None, 2, 59)

        self.entries['microsecond'].delete(0, END)
        self.entries['microsecond'].insert(0, fm)
        self.lose_focus("microsecond", 6, prepend=FALSE)
        self.track("microsecond", None, 6, 999999)

    def update_variable(self):
        self.time_text_variable.set(self.__str__())

    def __str__(self):
        if all(self.isblank(value.get()) for value in self.entries.values()):
            return ''
        return "{0}:{1}:{2}.{3}".format(self.entries['hour'].get(), self.entries['minute'].get(),
                                        self.entries['second'].get(), self.entries['microsecond'].get())

    def isblank(self, v):
        initial = ['HH', 'MM', 'SS', 'micros']
        if v in initial or v == '':
            return True
        else:
            return False

    def get(self):
        try:
            if all(self.isblank(value.get()) for value in self.entries.values()):
                return ''
            else:
                for k, v in self.entries:
                    entryString = v.get()
                    if not entryString.isdigit():
                        raise ValueError("Not digit")

            self.update_variable()
        except ValueError:
            tkMessageBox.showerror("Data Error", "Hours, minutes, seconds, and microseconds must all be integers.")
            return ""
        return self


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
