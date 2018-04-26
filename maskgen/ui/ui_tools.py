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
