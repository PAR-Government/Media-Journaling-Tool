from Tkinter import *
import Tkconstants, tkFileDialog, tkSimpleDialog
import tkMessageBox
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
from autocomplete import AutocompleteEntry 
import sys

from scenario_model import Description, Scenario

def alignShape(im,shape):
   z = np.zeros(shape)
   x = min(shape[0],im.shape[0])
   y = min(shape[1],im.shape[1])
   for d in range(min(shape[2],im.shape[2])):
      z[0:x,0:y,d] = im[0:x,0:y,d]
   return z

# this program creates a canvas and puts a single polygon on the canvas

class FileFinder:
    dir = '.'
    file = '.'
    
    def __init__(self, dirname):
      self.dir = dirname

    def setFile(self,filename):
        self.file = filename 

    def composeFileName(self, postFix):
        return self.file[0:self.file.rfind('.')] + postFix

    def findFiles(self, filterFunction):
        exp = os.path.split(self.file[0:self.file.rfind('.')])[1]
        set= [os.path.abspath(os.path.join(self.dir,filename)) for filename in os.listdir(self.dir) if (filename.startswith(exp)) and filterFunction(os.path.abspath(os.path.join(self.dir,filename)))]
        set.sort()
        return set

class ScenarioModel:
    items = list()
    descriptions = list()
    step = 0
    filefinder = None
    startImg = None
    nextImg = None

    def __init__(self, filefinder):
      self.filefinder = filefinder

    def setInitialImage(self, name):
       self.step = 0
       self.items = list()
       self.items.append(name)
       self.descriptions = list()
       self.filefinder.setFile(name)
       self.startImg = None
       self.nextImg = None
      
    def startImageName(self):
      return self.items[max(0,self.step-1)]
    
    def nextImageName(self):
      return self.items[self.step]

    def nextDescription(self):
      return self.descriptions[max(self.step - 1,0)]

    def createAndSaveScenario(self):
        scenario= Scenario(os.path.split(self.filefinder.file)[1], \
                        os.path.split(self.nextImageName())[1], \
                        self.descriptions)
        with open(self.filefinder.composeFileName('.json'), 'w') as f:
          f.write(scenario.toJson())
        return scenario

    def createMask(self):
        si = np.array(self.startImg)
        ni = alignShape(np.array(self.nextImg),si.shape)
        dst = np.abs(si-ni).astype('uint8')
        gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)
        nin = self.filefinder.composeFileName('_mask_' + str(self.step) + '.png')
        self.descriptions.append(Description('change',os.path.split(nin)[1]))
        cv2.imwrite(nin,thresh1)
        return Image.fromarray(thresh1)

    def isMask(self, name):
      return name.rfind('_mask_')>0

    def startImage(self):
        if (self.startImg == None):
            self.startImg = Image.open(self.startImageName())
        return self.startImg

    def nextImage(self):
        if (self.nextImg == None):
            self.nextImg = Image.open(self.nextImageName())
        return self.nextImg

    def scanNextImage(self):
      suffix =   self.startImageName()[self.startImageName().rfind('.'):]
      self.startImg = self.nextImg
      self.nextImg = None

      def filterF (file):
         return file not in self.items and not(self.isMask(file)) and file.endswith(suffix)

      for file in self.filefinder.findFiles(filterF):
         self.items.append(file)
         self.step+=1
         return file
      return self.items[self.step]
    
ops = ['insert', 'splice',  'blur', 'resize', 'color', 'sharpen', 'compress', 'mosaic']

