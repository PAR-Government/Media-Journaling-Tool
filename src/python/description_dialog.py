from Tkinter import *
from group_filter import GroupFilter,GroupFilterLoader
import Tkconstants, tkFileDialog, tkSimpleDialog
from PIL import Image, ImageTk
from autocomplete_it import AutocompleteEntryInText
from tool_set import imageResize,imageResizeRelative, fixTransparency,openImage
from scenario_model import ProjectModel,Modification
from software_loader import Software, SoftwareLoader, getOS
import os
import numpy as np

def opfromitem(item):
   return (item[0] if type(item) is tuple else item)

def descfromitem(item):
   return (item[1] if type(item) is tuple else '')

def softwarefromitem(item):
   return (item[2] if type(item) is tuple and len(item)>3 else None)

def versionfromitem(item):
   return (item[3] if type(item) is tuple and len(item)>3 else None)

def getCategory(ops, mod):
    if mod.category is not None and len(mod.category)>0:
       return mod.category
    if mod.operationName is not None and len(mod.operationName)>0:
       matches = [i[0] for i in ops.items() if (mod.operationName in i[1])]
       if (len(matches)>0):
          return matches[0]
    return None

class DescriptionCaptureDialog(tkSimpleDialog.Dialog):

   description = None
   im = None
   dir = '.'
   software = None
   myops = {}
   photo=None
   c= None
   moc = None
   cancelled = True

   def __init__(self, parent,dir,im, myops,name, description=None, software=None):
      self.myops = myops
      self.dir = dir
      self.im = im
      self.parent = parent
      self.description=description if description is not None else Modification('','')
      self.software=software
      self.softwareLoader = SoftwareLoader()
      for catlist in self.myops.itervalues():
         for cat in catlist:
           if self.softwareLoader.add(Software(softwarefromitem(cat),versionfromitem(cat))):
             self.softwareLoader.save()
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def newcommand(self,event):
      command = self.e2.get()
      cat = self.e1.get()
      if cat in self.myops:
        catlist = self.myops[cat]
        for ctuple in catlist:
          if ctuple[0]==command:
           self.e4.set_completion_list(self.softwareLoader.get_names(),initialValue=softwarefromitem(ctuple))
           self.e5.set_completion_list(self.softwareLoader.get_versions(),initialValue=versionfromitem(ctuple))

   def newcategory(self, event):
      if (self.myops.has_key(self.e1.get())):
        oplist = [opfromitem(x) for x in self.myops[self.e1.get()]]
        desclist = [descfromitem(x) for x in self.myops[self.e1.get()]]
        self.e2.set_completion_list(oplist)
        self.e3.delete(1.0,END)
        self.e3.insert(1.0,desclist[0] if len(desclist)>0 else '')
      else:
        self.e2.set_completion_list([])
        self.e3.delete(1.0,END)

   def body(self, master):
      self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im,(250,250))))
      self.c = Canvas(master, width=250, height=250)
      self.c.create_image(125,125,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)
      Label(master, text="Category:").grid(row=1,sticky=W)
      Label(master, text="Operation:").grid(row=2,sticky=W)
      Label(master, text="Description:").grid(row=3,sticky=W)
      Label(master, text="Software Name:").grid(row=4,sticky=W)
      Label(master, text="Software Version:").grid(row=5,sticky=W)
      Label(master, text="Input Mask:").grid(row=6, column=0,sticky=W)
      self.inputmaskvar = StringVar()
      self.inputmaskvar.set('None' if self.description.inputmaskpathname is None else os.path.split(self.description.inputmaskpathname)[1])
      Label(master, textvariable=self.inputmaskvar).grid(row=6,column=1, sticky=W)
      self.attachImage = ImageTk.PhotoImage(file="icons/attach.png")
      self.b = Button(master,image=self.attachImage,text="Load",command=self.addinputmask)
      self.b.grid(row=6,column=3)

      opv = []
      cats = self.myops.keys()
      if (len(cats)>0):
         opv = [opfromitem(x) for x in self.myops[cats[0]]]
      self.e1 = AutocompleteEntryInText(master,values=cats,takefocus=False)
      self.e2 = AutocompleteEntryInText(master,values=opv,takefocus=False)
      self.e4 = AutocompleteEntryInText(master,values=self.softwareLoader.get_names(),takefocus=False)
      self.e5 = AutocompleteEntryInText(master,values=self.softwareLoader.get_versions(),takefocus=False)
      self.e1.bind("<Return>", self.newcategory)
      self.e1.bind("<<ComboboxSelected>>", self.newcategory)
      self.e2.bind("<Return>", self.newcommand)
      self.e2.bind("<<ComboboxSelected>>", self.newcommand)
      self.e3 = Text(master,height=2,width=28,font=('Times', '14'), relief=RAISED,borderwidth=2)

      if (len(cats)>0):
        self.e3.insert(1.0,descfromitem(self.myops[cats[0]][0]))

      self.e1.grid(row=1, column=1)
      self.e2.grid(row=2, column=1)
      self.e3.grid(row=3, column=1,sticky=E)
      self.e4.grid(row=4, column=1)
      self.e5.grid(row=5, column=1)

      if (self.description.inputmaskpathname is not None):
        self.inputmask = ImageTk.PhotoImage(openImage(self.description.inputmaskpathname))
        self.m = Canvas(master, width=250, height=250)
        self.moc = self.m.create_image(125,125,image=self.inputmask, tag='imgm')
        self.m.grid(row=7, column=0, columnspan=2)

      if self.description is not None:
         if (self.description.operationName is not None and len(self.description.operationName)>0):
            self.e1.set_completion_list(self.myops.keys(),initialValue=getCategory(self.myops,self.description))
            oplist = [opfromitem(x) for x in self.myops[self.e1.get()]]
            self.e2.set_completion_list(oplist,self.description.operationName)
         if (self.description.additionalInfo is not None):
            self.e3.delete(1.0, END)
            self.e3.insert(1.0,self.description.additionalInfo)

      if self.software is not None:
         self.e4.set_completion_list(self.softwareLoader.get_names(),initialValue=self.software.name)
         self.e5.set_completion_list(self.softwareLoader.get_versions(),initialValue=self.software.version)
      else:
         self.newcommand(None)

      return self.e1 # initial focus

   def addinputmask(self):
       val = tkFileDialog.askopenfilename(initialdir = dir, title = "Select Input Mask",filetypes = (("jpeg files","*.jpg"),("png files","*.png"),("all files","*.*")))
       if (val != None and len(val)> 0):
        try:
          self.inputmask = ImageTk.PhotoImage(openImage(val))
          if self.moc is not None: 
            self.m.itemconfig(self.moc, image=self.inputmask)
          self.inputmaskvar.set(os.path.split(val)[1])
          self.description.inputmaskpathname = val
        except IOError:
          tkMessageBox.showinfo("Error", "Failed to load image")

   def cancel(self):
       if self.cancelled:
          self.description = None
       tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
       self.cancelled = False
       self.description.operationName=self.e2.get()
       self.description.additionalInfo=self.e3.get(1.0,END)
       self.description.category=self.e1.get()
       self.software=Software(self.e4.get(),self.e5.get())
       if (self.softwareLoader.add(self.software)):
          self.softwareLoader.save()

   def getSoftware(self):
      return self.software

