from Tkinter import *
from PIL import ImageTk
from tool_set import imageResizeRelative
import tkSimpleDialog
from maskgen.image_wrap import openImageFile
import logging
from tool_set import fileType
import Tkinter as tk
import numpy as np
import matplotlib
matplotlib.use("TkAgg")



"""
   Support classes for visualizing final image node analytics
"""

class MaskGenAnalytic:

    """
    Each analytic extends me
    """

    def screenName(self):
        """
        :return: The string name of the type analytic I am
        """
        return ''

    def appliesTo(self, filename):
        """
        :param filename:
        :return: True if this analytic is applicable to this video/image file
        """
        return False

    def draw(self,frame, filename):
        """
           Create a canvas; add it to the provide frame at grid row 0, column 0
        :param frame:
        :param filename:
        :return:
        """
        pass

class YuvHistogramAnalytic:

    def screenName(self):
        return "Luminance Histogram"

    def appliesTo(self, filename):
        return fileType(filename) == 'image'

    def draw(self,frame, filename):
        from matplotlib.figure import Figure
        import pandas as pd
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        channels = openImageFile(filename).convert('YCbCr').to_array()
        hist = np.histogram(channels[:,:,0],bins=range(256))
        f = Figure(figsize=(5,5),dpi=100)
        ax = f.add_subplot(111)
        df = pd.DataFrame(hist[0])
        df.plot(kind='bar', legend=False, ax=ax, color=['b']*256)
        new_ticks=np.linspace(1,256,num=16).astype(np.int)
        ax.set_xticks(np.interp(new_ticks, df.index, np.arange(df.size)))
        ax.set_xticklabels(new_ticks)
        ax.set_xlabel('Intensity')
        ax.set_ylabel('Frequency')
        canvas = FigureCanvasTkAgg(f, frame)
        canvas.show()
        canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

customAnalytics = {'allyuvhist': YuvHistogramAnalytic()}
def loadAnalytics():
    global customAnalytics
    import pkg_resources
    for p in  pkg_resources.iter_entry_points("maskgen_analytics"):
        logging.getLogger('maskgen').info( 'load analytic  ' + p.name)
        customAnalytics[p.name] = p.load()()


class AnalsisViewDialog(tkSimpleDialog.Dialog):
    currentFileName = None

    analytic_frames = {}
    def __init__(self, parent, name, scenarioModel, nodes=None):
        self.scenarioModel= scenarioModel
        if nodes is not None:
            self.finalNodes =nodes
        else:
            self.finalNodes = self.scenarioModel.finalNodes()
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def load_analytic(self,event):
        analyticName = self.analytic.get()
        key = self.currentFileName + analyticName
        if key in self.analytic_frames:
            self.analytic_frames[key].tkraise()
        else:
            analysis_frame = Frame(self.image_frame)
            analysis_frame.grid(row=1,column=1,sticky="nsew")
            self.analytic_frames[key]=analysis_frame
            pick  =[analytic for analytic in customAnalytics.values() if analytic.screenName() == analyticName]
            if len(pick) > 0:
                pick[0].draw(analysis_frame,self.currentFileName)
                analysis_frame.tkraise()

    def load_image(self, event, initialize=False):
        node = self.item.get()
        im,filename = self.scenarioModel.getGraph().get_image(node)
        self.currentFileName = filename
        imResized = imageResizeRelative(im, (300, 300), im.size)
        self.photo = ImageTk.PhotoImage(imResized.toPIL())
        if initialize:
            self.c = Canvas(self.image_frame, width=300, height=300)
            self.image_on_canvas = self.c.create_image(0, 0, image=self.photo, anchor=NW)
        else:
            self.c.itemconfig(self.image_on_canvas, image=self.photo)
        first = None
        analytics = []
        for analytic in customAnalytics.values():
            sn =  analytic.screenName()
            if analytic.appliesTo(filename):
                if first is None:
                    first = sn
                analytics.append(sn)
        self.analyticBox.config(values=analytics)
        self.analytic.set(first if first else '')
        self.load_analytic(None)

    def body(self, master):
        import ttk
        self.item = StringVar()
        self.analytic = StringVar()
        row = 0
        self.image_frame = master
        self.item.set(self.finalNodes[0] if len(self.finalNodes) > 0 else '')
        optionsBox = ttk.Combobox(master,
                                       values=list(self.finalNodes),
                                       textvariable=self.item)
        self.analyticBox = ttk.Combobox(master,
                                  values=list(),
                                  textvariable=self.analytic)
        optionsBox.grid(row=row, column=0)
        self.analyticBox.grid(row=row, column=1)
        optionsBox.bind("<<ComboboxSelected>>", self.load_image)
        self.analyticBox.bind("<<ComboboxSelected>>", self.load_analytic)
        self.load_image(None,initialize=True)
        self.c.grid(row=1, column=0)