class DescriptionCaptureDialog(tkSimpleDialog.Dialog):

   description = None

   def __init__(self, parent, description):
      self.description = description
      tkSimpleDialog.Dialog.__init__(self, parent, "Operation Description")

   def body(self, master):
      Label(master, text="Operation:").grid(row=0)
      Label(master, text="Description:").grid(row=1)

      self.e1 = AutocompleteEntry(master,ops)
      self.e2 = Entry(master)

      self.e1.grid(row=0, column=1)
      self.e2.grid(row=1, column=1)
      return self.e1 # initial focus

   def apply(self):
       first = self.e1.get()
       second = self.e2.get()
       self.description.operationName = first
       self.description.additionalInfo = second
       print first, second # or something

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

    def printit(self):
        print "hi"

    def open(self):
        val = tkFileDialog.askopenfilename(initialdir = self.scModel.filefinder.dir, title = "Select image file",filetypes = (("jpeg files","*.jpg"),("png files","*.png"),("all files","*.*")))
        if (val != None and len(val)> 0):
          self.scModel.setInitialImage(val)
          try:
            self.img1 = ImageTk.PhotoImage(Image.open(self.scModel.startImageName()))
            self.img1c.itemconfig(self.img1oc, image= self.img1)
            self.processmenu.entryconfig(0,state='normal')
          except IOError:
            tkMessageBox.showinfo("Error", "Failed to load image " + self.scModel.startImageName())

    def stop(self):
        self.processmenu.entryconfig(1,state='disabled')
        self.processmenu.entryconfig(0,state='disabled')
        self.scModel.createAndSaveScenario()
        self.img1= ImageTk.PhotoImage(Image.fromarray(np.zeros((500,500,3)).astype('uint8')))
        self.img2= ImageTk.PhotoImage(Image.fromarray(np.zeros((500,500,3)).astype('uint8')))
        self.img3= ImageTk.PhotoImage(Image.fromarray(np.zeros((500,500,3)).astype('uint8')))
        self.img1c.itemconfig(self.img1oc, image=self.img1)
        self.img2c.itemconfig(self.img2oc, image=self.img2)
        self.img3c.itemconfig(self.img3oc, image=self.img3)

    def next(self):
        self.processmenu.entryconfig(1,state='normal')
        self.scModel.scanNextImage()
        self.img1= ImageTk.PhotoImage(self.scModel.startImage())
        self.img2= ImageTk.PhotoImage(self.scModel.nextImage())
        self.img3= ImageTk.PhotoImage(self.scModel.createMask())
        self.img1c.itemconfig(self.img1oc, image=self.img1)
        self.img2c.itemconfig(self.img2oc, image=self.img2)
        self.img3c.itemconfig(self.img3oc, image=self.img3)
        self.l1.config(text=os.path.split(self.scModel.startImageName())[1])
        self.l2.config(text=os.path.split(self.scModel.nextImageName())[1])
        self.l3.config(text=self.scModel.nextDescription().maskFileName)
        d = DescriptionCaptureDialog(self.master, self.scModel.nextDescription())
        print self.scModel.nextDescription().operationName
        
    def gquit(self, event):
        self.quit()

    def gopen(self, event):
        self.open()

    def gnext(self, next):
        if (self.processmenu.entrycget(0,'state')=="normal"):
          self.next()

    def gfinish(self, next):
        if (self.processmenu.entrycget(1,'state')=="normal"):
          self.stop()

    def createWidgets(self):
        self.master.title("Mask Generator")

        menubar = Menu(self)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open",command=self.open, accelerator="Ctrl+O")
        filemenu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=filemenu)

        self.processmenu = Menu(menubar, tearoff=0)
        self.processmenu.add_command(label="Next", command=self.next, accelerator="Ctrl+N", state='disabled')
        self.processmenu.add_command(label="Finish", command=self.stop, accelerator="Ctrl+F", state='disabled')
        menubar.add_cascade(label="Process", menu=self.processmenu)
        self.master.config(menu=menubar)
        self.bind_all('<Control-q>',self.gquit)
        self.bind_all('<Control-o>',self.gopen)
        self.bind_all('<Control-n>',self.gnext)
        self.bind_all('<Control-f>',self.gfinish)

        self.grid()
        self.master.rowconfigure(0,weight=1)
        self.master.rowconfigure(1,weight=1)
        self.master.rowconfigure(2,weight=1)
        self.master.columnconfigure(0,weight=1)
        self.master.columnconfigure(1,weight=1)
        self.master.columnconfigure(2,weight=1)

        img1f = img2f = img3f = self.master

        self.img1c = Canvas(img1f, width=500, height=500)
        self.img1c.grid(row = 0, column = 0)
        self.img2c = Canvas(img2f, width=500, height=500)
        self.img2c.grid(row = 0, column = 1)
        self.img3c = Canvas(img3f, width=500, height=500)
        self.img3c.grid(row = 0, column = 2)

        self.img1 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "white"))
        self.img1oc = self.img1c.create_image(250,250,image=self.img1, tag='img1')
        self.img2 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "white"))
        self.img2oc = self.img2c.create_image(250,250,image=self.img2, tag='img2')
        self.img3 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "white"))
        self.img3oc = self.img3c.create_image(250,250,image=self.img3, tag='img3')

        self.l1 = Label(img1f, text="") 
        self.l1.grid(row=1,column=0)
        self.l2 = Label(img2f, text="")
        self.l2.grid(row=1,column=1)
        self.l3 = Label(img3f, text="")
        self.l3.grid(row=1,column=2)

    def __init__(self, filefinder,master=None):
        Frame.__init__(self, master)
        self.createWidgets()
        self.filefinder = filefinder
        self.scModel = ScenarioModel(filefinder)

def main(argv=None):
   if (argv is None):
       argv = sys.argv
   imgdir = '.'
   if (len(argv)>0 and os.path.isdir(argv[1])):
      imgdir = argv[1]
   root= Tk()
   gui = MakeGenUI(filefinder=FileFinder(imgdir),master=root)
   gui.mainloop()

if __name__ == "__main__":
    sys.exit(main())

