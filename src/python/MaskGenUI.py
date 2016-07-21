from Tkinter import *
import plugins
from group_filter import GroupFilter,GroupFilterLoader
import Tkconstants, tkFileDialog, tkSimpleDialog
import tkMessageBox
from PIL import Image, ImageTk
import numpy as np
import os
import sys
import argparse
import mask_operation
from mask_frames import HistoryFrame 
import ttk
from graph_canvas import MaskGraphCanvas
from scenario_model import ProjectModel,Modification,findProject
from description_dialog import DescriptionCaptureDialog,DescriptionViewDialog,FilterCaptureDialog,FilterGroupCaptureDialog
from tool_set import imageResizeRelative,fixTransparency
from software_loader import Software
from group_manager import GroupManagerDialog

# this program creates a canvas and puts a single polygon on the canvas

defaultypes = [("jpeg files","*.jpg"),("png files","*.png"),("tiff files","*.tiff"),("all files","*.*")]
defaultops = ['insert', 'splice',  'blur', 'resize', 'color', 'sharpen', 'compress', 'mosaic']

class MakeGenUI(Frame):

    img1 = None
    img2 = None
    img3 = None
    img1c = None
    img2c = None
    img3c = None
    img1oc = None
    img2oc = None
    img3oc = None
    scModel = None
    l1 = None
    l2 = None
    l3 = None
    processmenu = None
    myops = {}
    mypluginops = {}
    nodemenu = None
    edgemenu = None
    filteredgemenu = None
    canvas = None
   
    gfl = GroupFilterLoader()

    def _check_dir(self,pathinfo):
         dir = os.path.abspath(os.path.split(pathinfo)[0])
         set = [filename for filename in os.listdir(dir) if filename.endswith('.json')]
         return not len(set)>0

    def setSelectState(self, state):
       self.processmenu.entryconfig(1,state=state)
       self.processmenu.entryconfig(2,state=state)
       self.processmenu.entryconfig(3,state=state)
       self.processmenu.entryconfig(4,state=state)
       self.processmenu.entryconfig(5,state=state)

    def new(self):
       val = tkFileDialog.asksaveasfilename(initialdir = self.scModel.get_dir(), title = "Select new project file",filetypes = [("json files","*.json")])
       if val is None or val== '':
         return
       if (not self._check_dir(val)):
         tkMessageBox.showinfo("Error", "Directory already associated with a project")
         return
       self.scModel.startNew(val)
       if self.scModel.getProjectData('typespref') is None:
          self.scModel.setProjectData('typespref',defaultypes)
       self.master.title(val)
       self.drawState()
       self.canvas.update()
       self.setSelectState('disabled')
 
    def about(self):
        tkMessageBox.showinfo('About','Version: ' + self.scModel.getVersion())

    def open(self):
        val = tkFileDialog.askopenfilename(initialdir = self.scModel.get_dir(), title = "Select project file",filetypes = [("json files","*.json")])
        if (val != None and len(val)>0):
          self.scModel.load(val)
          if self.scModel.getProjectData('typespref') is None:
              self.scModel.setProjectData('typespref',defaultypes)
          self.master.title(val)
          self.drawState()
          self.canvas.update()
          if (self.scModel.start is not None):
             self.setSelectState('normal')

    def add(self):
        val = tkFileDialog.askopenfilenames(initialdir = self.scModel.get_dir(), title = "Select image file(s)",filetypes =self.getFileTypes())
        if (val != None and len(val)> 0):
          self.updateFileTypes(val[0])
          try:
            self.canvas.addNew([self.scModel.addImage(f) for f in val])
            self.processmenu.entryconfig(6,state='normal')
          except IOError:
            tkMessageBox.showinfo("Error", "Failed to load image " + self.scModel.startImageName())
          self.setSelectState('normal')

    def save(self):
       self.scModel.save()

    def saveas(self):
       val = tkFileDialog.asksaveasfile(initialdir = self.scModel.get_dir(), title = "Save As",filetypes = [("json files","*.json")])
       if (val is not None and len(val.name)>0):
         dir = os.path.abspath(os.path.split(val.name)[0])
         if (dir == os.path.abspath(self.scModel.get_dir())):
            tkMessageBox.showwarning("Save As", "Cannot save to the same directory\n(%s)" % dir)
         else:
            self.scModel.saveas(val.name)
            self.master.title(val.name)
         val.close()

    def export(self):
       val = tkFileDialog.askdirectory(initialdir = '.',title = "Export To Directory")
       if (val is not None and len(val)>0):
         self.scModel.export(val)
         tkMessageBox.showinfo("Export", "Complete")
  
    def undo(self):
       self.scModel.undo()
       self.drawState()
       self.canvas.update()
       self.processmenu.entryconfig(6,state='disabled')
       self.setSelectState('disabled')

    def updateFileTypes(self, filename):
        if filename is None or len(filename) == 0:
           return

        suffix = filename[filename.rfind('.'):]
        place=0
        top=None
        allPlace=0
        prefs = self.getFileTypes()
        for pref in prefs:
           if pref[1] == '*.*':
             allPlace = place  
           if pref[1] == '*' + suffix:
             top=pref
             break
           place+=1
        if top is not None and place>0:
           prefs[place]=prefs[0]
           prefs[0]=top
           self.scModel.setProjectData('typespref',prefs)
        elif top is None and allPlace > 0:
           top = prefs[0]
           prefs[0] = prefs[allPlace]
           prefs[allPlace] = top

    def getFileTypes(self):
        return [tuple(x) for x in self.scModel.getProjectData('typespref')]
            
    def nextadd(self):
        val = tkFileDialog.askopenfilename(initialdir = self.scModel.get_dir(), title = "Select image file",filetypes = self.getFileTypes())
        self.updateFileTypes(val)
        file,im = self.scModel.openImage(val)
        if (file is None or file == ''): 
            return
        d = DescriptionCaptureDialog(self,self.scModel.get_dir(),im,self.myops,os.path.split(file)[1])
        if (d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            msg = self.scModel.addNextImage(file,im,mod=d.description,software=d.getSoftware())
            if msg is not None:
              tkMessageBox.showwarning("Auto Connect",msg)
            else:
              self.drawState()
              self.canvas.add(self.scModel.start, self.scModel.end)
              self.processmenu.entryconfig(6,state='normal')

    def nextauto(self):
        im,filename = self.scModel.scanNextImage()
        if (filename is None): 
            return
        d = DescriptionCaptureDialog(self,self.scModel.get_dir(),im,self.myops,os.path.split(filename)[1])
        if (d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            msg = self.scModel.addNextImage(filename,im,mod=d.description,software=d.getSoftware())
            if msg is not None:
              tkMessageBox.showwarning("Auto Connect",msg)
            else:
              self.drawState()
              self.canvas.add(self.scModel.start, self.scModel.end)
              self.processmenu.entryconfig(6,state='normal')

    def resolvePluginValues(self,args):
      result = {}
      for k,v in args.iteritems():
       if k == 'donor':
          result[k] = self.scModel.getImageAndName(v)
       else:
          result[k] = v
      result['sendNotifications'] = False
      return result

    def nextfilter(self):
        im,filename = self.scModel.currentImage()
        if (im is None): 
            return
        d = FilterCaptureDialog(self,self.scModel.get_dir(),im,plugins.getOperations(),os.path.split(filename)[1], self.scModel)
        if d.optocall is not None:
            msg = self.scModel.imageFromPlugin(d.optocall,im,filename,**self.resolvePluginValues(d.argvalues))
            if msg is not None:
              tkMessageBox.showwarning("Next Filter",msg)
            else:
              self.drawState()
              self.canvas.add(self.scModel.start, self.scModel.end)
              if 'donor' in d.argvalues:
                end = self.scModel.end
                self.scModel.selectImage(d.argvalues['donor'])
                self.scModel.connect(end)
                self.canvas.add(self.scModel.start, self.scModel.end)
              self.processmenu.entryconfig(6,state='normal')

    def nextfiltergroup(self):
        im,filename = self.scModel.currentImage()
        if (im is None): 
            return
        if len(self.gfl.getGroupNames()) == 0:
            tkMessageBox.showwarning("Next Group Filter","No groups found")
            return
        d = FilterGroupCaptureDialog(self,im,os.path.split(filename)[1])
        if d.getGroup() is not None:
            start = self.scModel.startImageName()
            end = None
            ok = False
            for filter in self.gfl.getGroup(d.getGroup()).filters:
               msg = self.scModel.imageFromPlugin(filter,im,filename)
               if msg is not None:
                 tkMessageBox.showwarning("Next Filter",msg)
                 break
               ok = True
               self.canvas.add(self.scModel.start, self.scModel.end)
               end = self.scModel.nextImageName()
               # reset back to the start image
               self.scModel.selectImage(start)
            #select the last one completed
            self.scModel.select((start,end))
            self.drawState()
            if ok:
               self.processmenu.entryconfig(6,state='normal')

    def nextfiltergroupsequence(self):
        im,filename = self.scModel.currentImage()
        if (im is None): 
            return
        if len(self.gfl.getGroupNames()) == 0:
            tkMessageBox.showwarning("Next Group Filter","No groups found")
            return
        d = FilterGroupCaptureDialog(self,im,os.path.split(filename)[1])
        if d.getGroup() is not None:
            for filter in self.gfl.getGroup(d.getGroup()).filters:
               msg = self.scModel.imageFromPlugin(filter,im,filename)
               if msg is not None:
                 tkMessageBox.showwarning("Next Filter",msg)
                 break
               self.canvas.add(self.scModel.start, self.scModel.end)
               im,filename = self.scModel.getImageAndName(self.scModel.end)
            self.drawState()
            self.processmenu.entryconfig(6,state='normal')

    def drawState(self):
        sim = self.scModel.startImage()
        nim = self.scModel.nextImage()
        self.img1= ImageTk.PhotoImage(fixTransparency(imageResizeRelative(sim,(250,250),nim.size)))
        self.img2= ImageTk.PhotoImage(fixTransparency(imageResizeRelative(nim,(250,250),sim.size)))
        self.img3= ImageTk.PhotoImage(imageResizeRelative(self.scModel.maskImage(),(250,250),nim.size))
        self.img1c.itemconfig(self.img1oc, image=self.img1)
        self.img2c.itemconfig(self.img2oc, image=self.img2)
        self.img3c.itemconfig(self.img3oc, image=self.img3)
        self.l1.config(text=self.scModel.startImageName())
        self.l2.config(text=self.scModel.nextImageName())
        self.maskvar.set(self.scModel.maskStats())

    def groupmanager(self):
        d = GroupManagerDialog(self)

    def quit(self):
        self.save()
        Frame.quit(self)

    def gquit(self, event):
        self.quit()

    def gopen(self, event):
        self.open()

    def gnew(self, event):
        self.new()

    def gsave(self, event):
        self.save()

    def gnextauto(self, next):
        self.nextauto()

    def gnextadd(self, next):
        self.nextadd()

    def gnextfilter(self, next):
        self.nextfilter()

    def gundo(self, next):
        self.undo()

    def gadd(self, next):
        self.add()

    def compareto(self):
      self.canvas.compareto()

    def connectto(self):
       self.drawState()
       self.canvas.connectto()
       self.processmenu.entryconfig(6,state='normal')

    def exportpath(self):
       val = tkFileDialog.askdirectory(initialdir = '.',title = "Export " + self.scModel.startImageName() + " To Directory")
       if (val is not None and len(val)>0):
         self.scModel.export_path(val)
         tkMessageBox.showinfo("Export", "Complete")

    def select(self):
       self.drawState()
       self.setSelectState('normal')

    def connectEvent(self,modification):
        if (modification.operationName == 'PasteSplice'):
           tkMessageBox.showinfo("Splice Requirement", "A splice operation should be accompanied by a donor image.")

    def remove(self):
       self.canvas.remove()
       self.drawState()
       self.processmenu.entryconfig(6,state='normal')
       self.setSelectState('disabled')

    def edit(self):
       im,filename = self.scModel.currentImage()
       if (im is None): 
            return
       d = DescriptionCaptureDialog(self,self.scModel.get_dir(),im,self.myops,os.path.split(filename)[1],description=self.scModel.getDescription(),software=self.scModel.getSoftware())
       if (d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
           self.scModel.update_edge(d.description,software=d.getSoftware())
       self.drawState()

    def view(self):
       im,filename = self.scModel.currentImage()
       if (im is None): 
            return
       d = DescriptionViewDialog(self,im,self.myops,os.path.split(filename)[1],description=self.scModel.getDescription(),software=self.scModel.getSoftware(), exifdiff=self.scModel.getExifDiff())

    def createWidgets(self):
        self.master.title(os.path.join(self.scModel.get_dir(),self.scModel.getName()))

        menubar = Menu(self)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="About",command=self.about)
        filemenu.add_command(label="Open",command=self.open, accelerator="Ctrl+O")
        filemenu.add_command(label="New",command=self.new, accelerator="Ctrl+N")
        filemenu.add_command(label="Save", command=self.save, accelerator="Ctrl+S")
        filemenu.add_command(label="Save As", command=self.saveas)
        filemenu.add_command(label="Export", command=self.export, accelerator="Ctrl+E")
        filemenu.add_command(label="Group Manager", command=self.groupmanager)
        filemenu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=filemenu)

        self.processmenu = Menu(menubar, tearoff=0)
        self.processmenu.add_command(label="Add", command=self.add, accelerator="Ctrl+A")
        self.processmenu.add_command(label="Next w/Auto Pick", command=self.nextauto, accelerator="Ctrl+P", state='disabled')
        self.processmenu.add_command(label="Next w/Add", command=self.nextadd, accelerator="Ctrl+L", state='disabled')
        self.processmenu.add_command(label="Next w/Filter", command=self.nextfilter, accelerator="Ctrl+F", state='disabled')
        self.processmenu.add_command(label="Next w/Filter Group", command=self.nextfiltergroup, state='disabled')
        self.processmenu.add_command(label="Next w/Filter Sequence", command=self.nextfiltergroupsequence, state='disabled')
        self.processmenu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z",state='disabled')
        menubar.add_cascade(label="Process", menu=self.processmenu)
        self.master.config(menu=menubar)
        self.bind_all('<Control-q>',self.gquit)
        self.bind_all('<Control-o>',self.gopen)
        self.bind_all('<Control-s>',self.gsave)
        self.bind_all('<Control-a>',self.gadd)
        self.bind_all('<Control-n>',self.gnew)
        self.bind_all('<Control-p>',self.gnextauto)
        self.bind_all('<Control-l>',self.gnextadd)
        self.bind_all('<Control-f>',self.gnextfilter)
        self.bind_all('<Control-z>',self.gundo)

        self.grid()
        self.master.rowconfigure(0,weight=1)
        self.master.rowconfigure(1,weight=1)
        self.master.rowconfigure(2,weight=1)
        self.master.rowconfigure(3,weight=1)
        self.master.columnconfigure(0,weight=1)
        self.master.columnconfigure(1,weight=1)
        self.master.columnconfigure(2,weight=1)

        img1f = img2f = img3f = self.master

        self.img1c = Canvas(img1f, width=256, height=256)
        self.img1c.grid(row = 1, column = 0)
        self.img2c = Canvas(img2f, width=256, height=256)
        self.img2c.grid(row = 1, column = 1)
        self.img3c = Canvas(img3f, width=256, height=256)
        self.img3c.grid(row = 1, column = 2)

        self.img1 = ImageTk.PhotoImage(Image.new("RGB", (250, 250), "black"))
        self.img1oc = self.img1c.create_image(125,125,image=self.img1, tag='img1')
        self.img2 = ImageTk.PhotoImage(Image.new("RGB", (250, 250), "black"))
        self.img2oc = self.img2c.create_image(125,125,image=self.img2, tag='img2')
        self.img3 = ImageTk.PhotoImage(Image.new("RGB", (250, 250), "black"))
        self.img3oc = self.img3c.create_image(125,125,image=self.img3, tag='img3')

        self.l1 = Label(img1f, text="") 
        self.l1.grid(row=0,column=0)
        self.l2 = Label(img2f, text="")
        self.l2.grid(row=0,column=1)
        self.l3 = Label(img3f, text="")
        self.l3.grid(row=0,column=2)

        self.nodemenu = Menu(self.master,tearoff=0)
        self.nodemenu.add_command(label="Select", command=self.select)
        self.nodemenu.add_command(label="Remove", command=self.remove)
        self.nodemenu.add_command(label="Connect To", command=self.connectto)
        self.nodemenu.add_command(label="Export", command=self.exportpath)
        self.nodemenu.add_command(label="Compare To", command=self.compareto)

        self.edgemenu = Menu(self.master,tearoff=0)
        self.edgemenu.add_command(label="Select", command=self.select)
        self.edgemenu.add_command(label="Remove", command=self.remove)
        self.edgemenu.add_command(label="Edit", command=self.edit)
        self.edgemenu.add_command(label="Inspect", command=self.view)

        self.filteredgemenu = Menu(self.master,tearoff=0)
        self.filteredgemenu.add_command(label="Select", command=self.select)
        self.filteredgemenu.add_command(label="Remove", command=self.remove)
        self.filteredgemenu.add_command(label="Inspect", command=self.view)

        iframe = Frame(self.master, bd=2, relief=SUNKEN)
        iframe.grid_rowconfigure(0, weight=1)
        iframe.grid_columnconfigure(0, weight=1)
        self.maskvar = StringVar()
        Label(iframe, textvariable=self.maskvar).grid(row=0, sticky=W)
        iframe.grid(row=2,column=0,rowspan=1,columnspan=3, sticky=N+S+E+W)

        mframe = Frame(self.master, bd=2, relief=SUNKEN)
        mframe.grid_rowconfigure(0, weight=1)
        mframe.grid_columnconfigure(0, weight=1)
        self.vscrollbar = Scrollbar(mframe, orient=VERTICAL)
        self.hscrollbar = Scrollbar(mframe, orient=HORIZONTAL)
        self.vscrollbar.grid(row=0, column=1, sticky=N+S)
        self.hscrollbar.grid(row=1, column=0, sticky=E+W)
        self.canvas = MaskGraphCanvas(mframe,self.scModel,self.graphCB,self.myops, width=768, height=512, scrollregion=(0, 0, 4000, 4000), yscrollcommand=self.vscrollbar.set,xscrollcommand=self.hscrollbar.set)
        self.canvas.grid(row=0, column=0,sticky=N+S+E+W)
        self.vscrollbar.config(command=self.canvas.yview)
        self.hscrollbar.config(command=self.canvas.xview)
        mframe.grid(row=3,column=0,rowspan=1,columnspan=3, sticky=N+S+E+W)

        if (self.scModel.start is not None):
            self.setSelectState('normal')
            self.drawState()

    def graphCB(self, event, eventName):
       if eventName == 'rcNode':
          self.nodemenu.post(event.x_root,event.y_root)
       elif eventName == 'rcEdge':
          self.edgemenu.post(event.x_root,event.y_root)
       elif eventName == 'rcNonEditEdge':
          self.filteredgemenu.post(event.x_root,event.y_root)
       elif eventName == 'n':
           self.drawState()

    def __init__(self,dir,master=None, ops=[],pluginops={}):
        Frame.__init__(self, master)
#        master.wm_attributes("-transparent", True)
        self.myops = ops
        self.mypluginops = pluginops
        self.scModel = ProjectModel(findProject(dir), notify=self.connectEvent)
        if self.scModel.getProjectData('typespref') is None:
            self.scModel.setProjectData('typespref',defaultypes)
        self.createWidgets()



def main(argv=None):
   if (argv is None):
       argv = sys.argv

   parser = argparse.ArgumentParser(description='')
   parser.add_argument('imagedir', help='image directory')
   parser.add_argument('--ops', help="operations list file")
   imgdir = '.'
   argv = argv[1:]
   args = parser.parse_args(argv)
   if args.imagedir is not None:
       imgdir = args.imagedir
   if args.ops is not None:
       ops = mask_operation.loadOperations(args.ops)
   else:
       ops = defaultops
   root= Tk()

   gui = MakeGenUI(imgdir,master=root,ops=ops,pluginops=plugins.loadPlugins())
   gui.mainloop()

if __name__ == "__main__":
    sys.exit(main())