class DescriptionViewDialog(tkSimpleDialog.Dialog):

   description = None
   im = None
   software = None
   photo=None
   c= None

   def __init__(self, parent,im, myops,name, description=None,software=None):
      self.myops = myops
      self.im = im
      self.parent = parent
      self.description=description if description is not None else Modification('','')
      self.software = software
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      self.photo = ImageTk.PhotoImage(imageResize(self.im,(250,250)))
      self.c = Canvas(master, width=250, height=250)
      self.c.create_image(128,128,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)
      Label(master, text="Category:",anchor=W,justify=LEFT).grid(row=1, column=0,sticky=W)
      Label(master, text="Operation:",anchor=W,justify=LEFT).grid(row=2, column=0,sticky=W)
      Label(master, text="Description:",anchor=W,justify=LEFT).grid(row=3, column=0,sticky=W)
      Label(master, text="Software Name:",anchor=W,justify=LEFT).grid(row=4, column=0,sticky=W)
      Label(master, text="Software Version:",anchor=W,justify=LEFT).grid(row=5, column=0,sticky=W)
      Label(master, text=self.description.operationName,anchor=W,justify=LEFT).grid(row=1,column=1,sticky=W)
      Label(master, text=getCategory(self.myops,self.description),anchor=W,justify=LEFT).grid(row=2, column=1,sticky=W)
      Label(master, text=self.description.additionalInfo,anchor=W,justify=LEFT).grid(row=3, column=1,sticky=W)
      Label(master, text=self.software.name,anchor=W,justify=LEFT).grid(row=4, column=1,sticky=W)
      Label(master, text=self.software.version,anchor=W,justify=LEFT).grid(row=5, column=1,sticky=W)

   def cancel(self):
       tkSimpleDialog.Dialog.cancel(self)

   def buttonbox(self):
        box = Frame(self)
        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()

