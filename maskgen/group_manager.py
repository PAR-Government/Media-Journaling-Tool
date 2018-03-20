# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import matplotlib
matplotlib.use("TkAgg")
from Tkinter import *
from group_filter import GroupFilter
import tkSimpleDialog
from tool_set import get_icon
from PIL import ImageTk
from PIL import Image


class GroupManagerDialog(tkSimpleDialog.Dialog):
    gfl = None
    lastselection = None

    def __init__(self, parent, grpFilterManager):
        self.parent = parent
        self.gfl = grpFilterManager
        tkSimpleDialog.Dialog.__init__(self, parent, grpFilterManager.getName() + " Group Manager")

    def body(self, master):
        Label(master, text="Group").grid(row=0, column=0)
        Label(master, text="Avaiable").grid(row=0, column=3)
        Label(master, text="Assigned").grid(row=0, column=5)
        self.yGBScroll = Scrollbar(master, orient=VERTICAL)
        self.yGBScroll.grid(row=1, column=2, sticky=N + S)
        self.groupBox = Listbox(master, yscrollcommand=self.yGBScroll.set)
        self.yGBScroll['command'] = self.groupBox.yview
        for name in self.gfl.getGroupNames():
            self.groupBox.insert(END, name)
        self.groupBox.grid(row=1, column=0, columnspan=2, sticky=N + S + E + W)
        self.groupBox.bind("<<ListboxSelect>>", self.groupselect)
        self.addImage = ImageTk.PhotoImage(Image.open(get_icon('add.png')).resize((16, 16)))
        self.subImage = ImageTk.PhotoImage(Image.open(get_icon('subtract.png')).resize( (16, 16)))
        self.addb = Button(master, image=self.addImage, text="Add", command=self.addgroup)
        self.addb.grid(row=2, column=0)
        self.subb = Button(master, image=self.subImage, text="Sub", command=self.subgroup)
        self.subb.grid(row=2, column=1)

        self.yAVScroll = Scrollbar(master, orient=VERTICAL)
        self.yAVScroll.grid(row=1, column=4, sticky=N + S)
        self.availableBox = Listbox(master, yscrollcommand=self.yAVScroll.set)
        self.availableBox.grid(row=1, column=3, sticky=N + S + E + W)
        self.yAVScroll['command'] = self.availableBox.yview

        self.yASScroll = Scrollbar(master, orient=VERTICAL)
        self.yASScroll.grid(row=1, column=6, sticky=N + S)
        self.assignedBox = Listbox(master, yscrollcommand=self.yASScroll.set)
        self.assignedBox.grid(row=1, column=5, sticky=N + S + E + W)
        self.yASScroll['command'] = self.assignedBox.yview

        self.addFilterImage = ImageTk.PhotoImage(Image.open(get_icon("rightarrow.png")).resize( (16, 16)))
        self.subFilterImage = ImageTk.PhotoImage(Image.open(get_icon("leftarrow.png")).resize( (16, 16)))
        self.addFilterButton = Button(master, image=self.addFilterImage, text="Add", command=self.addfilter)
        self.addFilterButton.grid(row=2, column=3)
        self.subFilterButton = Button(master, image=self.subFilterImage, text="Sub", command=self.subfilter)
        self.subFilterButton.grid(row=2, column=5)

    def addfilter(self):
        if len(self.availableBox.curselection()) == 0:
            return
        index = int(self.availableBox.curselection()[0])
        value = self.availableBox.get(index)
        self.assignedBox.insert(END, value)
        self.availableBox.delete(index)
        self._refilAvailable()

    def _refilAvailable(self):
        whatsleft = self.availableBox.get(0, END)
        whatsused = self.assignedBox.get(0, END)
        checked_whatsleft = self.gfl.getAvailableFilters(operations_used=whatsused)
        if len(checked_whatsleft) != len(whatsleft):
            self.availableBox.delete(0, END)
            checked_whatsleft = sorted(checked_whatsleft)
            for filter in checked_whatsleft:
                self.availableBox.insert(END, filter)

    def subfilter(self):
        if len(self.assignedBox.curselection()) == 0:
            return
        index = int(self.assignedBox.curselection()[0])
        value = self.assignedBox.get(index)
        self.availableBox.insert(END, value)
        self.assignedBox.delete(index)
        self._refilAvailable()

    def populateFilterBoxes(self, groupFilter):
        self.assignedBox.delete(0, END)
        self.availableBox.delete(0, END)
        for filter in groupFilter.filters:
            self.assignedBox.insert(END, filter)
        available = set(self.gfl.getAvailableFilters(operations_used=groupFilter.filters))
        available = sorted(available)
        for filter in available:
            self.availableBox.insert(END, filter)

    def addgroup(self):
        d = tkSimpleDialog.askstring("Add Group", "Name", parent=self)
        if d is not None:
            self.gfl.add(GroupFilter(d, []))
            self.groupBox.insert(END, d)

    def subgroup(self):
        if len(self.groupBox.curselection()) > 0:
            index = int(self.groupBox.curselection()[0])
            value = self.groupBox.get(index)
            self.gfl.remove(value)
            self.groupBox.delete(index)

    def apply(self):
        if len(self.groupBox.curselection()) > 0:
            index = int(self.groupBox.curselection()[0])
            value = self.groupBox.get(index)
            self.savecondition(value)
        elif self.lastselection is not None:
            self.savecondition(self.lastselection)
        self.gfl.save()
        return

    def savecondition(self, grpName):
        import logging
        grp = self.gfl.getGroup(grpName)
        if grp is None:
            logging.getLogger('maskgen').warn('Group {} not found'.format(grpName))
            return
        grp.filters = []
        for filter in self.assignedBox.get(0, END):
            grp.filters.append(filter)

    def groupselect(self, event):
        if self.lastselection is not None:
            self.savecondition(self.lastselection)
        index = int(self.groupBox.curselection()[0])
        value = self.groupBox.get(index)
        self.lastselection = value
        grp = self.gfl.getGroup(value)
        self.populateFilterBoxes(grp)


class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    
    """

    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())

        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())

        canvas.bind('<Configure>', _configure_canvas)

        return
