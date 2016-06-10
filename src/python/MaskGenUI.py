from Tkinter import *
import Tkconstants, tkFileDialog, tkSimpleDialog
import tkMessageBox
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
from autocomplete import AutocompleteEntryWithList 
from autocomplete_it import AutocompleteEntryInText
import sys
import argparse
import mask_operation
from mask_frames import HistoryFrame 
import ttk

from scenario_model import Modification, Scenario

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
    images = list()
    modifications = list()
    step = 0
    filefinder = None

    def __init__(self, filefinder):
      self.filefinder = filefinder

    def setInitialImage(self, name):
       self.step = 0
       self.items = list()
       self.items.append(name)
       self.images.append(Image.open(name))
       self.modifications = list()
       self.filefinder.setFile(name)
      
    def startImageName(self):
      return self.items[max(0,self.step-1)]
    
    def nextImageName(self):
      return self.items[self.step]

    def nextModification(self):
      return self.modifications[max(self.step - 1,0)]

    def createAndSaveScenario(self):
        scenario= Scenario(os.path.split(self.filefinder.file)[1], \
                        os.path.split(self.nextImageName())[1], \
                        self.modifications)
        with open(self.filefinder.composeFileName('.json'), 'w') as f:
          f.write(scenario.toJson())
        return scenario

    def startImage(self):
       return self.images[max(0,self.step-1)]

    def nextImage(self):
      return self.images[self.step]

    def createMask(self):
        si = np.array(self.startImage())
        ni = alignShape(np.array(self.nextImage()),si.shape)
        dst = np.abs(si-ni).astype('uint8')
        gray_image = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        ret,thresh1 = cv2.threshold(gray_image,1,255,cv2.THRESH_BINARY)

        ni2 = np.array(self.nextImage())
        si2 = alignShape(np.array(self.startImage()),ni2.shape)
        dst2 = np.abs(ni2-si2).astype('uint8')
        gray_image2 = cv2.cvtColor(dst2, cv2.COLOR_BGR2GRAY)
        ret,thresh2 = cv2.threshold(gray_image2,1,255,cv2.THRESH_BINARY)

#        intersect = cv2.bitwise_and(thresh1,thresh1,mask = thresh2)
#        if (np.max(intersect)>0):
#          thresh1 = intersect
        nin = self.filefinder.composeFileName('_mask_' + str(self.step) + '.png')
        cv2.imwrite(nin,thresh1)
        return Image.fromarray(thresh1)

    def revertToStep(self, maskid):
       fpos = [i for i in range(len(self.modifications)) if self.modifications[i].maskFileName==maskid]
       if (len(fpos)> 0):
         pos = fpos[0]+1
         self.modifications = self.modifications[0:pos]
         self.items = self.items[0:pos+1]
         self.images = self.images[0:pos+1]
         self.step=pos

    def revertToPriorStep(self):
       print "revert"
       self.deleteMask()
       self.step-=1
       self.modifications = self.modifications[0:len(self.modifications)-1]
       self.items=self.items[0:len(self.items)-1]

    def deleteMask(self):
       f = self.filefinder.composeFileName('_mask_' + str(self.step) + '.png')
       if (os.path.exists(f)):
         os.remove(f)

    def isMask(self, name):
      return name.rfind('_mask_')>0

    def scanNextImage(self):
      suffix =   self.startImageName()[self.startImageName().rfind('.'):]

      def filterF (file):
         return file not in self.items and not(self.isMask(file)) and file.endswith(suffix)
      
      # if the user is writing to the same output file
      # in a lock step process with the changes
      # then nfile remains the same name is changed file
      nfile = self.items[self.step]
      for file in self.filefinder.findFiles(filterF):
         nfile = file
         break

      maskfile = self.filefinder.composeFileName('_mask_' + str(self.step) + '.png')
      self.modifications.append(Modification('change',os.path.split(maskfile)[1]))
      self.items.append(nfile)
      self.images.append(Image.open(nfile))
      self.step+=1
      return nfile
    
defaultops = ['insert', 'splice',  'blur', 'resize', 'color', 'sharpen', 'compress', 'mosaic']