class ImageNodeCaptureDialog(tkSimpleDialog.Dialog):
   scModel = None
   selectedImage = None

   def __init__(self,parent,scModel):
      self.scModel = scModel
      tkSimpleDialog.Dialog.__init__(self, parent, "Select Image Node")

   def body(self, master):
      Label(master, text="Image Name:",anchor=W,justify=LEFT).grid(row=0, column=0,sticky=W)
      self.box = AutocompleteEntryInText(master,values=self.scModel.getNodeNames(), takefocus=True)
      self.box.grid(row=0,column=1)
      self.c = Canvas(master, width=250, height=250)
      self.photo= ImageTk.PhotoImage(Image.fromarray(np.zeros((250,250))))
      self.imc = self.c.create_image(125,125,image=self.photo, tag='imgd')
      self.c.grid(row=1, column=0, columnspan=2)
      self.box.bind("<Return>", self.newimage)
      self.box.bind("<<ComboboxSelected>>", self.newimage)

   def newimage(self,event):
      im = self.scModel.getImage(self.box.get())
      self.photo=ImageTk.PhotoImage(fixTransparency(imageResize(im,(250,250))))
      self.c.itemconfig(self.imc,image=self.photo)

   def cancel(self):
      tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
      self.selectedImage = self.box.get()     

class CompareDialog(tkSimpleDialog.Dialog):
   
   def __init__(self,parent,im,mask,name, analysis):
      self.im  = im
      self.mask = mask
      self.analysis = analysis
      tkSimpleDialog.Dialog.__init__(self, parent, "Compare to " + name)

   def body(self, master):
      self.cim = Canvas(master, width=250, height=250)
      self.photoim= ImageTk.PhotoImage(fixTransparency(imageResizeRelative(self.im,(250,250),self.im.size)))
      self.imc = self.cim.create_image(125,125,image=self.photoim, tag='imgim')
      self.cim.grid(row=0, column=0)

      self.cmask = Canvas(master, width=250, height=250)
      self.photomask= ImageTk.PhotoImage(fixTransparency(imageResizeRelative(self.mask,(250,250),self.mask.size)))
      self.maskc = self.cmask.create_image(125,125,image=self.photomask, tag='imgmask')
      self.cmask.grid(row=0, column=1)

      iframe = Frame(master, bd=2, relief=SUNKEN)
      iframe.grid_rowconfigure(1, weight=1)
#      iframe.grid_columnconfigure(0, weight=1)
      Label(iframe, text='  '.join([key + ': ' + str(value) for key,value in self.analysis.items()]),anchor=W,justify=LEFT).grid(row=0, column=0,sticky=W)
      iframe.grid(row=1,column=0,columnspan=2, sticky=N+S+E+W)

   def buttonbox(self):
        box = Frame(self)
        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()

