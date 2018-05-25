# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import ttk
from Tkinter import *
import tkSimpleDialog
import tkFont
from maskgen.scenario_model import ImageProjectModel, Modification


class HistoryDialog(Toplevel):
    def __init__(self, master, scModel):
        """

        :param master:
        :param scModel:
         @type scModel: ImageProjectModel
        """
        self.parent = master
        self.scModel = scModel
        Toplevel.__init__(self, master)
        self.resizable(width=True, height=True)
        self.title('History')
        body = Frame(self)
        self.body(body)
        body.grid(row=0, column=0, sticky=N + E + S + W)
        self.grid_propagate(True)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        w = self.buttons(body)
        w.grid(row=2, column=0)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (master.winfo_rootx() + 50,
                                  master.winfo_rooty() + 50))

    def body(self, master):
        self.history_frame = HistoryFrame(master, self.scModel)
        self.history_frame.grid(row=0, sticky=NSEW)

    def buttons(self, frame):
        return Button(frame, text="OK", width=10, command=self.cancel, default=ACTIVE)

    def cancel(self):
        self.parent.focus_set()
        self.destroy()

    def wait(self, root):
        root.wait_window(self)


class HistoryFrame(Frame):
    """ Display a table of operations, in lieu of the graph view
    """
    modifications = []

    def __init__(self, master, scModel):
        """
               :param master:
               :param scModel:
                @type scModel: ImageProjectModel
        """
        Frame.__init__(self, master)
        self.createWidgets()
        self.loadData(scModel)

    def focus(self):
        return self.tree.focus()

    def createWidgets(self):
        # create the tree and scrollbars
        self.dataCols = ('Operation', 'Start', 'End', 'Time', 'User', 'Description')
        self.tree = ttk.Treeview(self, columns=self.dataCols, show='headings', selectmode='browse',
                                 displaycolumns='#all')
        self.tree.column('Operation', width=120, stretch=False, minwidth=120)
        self.tree.column('Start', width=120, stretch=False, minwidth=120)
        self.tree.column('End', width=120, minwidth=120)
        self.tree.column('User', width=120)
        self.tree.column('Time', width=140, stretch=False)
        self.tree.column('Description', width=400, minwidth=400)

        self.tree.heading("Operation", text="Operation")
        self.tree.heading("Start", text="Start")
        self.tree.heading("End", text="End")
        self.tree.heading("User", text="User")
        self.tree.heading("Time", text="Time")
        self.tree.heading("Description", text="Description")

        self.ysb = ttk.Scrollbar(self, orient=VERTICAL, command=self.tree.yview)
        self.xsb = ttk.Scrollbar(self, orient=HORIZONTAL, command=self.tree.xview)
        self.tree['yscroll'] = self.ysb.set
        self.tree['xscroll'] = self.xsb.set

        # add tree and scrollbars to frame
        self.tree.grid(row=0, column=0, sticky=NSEW)
        self.ysb.grid(row=0, column=1, sticky=NS)
        self.xsb.grid(row=1, column=0, sticky=EW)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def clearData(self):
        for mod in self.modifications:
            self.tree.delete(mod.maskFileName)
        self.modifications = []

    def loadData(self, scModel):
        """
        :param scModel:
        :return: None
        @type scModel : ImageProjectModel
        """
        self.modifications = sorted(scModel.getDescriptions(), key=lambda mod: mod.ctime, reverse=True)
        for moddata in self.modifications:
            self._load(moddata)

    def _load(self, mod):
        """
        :param start:
        :param end:
        :param mod:
        :return:
        @type start: str
        @type end: str
        @type mod: Modification
        """
        item = (mod.operationName, mod.start, mod.end, mod.ctime, mod.username, mod.additionalInfo)
        self.tree.insert('', 'end', iid=mod.changeMaskName, values=item)
        # and adjust column widths if necessary
        for idx, val in enumerate(item):
            iwidth = tkFont.Font().measure(val)
            if self.tree.column(self.dataCols[idx], 'width') < iwidth:
                self.tree.column(self.dataCols[idx], width=iwidth)
