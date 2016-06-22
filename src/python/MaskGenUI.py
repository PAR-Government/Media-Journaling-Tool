from Tkinter import *
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
from scenario_model import FileFinder,ProjectModel,Modification
from description_dialog import DescriptionCaptureDialog
from tool_set import imageResize

# this program creates a canvas and puts a single polygon on the canvas


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
    nodemenu = None
    edgemenu = None
    canvas = None

    def new(self):
       res = tkSimpleDialog.askstring("Project Name", "Name")
       if res is None or res == '':
         return
       self.scModel.startNew(res)
       self.master.title(res)
       self.drawState()
       self.canvas.update()
       self.processmenu.entryconfig(1,state='disabled')

    def open(self):
        val = tkFileDialog.askopenfilename(initialdir = self.scModel.filefinder.dir, title = "Select project file",filetypes = [("json files","*.json")])
        if(val != None and len(val)>0):
          self.scModel.load(val)
          self.drawState()
          self.canvas.update()
          if (self.scModel.start is not None):
             self.processmenu.entryconfig(1,state='normal')

    def add(self):
        val = tkFileDialog.askopenfilename(initialdir = self.scModel.filefinder.dir, title = "Select image file",filetypes = (("jpeg files","*.jpg"),("png files","*.png"),("all files","*.*")))
        if (val != None and len(val)> 0):
          place = self.scModel.start if self.scModel.end is None else self.scModel.end
          self.scModel.addImage(val)
          try:
            self.drawState()
            self.processmenu.entryconfig(1,state='normal')
            self.canvas.addNew()
          except IOError:
            tkMessageBox.showinfo("Error", "Failed to load image " + self.scModel.startImageName())

    def save(self):
       self.scModel.save()

    def saveas(self):
       val = tkFileDialog.asksaveasfile(initialdir = self.scModel.filefinder.dir, title = "Save As",filetypes = [("json files","*.json")])
       if (val is not None and len(val.name)>0):
         name = os.path.split(val.name[0:val.name.rfind('.')])[1]
         dir = os.path.split(val.name)[0]
         if (dir != os.path.abspath(self.scModel.filefinder.dir)):
            tkMessageBox.showwarning("Save As", "Cannot save to a different directory\n(%s)" % dir)
         else:
            self.scModel.saveas(val.name,name)
            self.master.title(name)
         val.close()
  
    def undo(self):
       self.scModel.undo()
       self.drawState()
       self.canvas.update()

    def next(self):
        file,im = self.scModel.scanNextImage()
        if (file is None): 
            return
        d = DescriptionCaptureDialog(self,im,self.myops,os.path.split(file)[1])
        if (d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            self.scModel.addNextImage(file,mod=d.description)
            self.drawState()
            self.canvas.add(self.scModel.start, self.scModel.end)

    def drawState(self):
        self.img1= ImageTk.PhotoImage(imageResize(self.scModel.startImage(),(250,250)))
        self.img2= ImageTk.PhotoImage(imageResize(self.scModel.nextImage(),(250,250)))
        self.img3= ImageTk.PhotoImage(imageResize(self.scModel.maskImage(),(250,250)))
        self.img1c.itemconfig(self.img1oc, image=self.img1)
        self.img2c.itemconfig(self.img2oc, image=self.img2)
        self.img3c.itemconfig(self.img3oc, image=self.img3)
        self.l1.config(text=self.scModel.startImageName())
        self.l2.config(text=self.scModel.nextImageName())

    def gquit(self, event):
        self.quit()

    def gopen(self, event):
        self.open()

    def gnew(self, event):
        self.new()

    def gsave(self, event):
        self.save()

    def gnext(self, next):
        self.next()

    def gundo(self, next):
        self.undo()

    def gadd(self, next):
        self.add()

    def connectto(self):
       self.drawState()
       self.canvas.connectto()

    def select(self):
       self.drawState()

    def remove(self):
       self.canvas.remove()
       self.drawState()

    def createWidgets(self):
        self.master.title("Untitled")

        menubar = Menu(self)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open",command=self.open, accelerator="Ctrl+O")
        filemenu.add_command(label="New",command=self.new, accelerator="Ctrl+N")
        filemenu.add_command(label="Save", command=self.save, accelerator="Ctrl+S")
        filemenu.add_command(label="Save As", command=self.saveas)
        filemenu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=filemenu)

        self.processmenu = Menu(menubar, tearoff=0)
        self.processmenu.add_command(label="Add", command=self.add, accelerator="Ctrl+A")
        self.processmenu.add_command(label="Next", command=self.next, accelerator="Ctrl+F", state='disabled')
        self.processmenu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+U")
        menubar.add_cascade(label="Process", menu=self.processmenu)
        self.master.config(menu=menubar)
        self.bind_all('<Control-q>',self.gquit)
        self.bind_all('<Control-o>',self.gopen)
        self.bind_all('<Control-s>',self.gsave)
        self.bind_all('<Control-a>',self.gadd)
        self.bind_all('<Control-n>',self.gnew)
        self.bind_all('<Control-f>',self.gnext)
        self.bind_all('<Control-u>',self.gundo)

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

        self.edgemenu = Menu(self.master,tearoff=0)
        self.edgemenu.add_command(label="Select", command=self.select)
        self.edgemenu.add_command(label="Remove", command=self.remove)

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
        mframe.grid(row=2,column=0,rowspan=1,columnspan=3, sticky=N+S+E+W)

    def graphCB(self, event, eventName):
       if eventName == 'rcNode':
          self.nodemenu.post(event.x_root,event.y_root)
       if eventName == 'rcEdge':
          self.edgemenu.post(event.x_root,event.y_root)
       if eventName == 'n':
           self.drawState()

    def __init__(self, filefinder,master=None, ops=[]):
        Frame.__init__(self, master)
        self.myops = ops
        self.filefinder = filefinder
        self.scModel = ProjectModel(filefinder,"Untitled")
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
   gui = MakeGenUI(filefinder=FileFinder(imgdir),master=root,ops=ops)
   gui.mainloop()

if __name__ == "__main__":
    sys.exit(main())