class FilterCaptureDialog(tkSimpleDialog.Dialog):

   description = None
   im = None
   software = None
   photo=None
   c= None
   optocall= None
   argvalues = {}
   cancelled = True

   def __init__(self,parent,dir,im, myops, name, scModel):
      self.myops = myops
      self.im = im
      self.dir = dir
      self.parent = parent
      self.description=Modification('','')
      self.scModel = scModel
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      self.photo = ImageTk.PhotoImage(imageResize(self.im,(250,250)))
      self.c = Canvas(master, width=250, height=250)
      self.c.create_image(128,128,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)
      self.e1 = AutocompleteEntryInText(master,values=self.myops.keys(),takefocus=True)
      self.e1.bind("<Return>", self.newop)
      self.e1.bind("<<ComboboxSelected>>", self.newop)
      row = 1
      labels = ['Plugin Name:','Category:','Operation:','Software Name:','Software Version:']
      for label in labels:
        Label(master, text=label,anchor=W,justify=LEFT).grid(row=row, column=0,sticky=W)
        row+=1
      self.catvar = StringVar()
      self.opvar = StringVar()
      self.softwarevar = StringVar()
      self.versionvar = StringVar()
      self.e1.grid(row=1, column=1)
      row=2
      variables = [self.catvar, self.opvar, self.softwarevar, self.versionvar]
      for variable in variables:
        Label(master, textvariable=variable,anchor=W,justify=LEFT).grid(row=row,column=1,sticky=W)
        row+=1
      Label(master, text='Parameters:',anchor=W,justify=LEFT).grid(row=row, column=0,columnspan=2)
      row+=1
      self.argBox = Listbox(master)
      self.argBox.bind("<Double-Button-1>", self.changeParameter)
      self.argBox.grid(row=row,column =0, columnspan=2)
      if len(self.myops.keys()) > 0:
         self.newop(None)

   def changeParameter(self,event):
      if len(self.argBox.curselection()) == 0:
        return
      index = int(self.argBox.curselection()[0])
      value = self.argBox.get(index)
      if self.optocall is not None:
        op=self.myops[self.optocall]
        arginfo = op['arguments']
        if arginfo is not None:
          arg = arginfo[index]
          if arg[0] == 'donor':
            d = ImageNodeCaptureDialog(self, self.scModel)
            res = d.selectedImage
          elif arg[0] == 'inputmaskpathname':
             val = tkFileDialog.askopenfilename(initialdir = dir, title = "Select Input Mask",filetypes = (("jpeg files","*.jpg"),("png files","*.png"),("all files","*.*")))
             if (val != None and len(val)> 0):
                res=val
          else:
            res = tkSimpleDialog.askstring("Set Parameter " + arg[0], "Value:", parent=self)
          if res is not None:
            self.argvalues[arg[0]] = res
            self.argBox.delete(index)
            self.argBox.insert(index,arg[0] + ': ' + res)
           
   def newop(self, event):
      self.argvalues= {}
      if (self.myops.has_key(self.e1.get())):
         self.optocall=self.e1.get()
         self.argBox.delete(0,END)
         op=self.myops[self.optocall]
         opinfo = op['operation']
         arginfo = op['arguments']
         self.catvar.set(opinfo[1])
         self.opvar.set(opinfo[0])
         self.description.additionalInfo=opinfo[2]
         self.softwarevar.set(opinfo[3])
         self.versionvar.set(opinfo[4])
         if arginfo is not None:
           for arg in arginfo:
              if arg is not None:
                self.argBox.insert(END,arg[0] + ': ' + str(arg[1] if arg[1] is not None else ''))
      else:
         self.catvar.set('')
         self.opvar.set('')
         self.softwarevar.set('')
         self.versionvar.set('')
         self.optocall = None
         self.argBox.delete(0,END)

   def cancel(self):
       if self.cancelled:
          self.optocall=None
       tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
       self.cancelled = False
       self.optocall=self.e1.get()
       self.description.operationName=self.opvar.get()
       self.description.additionalInfo=self.e1.get() + ':' + self.description.additionalInfo
       self.description.category=self.catvar.get()
       self.software=Software(self.softwarevar.get(),self.versionvar.get())
       self.software.internal=True
#       if (self.softwareLoader.add(self.software)):
#          self.softwareLoader.save()

   def getSoftware(self):
      return self.software


class FilterGroupCaptureDialog(tkSimpleDialog.Dialog):

   gfl = None
   im = None
   grouptocall= None
   cancelled = True

   def __init__(self,parent,im,name):
      self.im = im
      self.parent = parent
      self.name = name
      self.gfl=  GroupFilterLoader()
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      self.photo = ImageTk.PhotoImage(imageResize(self.im,(250,250)))
      self.c = Canvas(master, width=250, height=250)
      self.c.create_image(128,128,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)
      Label(master, text="Group Name:",anchor=W,justify=LEFT).grid(row=1, column=0,sticky=W)
      self.e1 = AutocompleteEntryInText(master,values=self.gfl.getGroupNames(),takefocus=True)
      self.e1.grid(row=1, column=1)

   def cancel(self):
       if self.cancelled:
          self.grouptocall = None
       tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
       self.cancelled = False
       self.grouptocall=self.e1.get()

   def getGroup(self):
      return self.grouptocall