class DescriptionCaptureDialog(tkSimpleDialog.Dialog):

   description = None
   model = None
   justExit = False
   myops = []

   def __init__(self, parent, model,myops):
      self.description = model.nextModification()
      self.model = model
      self.myops = myops
      self.parent = parent
      tkSimpleDialog.Dialog.__init__(self, parent, "Operation Description")
     
   def newselection(self, event):
      self.value_of_combo = self.e1.get()

   def body(self, master):
      Label(master, text="Operation:").grid(row=0)
      Label(master, text="Description:").grid(row=1)

      self.e1 = AutocompleteEntryInText(master,self.myops,values=self.myops,takefocus=False)
      self.e1.bind("<Return>", self.newselection)
      self.e1.bind("<<ComboboxSelected>>", self.newselection)
      self.e2 = Entry(master)

      self.e1.grid(row=0, column=1)
      self.e2.grid(row=1, column=1)
      return self.e1 # initial focus

   def cancel(self):
       if not self.justExit:
          self.model.revertToPriorStep()
       tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
       self.justExit = True
       first = self.value_of_combo
#self.e1.get()
       second = self.e2.get()
       self.description.operationName = first
       self.description.additionalInfo = second
       self.parent.history.addModification(self.description)
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
    myops = []
    itemmenu = None

    def printit(self):
        print "hi"

    def open(self):
        val = tkFileDialog.askopenfilename(initialdir = self.scModel.filefinder.dir, title = "Select image file",filetypes = (("jpeg files","*.jpg"),("png files","*.png"),("all files","*.*")))
        if (val != None and len(val)> 0):
          self.scModel.setInitialImage(val)
          try:
            self.history.clearData()
            self.img1= ImageTk.PhotoImage(Image.open(self.scModel.startImageName()))
            self.img2= self.img1
            self.img3= ImageTk.PhotoImage(Image.fromarray(np.zeros((500,500,3)).astype('uint8')))
            self.img1c.itemconfig(self.img1oc, image= self.img1)
            self.img2c.itemconfig(self.img2oc, image=self.img2)
            self.img3c.itemconfig(self.img3oc, image=self.img3)         
            self.l1.config(text=os.path.split(self.scModel.startImageName())[1])
            self.l2.config(text=os.path.split(self.scModel.startImageName())[1])
            self.l3.config(text="")
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
        self.l1.config(text="")
        self.l2.config(text="")
        self.l3.config(text="")
        self.history.clearData()

    def next(self):
        self.processmenu.entryconfig(1,state='normal')
        self.scModel.scanNextImage()
        self.drawState()
        d = DescriptionCaptureDialog(self, self.scModel, self.myops)

    def drawState(self):
        self.img1= ImageTk.PhotoImage(self.scModel.startImage())
        self.img2= ImageTk.PhotoImage(self.scModel.nextImage())
        self.img3= ImageTk.PhotoImage(self.scModel.createMask())
        self.img1c.itemconfig(self.img1oc, image=self.img1)
        self.img2c.itemconfig(self.img2oc, image=self.img2)
        self.img3c.itemconfig(self.img3oc, image=self.img3)
        self.l1.config(text=os.path.split(self.scModel.startImageName())[1])
        self.l2.config(text=os.path.split(self.scModel.nextImageName())[1])
        self.l3.config(text=self.scModel.nextModification().maskFileName)
        
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

    def revert(self):
        maskid = self.history.focus()
        if (len(maskid)>0):
          self.history.clearData()
          self.scModel.revertToStep(maskid)
          self.drawState()
          self.history.loadData(self.scModel.modifications)

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
        self.img1c.grid(row = 1, column = 0)
        self.img2c = Canvas(img2f, width=500, height=500)
        self.img2c.grid(row = 1, column = 1)
        self.img3c = Canvas(img3f, width=500, height=500)
        self.img3c.grid(row = 1, column = 2)

        self.img1 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "white"))
        self.img1oc = self.img1c.create_image(250,250,image=self.img1, tag='img1')
        self.img2 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "white"))
        self.img2oc = self.img2c.create_image(250,250,image=self.img2, tag='img2')
        self.img3 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "white"))
        self.img3oc = self.img3c.create_image(250,250,image=self.img3, tag='img3')

        self.l1 = Label(img1f, text="") 
        self.l1.grid(row=0,column=0)
        self.l2 = Label(img2f, text="")
        self.l2.grid(row=0,column=1)
        self.l3 = Label(img3f, text="")
        self.l3.grid(row=0,column=2)

        self.itemmenu = Menu(self.master,tearoff=0)
        self.itemmenu.add_command(label="Revert To", command=self.revert)

        self.history = HistoryFrame(self.master)
        self.history.grid(row=2,column=0,columnspan=3,sticky=W+E+N+S)
        self.history.tree.bind("<Button-2>", self.popup)
        

    def popup(self, event):
       self.itemmenu.post(event.x_root, event.y_root)

    def __init__(self, filefinder,master=None, ops=[]):
        Frame.__init__(self, master)
        self.myops = ops
        self.createWidgets()
        self.filefinder = filefinder
        self.scModel = ScenarioModel(filefinder)

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

