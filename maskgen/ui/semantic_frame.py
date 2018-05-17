from maskgen.ui.collapsing_frame import Accordion, Chord
from maskgen.software_loader import *
from maskgen.ui.ui_tools import SelectDialog
from Tkinter import *


class SemanticFrame(Frame):
    def __init__(self, master):
        self.master = master
        Frame.__init__(self, master)
        self.setup_frame()
    
    def setup_frame(self):
        self.popup = Menu(self, tearoff=0)
        self.popup.add_command(label="Add", command=self.group_add)
        self.popup.add_command(label="Remove", command=self.group_remove)  #

        self.collapseFrame = Accordion(self)  # ,height=100,width=100)
        self.groupFrame = Chord(self.collapseFrame, title='Semantic Groups')
        self.gscrollbar = Scrollbar(self.groupFrame, orient=VERTICAL)
        self.listbox = Listbox(self.groupFrame, yscrollcommand=self.gscrollbar.set, height=3)
        self.listbox.config(yscrollcommand=self.gscrollbar.set)
        self.listbox.bind("<<ListboxSelect>>", self.listBoxHandler)
        self.listbox.grid(row=0, column=0, columnspan=3, sticky=E + W)
        self.gscrollbar.config(command=self.listbox.yview)
        self.gscrollbar.grid(row=0, column=1, stick=N + S)
        self.collapseFrame.append_chords([self.groupFrame])
        self.collapseFrame._click_handler(self.groupFrame)
        self.collapseFrame.pack()

    def group_remove(self):
        self.listbox.delete(ANCHOR)

    def group_add(self):
        d = SelectDialog(self, "Set Semantic Group", 'Select a semantic group for these operations.',
                         getSemanticGroups(), information="semanticgroup")
        res = d.choice
        if res is not None:
            self.listbox.insert(END, res)

    def listBoxHandler(self, evt):
        # Note here that Tkinter passes an event object to onselect()
        w = evt.widget
        x = w.winfo_rootx()
        y = w.winfo_rooty()
        if w.curselection() is not None and len(w.curselection()) > 0:
            index = int(w.curselection()[0])
            self.group_to_remove = index
        try:
            self.popup.tk_popup(x, y, 0)
        finally:
            # make sure to release the grab (Tk 8.0a1 only)
            self.popup.grab_release()

    def getListbox(self):
        return self.listbox

    def insertListbox(self, index, element):
        self.listbox.insert(index, element)
        return

    def getListContents(self, start, end):
        return self.listbox.get(start, end)
