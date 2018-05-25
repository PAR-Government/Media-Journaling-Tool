# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import Tkinter as tk
import collections
import tkSimpleDialog

import matplotlib
from PIL import ImageTk
from maskgen.analytics.dctAnalytic import *
from maskgen.image_wrap import openImageFile
from maskgen.tool_set import fileType
from maskgen.tool_set import imageResizeRelative

matplotlib.use("TkAgg")
import  tkFileDialog
from maskgen.tool_set import imageResize,fixTransparency


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
        :return: the object that is viewed
        """
        pass

    def export(self, object, exportfilename):
        """
        Export the result to an image file.
        :param object  the object returned from draw
        :param exportfilename - the name of the file to export the analysis
        """
        pass


class PCAAnalytic:

    def screenName(self):
        return "PCA Analysis"

    def appliesTo(self, filename):
        return fileType(filename) == 'image'

    def export(self, imtuple, exportfilename):
        imtuple[0].save(exportfilename)

    def draw(self,frame, filename):
        from maskgen.analytics.analysis import pca
        im = pca(openImageFile(filename))
        photo = ImageTk.PhotoImage(fixTransparency(imageResize(im, (400, 400))).toPIL())
        canvas = Canvas(frame, width=400, height=400)
        canvas.create_image(0, 0, image=photo,anchor=NW)
        canvas.grid(row=0, column=0)
        return (im,photo)

class ElaAnalytic:

    def screenName(self):
        return "Error Level Analysis"

    def appliesTo(self, filename):
        return fileType(filename) == 'image'

    def export(self, imtuple, exportfilename):
        imtuple[0].save(exportfilename)

    def draw(self,frame, filename):
        from maskgen.analytics.analysis import ela
        im = ela(openImageFile(filename))
        photo = ImageTk.PhotoImage(fixTransparency(imageResize(im, (400, 400))).toPIL())
        canvas = Canvas(frame, width=400, height=400)
        canvas.create_image(0, 0, image=photo,anchor=NW)
        canvas.grid(row=0, column=0)
        return (im,photo)


class YuvHistogramAnalytic:

    def screenName(self):
        return "Luminance Histogram"

    def appliesTo(self, filename):
        return fileType(filename) == 'image'

    def export(self, figure, exportfilename):
        figure.savefig(exportfilename)

    def _get_figure(self, filename):
        from matplotlib.figure import Figure
        import pandas as pd
        channels = openImageFile(filename).convert('YCbCr').to_array()
        hist = np.histogram(channels[:, :, 0], bins=range(256))
        f = Figure(figsize=(5, 5), dpi=100)
        ax = f.add_subplot(111)
        df = pd.DataFrame(hist[0])
        df.plot(kind='bar', legend=False, ax=ax, color=['b'] * 256)
        new_ticks = np.linspace(1, 256, num=16).astype(np.int)
        ax.set_xticks(np.interp(new_ticks, df.index, np.arange(df.size)))
        ax.set_xticklabels(new_ticks)
        ax.set_xlabel('Intensity')
        ax.set_ylabel('Frequency')
        return f

    def draw(self,frame, filename):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        f = self._get_figure(filename)
        canvas = FigureCanvasTkAgg(f, frame)
        canvas.show()
        canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        return f

# Order YuvHistogramAnalytic first, as it is relatively lightweight
customAnalytics = [('allyuvhist', YuvHistogramAnalytic()),
                   ('ela',ElaAnalytic()),
                   ('pca', PCAAnalytic()),
                   ('dcthist', DCTView()),
                   ('fftdcthist', FFT_DCTView())]
customAnalytics = collections.OrderedDict(customAnalytics)

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
        self.mappings = {}
        if nodes is not None:
            self.finalNodes =nodes
        else:
            self.finalNodes = self.scenarioModel.finalNodes()
        self.mappings = {self.scenarioModel.getFileName(node):node for node in self.finalNodes}
        self.analytic_frames = {}
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def load_analytic(self,event):
        import os
        analyticName = self.analytic.get()
        if not os.path.exists(self.currentFileName):
            return
        key = self.currentFileName + analyticName
        if key in self.analytic_frames:
            self.analytic_frames[key][0].tkraise()
        else:
            analysis_frame = Frame(self.image_frame)
            analysis_frame.grid(row=1,column=1,sticky="nsew")
            pick  =[analytic for analytic in customAnalytics.values() if analytic.screenName() == analyticName]
            if len(pick) > 0:
                self.analytic_frames[key] = (analysis_frame,pick[0].draw(analysis_frame,self.currentFileName))
                analysis_frame.tkraise()

    def load_image(self, event, initialize=False):
        filename = self.item.get()
        im,filename = self.scenarioModel.getGraph().get_image(self.mappings[filename])
        self.currentFileName = filename
        imResized = imageResizeRelative(im, (400, 400), im.size)
        self.photo = ImageTk.PhotoImage(imResized.toPIL())
        if initialize:
            self.c = Canvas(self.image_frame, width=400, height=400)
            self.image_on_canvas = self.c.create_image(0, 0, image=self.photo, anchor=NW)
            self.c.grid(row=1, column=0)
        else:
            self.c.itemconfig(self.image_on_canvas, image=self.photo)
        analytics = []
        for analytic in customAnalytics.values():
            sn =  analytic.screenName()
            if analytic.appliesTo(filename):
                analytics.append(sn)
        self.analyticBox.config(values=analytics)
        self.analytic.set(self.first.screenName())
        self.load_analytic(None)

    def body(self, master):
        import ttk
        self.item = StringVar()
        self.analytic = StringVar()
        self.first = customAnalytics[customAnalytics.keys()[0]]
        self.analytic.set(self.first.screenName())
        row = 0
        self.image_frame = master
        self.item.set(self.scenarioModel.getFileName(self.finalNodes[0]) if len(self.finalNodes) > 0 else '')
        optionsBox = ttk.Combobox(master,
                                       values=self.mappings.keys(),
                                       textvariable=self.item,
                                  width=60)
        self.analyticBox = ttk.Combobox(master,
                                  values=list(),
                                  textvariable=self.analytic)
        optionsBox.grid(row=row, column=0)
        self.analyticBox.grid(row=row, column=1)
        optionsBox.bind("<<ComboboxSelected>>", self.load_image)
        self.analyticBox.bind("<<ComboboxSelected>>", self.load_analytic)
        self.load_image(None,initialize=True)

    def export(self):
        analyticName = self.analytic.get()
        frame_key = self.currentFileName + analyticName
        if frame_key in self.analytic_frames:
            pick = [analytic for analytic in customAnalytics.values() if analytic.screenName() == analyticName]
            if len(pick) > 0:
                f = tkFileDialog.asksaveasfilename(initialdir='.', title=analyticName,
                                               defaultextension='.png')
                if f is not None:
                    pick[0].export(self.analytic_frames[frame_key][1],f)


    def buttonbox(self):
        box = Frame(self)
        self.okButton = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        self.okButton.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Export", width=10, command=self.export)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Escape>", self.ok)
        box.pack(side=BOTTOM)



