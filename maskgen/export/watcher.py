import maskgen.scenario_model
import maskgen.image_graph
import Tkinter
from Tkinter import Toplevel
from Tkinter import *
import ttk

class ExportWatcherDialouge(Toplevel()):
    def __init__(self, parent):
        self.parent = parent
        Toplevel.__init__(self, parent)


    def createWidgets(self):
        mainFrame = Frame(self)
        

