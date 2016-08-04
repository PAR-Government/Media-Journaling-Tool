from Tkinter import *
import tkMessageBox
from group_filter import GroupFilter,GroupFilterLoader
import Tkconstants, tkFileDialog, tkSimpleDialog
from PIL import Image, ImageTk
from autocomplete_it import AutocompleteEntryInText
from tool_set import imageResize,imageResizeRelative, fixTransparency,openImage
from scenario_model import ProjectModel,Modification
from software_loader import Software, SoftwareLoader, getOS, getOperations,getOperationsByCategory,getOperation
import os
import numpy as np
from tkintertable import TableCanvas, TableModel

def getCategory(mod):
    ops = getOperations()
    if mod.category is not None and len(mod.category)>0:
       return mod.category
    if mod.operationName in ops:
      return ops[mod.operationName].category
    return None

def exiftodict(exifdata): 
   d = {}
   for k,v in exifdata.iteritems(): 
      old = v[1] if v[0].lower()=='change' or v[0].lower()=='delete' else ''
      new = v[2] if v[0].lower()=='change' else (v[1] if v[0].lower()=='add' else '')
      d[k] = {'Operation':v[0],'Old':old,'New':new}
   return d

def tupletostring(tuple):
   strv = ''
   for item in tuple[1:]:
     if type(item) is str:
       strv = strv + item + ' '
     else:
       strv = strv + str(item) + ' '
   return strv

class DescriptionCaptureDialog(tkSimpleDialog.Dialog):

   description = None
   im = None
   inputMaskName = None
   dir = '.'
   photo=None
   c= None
   moc = None
   cancelled = True
   argvalues = {}
   arginfo = []
   mandatoryinfo = []

   def __init__(self, parent,dir,im,name, description=None):
      self.dir = dir
      self.im = im
      self.parent = parent
      self.argvalues=description.arguments if description is not None else {}
      self.description=description if description is not None else Modification('','')
      self.softwareLoader = SoftwareLoader()
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def newsoftware(self,event):
      sname = self.e4.get()
      self.e5.set_completion_list(self.softwareLoader.get_versions(sname),initialValue=self.softwareLoader.get_preferred_version(name=sname))

   def __checkParams(self):
       ok = True
       for arg in self.mandatoryinfo:
          ok  &= (arg in self.argvalues and len(self.argvalues[arg]) > 0)
       return ok

   def __addToBox(self,arg,mandatory):
      sep = '*: ' if mandatory else ': '
      if arg == 'inputmaskname':
          self.argBox.insert(END,arg + sep + (self.inputMaskName if self.inputMaskName is not None else ''))
      else:
          self.argBox.insert(END,arg + sep + (str(self.description.arguments[arg]) if arg in self.description.arguments else ''))

   def newcommand(self,event):
      op=getOperation(self.e2.get())
      self.argBox.delete(0,END)
      self.arginfo = []
      self.mandatoryinfo = []
      if op is not None:
        for arg in op.mandatoryparameters:
            self.__addToBox(arg,True)
            self.arginfo.append(arg)
            self.mandatoryinfo.append(arg)
        for arg in op.optionalparameters:
            self.__addToBox(arg,False)
            self.arginfo.append(arg)
      if self.okButton is not None:
         self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)

   def newcategory(self, event):
      opByCat = getOperationsByCategory()
      if self.e1.get() in opByCat:
        oplist = opByCat[self.e1.get()]
        self.e2.set_completion_list(oplist)
      else:
        self.e2.set_completion_list([])

   def body(self, master):
      self.okButton = None

      self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im,(250,250))))
      self.c = Canvas(master, width=250, height=250)
      self.c.create_image(125,125,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)
      Label(master, text="Category:").grid(row=1,sticky=W)
      Label(master, text="Operation:").grid(row=2,sticky=W)
      #self.attachImage = ImageTk.PhotoImage(file="icons/question.png")
      self.b = Button(master,bitmap='info',text="Help",command=self.help,borderwidth=0,relief=FLAT)
      self.b.grid(row=2,column=3)
      Label(master, text="Description:").grid(row=3,sticky=W)
      Label(master, text="Software Name:").grid(row=4,sticky=W)
      Label(master, text="Software Version:").grid(row=5,sticky=W)
      row=6
      Label(master, text='Parameters:',anchor=W,justify=LEFT).grid(row=row, column=0,columnspan=2)
      row+=1
      self.argBox = Listbox(master)
      self.argBox.bind("<Double-Button-1>", self.changeParameter)
      self.argBox.grid(row=row,column =0, columnspan=2, sticky=E+W)
      row+=1

      cats = getOperationsByCategory()
      catlist = list(cats.keys())
      catlist.sort()
      oplist = cats[catlist[0]] if len(cats)>0 else []
      self.e1 = AutocompleteEntryInText(master,values=catlist,takefocus=False)
      self.e2 = AutocompleteEntryInText(master,values=oplist,takefocus=False)
      self.e4 = AutocompleteEntryInText(master,values=self.softwareLoader.get_names(),takefocus=False)
      self.e5 = AutocompleteEntryInText(master,values=[],takefocus=False)
      self.e1.bind("<Return>", self.newcategory)
      self.e1.bind("<<ComboboxSelected>>", self.newcategory)
      self.e2.bind("<Return>", self.newcommand)
      self.e2.bind("<<ComboboxSelected>>", self.newcommand)
      self.e4.bind("<Return>", self.newsoftware)
      self.e4.bind("<<ComboboxSelected>>", self.newsoftware)
      self.e3 = Text(master,height=2,width=28,font=('Times', '14'), relief=RAISED,borderwidth=2)

      self.e1.grid(row=1, column=1)
      self.e2.grid(row=2, column=1)
      self.e3.grid(row=3, column=1,sticky=E)
      self.e4.grid(row=4, column=1)
      self.e5.grid(row=5, column=1)

      if self.description is not None:
         if (self.description.inputMaskName is not None):
            self.inputMaskname = self.description.inputMaskName
         if (self.description.operationName is not None and len(self.description.operationName)>0):
            selectCat = getCategory(self.description)
            self.e1.set_completion_list(catlist,initialValue=selectCat)
            oplist = cats[selectCat] if selectCat in cats else []
            self.e2.set_completion_list(oplist,initialValue=self.description.operationName)
         if (self.description.additionalInfo is not None):
            self.e3.delete(1.0, END)
            self.e3.insert(1.0,self.description.additionalInfo)
         self.newcommand(None)

      if self.description.software is not None:
         self.e4.set_completion_list(self.softwareLoader.get_names(),initialValue=self.description.software.name)
         self.e5.set_completion_list(self.softwareLoader.get_versions(self.description.software.name,version=self.description.software.version),initialValue=self.description.software.version)
      else:
         self.e4.set_completion_list(self.softwareLoader.get_names(),initialValue=self.softwareLoader.get_preferred_name())
         self.e5.set_completion_list(self.softwareLoader.get_versions(self.softwareLoader.get_preferred_name()),initialValue=self.softwareLoader.get_preferred_version(self.softwareLoader.get_preferred_name()))


      return self.e1 # initial focus

   def buttonbox(self):
        box = Frame(self)
        self.okButton = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE,state=ACTIVE if self.__checkParams() else DISABLED)
        self.okButton.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Escape>", self.cancel)
        box.pack()

   def changeParameter(self,event):
      if len(self.argBox.curselection()) == 0:
        return
      index = int(self.argBox.curselection()[0])
      value = self.argBox.get(index)
      if self.e2.get() is not None:
        op=getOperation(self.e2.get())
        if op is not None:
          res = None
          arg = self.arginfo[index]
          if arg == 'inputmaskname':
             val = tkFileDialog.askopenfilename(initialdir = dir, title = "Select Input Mask",filetypes = (("jpeg files","*.jpg"),("png files","*.png"),("all files","*.*")))
             if (val != None and len(val)> 0):
                res=val
                self.inputMaskName = res
          else:
            res = tkSimpleDialog.askstring("Set Parameter " + arg[0], "Value:", parent=self)
          if res is not None:
            self.argvalues[arg] = res
            self.argBox.delete(index)
            self.argBox.insert(index,arg + ': ' + res)
          self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)


   def help(self):
       op = getOperation(self.e2.get())
       if op is not None:
         tkMessageBox.showinfo(op.name, op.description if op.description is not None and len(op.description) > 0 else 'No description')

   def cancel(self):
       if self.cancelled:
          self.description = None
       tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
       self.cancelled = False
       self.description.setOperationName(self.e2.get())
       self.description.setAdditionalInfo(self.e3.get(1.0,END))
       self.description.setInputMaskName(self.inputMaskName)
       self.description.setArguments({k:v for (k,v) in self.argvalues.iteritems() if k in self.arginfo})
       self.description.setSoftware(Software(self.e4.get(),self.e5.get()))
       if (self.softwareLoader.add(self.description.software)):
          self.softwareLoader.save()

class DescriptionViewDialog(tkSimpleDialog.Dialog):

   description = None
   im = None
   photo=None
   c= None
   exifdiff = None

   def __init__(self,parent,dir,im,name, description=None,exifdiff=None):
      self.im = im
      self.dir = dir
      self.parent = parent
      self.description=description if description is not None else Modification('','')
      self.exifdiff = exifdiff
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
#      self.photo = ImageTk.PhotoImage(imageResize(self.im,(250,250)))
#      self.c = Canvas(master, width=250, height=250)
#      self.c.create_image(128,128,image=self.photo, tag='imgd')
#      self.c.grid(row=0, column=0, columnspan=2)
      Label(master, text="Category:",anchor=W,justify=LEFT).grid(row=0, column=0,sticky=W)
      Label(master, text="Operation:",anchor=W,justify=LEFT).grid(row=1, column=0,sticky=W)
      Label(master, text="Description:",anchor=W,justify=LEFT).grid(row=2, column=0,sticky=W)
      Label(master, text="Software Name:",anchor=W,justify=LEFT).grid(row=3, column=0,sticky=W)
      Label(master, text="Software Version:",anchor=W,justify=LEFT).grid(row=4, column=0,sticky=W)
      Label(master, text=getCategory(self.description),anchor=W,justify=LEFT).grid(row=0, column=1,sticky=W)
      Label(master, text=self.description.operationName,anchor=W,justify=LEFT).grid(row=1,column=1,sticky=W)
      Label(master, text=self.description.additionalInfo,anchor=W,justify=LEFT).grid(row=2, column=1,sticky=W)
      Label(master, text=self.description.getSoftwareName(),anchor=W,justify=LEFT).grid(row=3, column=1,sticky=W)
      Label(master, text=self.description.getSoftwareVersion(),anchor=W,justify=LEFT).grid(row=4, column=1,sticky=W)
      row=5
      if len(self.description.arguments)>0:
        Label(master, text='Parameters:',anchor=W,justify=LEFT).grid(row=row, column=0,columnspan=2,sticky=W)
        row+=1
        for argname,argvalue in self.description.arguments.iteritems(): 
             Label(master, text='      ' + argname + ': ' + argvalue,justify=LEFT).grid(row=row, column=0, columnspan=2,sticky=W)
             row+=1
      if self.description.inputMaskName is not None:
        Label(master, text='Mask:',anchor=W,justify=LEFT).grid(row=row, column=0,columnspan=2,sticky=W)
        self.inputmask = ImageTk.PhotoImage(openImage(os.path.join(self.dir,self.description.inputMaskName)))
        self.m = Canvas(master, width=250, height=250)
        self.moc = self.m.create_image(125,125,image=self.inputmask, tag='imgm')
        self.m.grid(row=row+1, column=0, columnspan=2,sticky=E+W)
        row+=2
      if self.exifdiff is not None and len(self.exifdiff) > 0:
         Label(master, text='EXIF Changes:',anchor=W,justify=LEFT).grid(row=row, column=0,columnspan=2,sticky=E+W)
         self.exifBox = ExifTable(master,self.exifdiff)
         self.exifBox.grid(row=row+1,column=0, columnspan=2,sticky=E+W)

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

   im = None
   photo=None
   c= None
   optocall= None
   argvalues = {}
   cancelled = True

   def __init__(self,parent,dir,im,pluginOps, name, scModel):
      self.pluginOps = pluginOps
      self.im = im
      self.dir = dir
      self.parent = parent
      self.scModel = scModel
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      self.photo = ImageTk.PhotoImage(imageResize(self.im,(250,250)))
      self.c = Canvas(master, width=250, height=250)
      self.c.create_image(128,128,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)
      self.e1 = AutocompleteEntryInText(master,values=self.pluginOps.keys(),takefocus=True)
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
      self.argBox.grid(row=row,column =0, columnspan=2,sticky=E+W)
      if len(self.pluginOps.keys()) > 0:
         self.newop(None)

   def changeParameter(self,event):
      if len(self.argBox.curselection()) == 0:
        return
      index = int(self.argBox.curselection()[0])
      value = self.argBox.get(index)
      if self.optocall is not None:
        op=self.pluginOps[self.optocall]
        arginfo = op['arguments']
        if arginfo is not None:
          arg = arginfo[index]
          if arg[0] == 'donor':
            d = ImageNodeCaptureDialog(self, self.scModel)
            res = d.selectedImage
          elif arg[0] == 'inputmaskname':
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
      if (self.pluginOps.has_key(self.e1.get())):
         self.optocall=self.e1.get()
         self.argBox.delete(0,END)
         op=self.pluginOps[self.optocall]
         opinfo = op['operation']
         arginfo = op['arguments']
         self.catvar.set(opinfo[1])
         self.opvar.set(opinfo[0])
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



class FilterGroupCaptureDialog(tkSimpleDialog.Dialog):

   gfl = None
   im = None
   grouptocall= None
   cancelled = True

   def __init__(self,parent,im,name):
      self.im = im
      self.parent = parent
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

class ExifTable(Frame):

    def __init__(self, master,items,**kwargs):
        self.items = items
        Frame.__init__(self, master, **kwargs)
        self._drawMe()
  
    def _drawMe(self):
       model = TableModel()
       for c in  ['Operation','Old','New']:
          model.addColumn(c)
       model.importDict(exiftodict(self.items))

       self.table = TableCanvas(self, model=model, rowheaderwidth=140, showkeynamesinheader=True)
       self.table.updateModel(model)
       self.table.createTableFrame()
  

class ListDialog(Toplevel):

   items = None

   def __init__(self,parent,items,name):
      self.items = items
      self.parent = parent
      Toplevel.__init__(self, parent)
      self.title(name)
      self.parent = parent
      body = Frame(self)
      self.body(body)
      body.pack(padx=5, pady=5)
      self.buttonbox()
      self.protocol("WM_DELETE_WINDOW", self.cancel)
      self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                parent.winfo_rooty()+50))


   def setItems(self,items):
      self.items = items
      self.itemBox.delete(0,END)
      for item in self.items:
         self.itemBox.insert(END,item[2])

#   def grab_set(self):
#       return None

   def body(self, master):
      self.itemBox = Listbox(master,width=80)
      self.itemBox.bind("<Double-Button-1>", self.change)
      self.itemBox.grid(row=0,column=0)
      for item in self.items:
         self.itemBox.insert(END,item[2])

   def cancel(self):
      self.parent.doneWithWindow(self)
      self.parent.focus_set()
      self.destroy()
      
   def change(self,event):
      if len(self.itemBox.curselection()) == 0:
        return
      index = int(self.itemBox.curselection()[0])
      self.parent.selectLink(self.items[index][0],self.items[index][1])

   def buttonbox(self):
      box = Frame(self)
      w = Button(box, text="OK", width=10, command=self.cancel, default=ACTIVE)
      w.pack(side=LEFT, padx=5, pady=5)
      self.bind("<Return>", self.cancel)
      self.bind("<Escape>", self.cancel)
      box.pack()

class CompositeCaptureDialog(tkSimpleDialog.Dialog):

   im = None
   selectMaskName = None
   cancelled = True
   modification = None

   def __init__(self, parent,dir,im,name,modification):
      self.dir = dir
      self.im = im
      self.parent = parent
      self.name  = name
      self.modification = modification
      self.selectMaskName = self.modification.selectMaskName
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im,(250,250))))
      self.c = Canvas(master, width=250, height=250)
      self.image_on_canvas = self.c.create_image(125,125,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)
      self.includeInMaskVar = StringVar()
      self.includeInMaskVar.set(self.modification.recordMaskInComposite)
      self.cbIncludeInComposite = Checkbutton(master, text="Included in Composite", variable=self.includeInMaskVar, \
         onvalue="yes", offvalue="no")
      self.useInputMaskVar = StringVar()
      self.useInputMaskVar.set('yes' if self.modification.usesInputMaskForSelectMask() else 'no')
      row  = 1
      self.cbIncludeInComposite.grid(row=row,column=0,columnspan=2,sticky=W)
      row+=1
      if (self.modification.inputMaskName is not None):
        self.cbUseInputMask = Checkbutton(master, text="Use Input Mask", variable=self.useInputMaskVar, \
           onvalue="yes", offvalue="no",command=self.useinputmask)
        self.cbUseInputMask.grid(row=row,column=0,columnspan=2,sticky=W)
        row+=1
      self.b = Button(master,text="Change Mask",command=self.changemask,borderwidth=0,relief=FLAT)
      self.b.grid(row=row,column=0)
      return self.cbIncludeInComposite

   def useinputmask(self):
       if self.useInputMaskVar.get() == 'yes':
          self.im = openImage(os.path.join(self.dir,self.modification.inputMaskName))
          self.selectMaskName = self.modification.inputMaskName
       elif self.modification.changeMaskName is not None:
          self.im = openImage(os.path.join(self.dir,self.modification.changeMaskName))
          self.selectMaskName = self.modification.changeMaskName
       else:
          self.im = Image.fromarray(np.zeros((250,250)))
       self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im,(250,250))))
       self.c.itemconfig(self.image_on_canvas, image = self.photo)

   def changemask(self):
        val = tkFileDialog.askopenfilename(initialdir = dir, title = "Select Input Mask", \
              filetypes = (("jpeg files","*.jpg"),("png files","*.png"),("all files","*.*")))
        if (val != None and len(val)> 0):
            self.selectMaskName = val
            self.im = openImage(val)
            self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im,(250,250))))
            self.c.itemconfig(self.image_on_canvas, image = self.photo)

   def cancel(self):
       tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
       self.cancelled = False
       self.modification.setSelectMaskName(self.selectMaskName)
       self.modification.setRecordMaskInComposite(self.includeInMaskVar.get())


class CompositeViewDialog(tkSimpleDialog.Dialog):

   im = None

   def __init__(self, parent,name,im):
      self.im = im
      self.parent = parent
      self.name  = name
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im,(250,250))))
      self.c = Canvas(master, width=250, height=250)
      self.image_on_canvas = self.c.create_image(125,125,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)

   def buttonbox(self):
        box = Frame(self)
        w1 = Button(box, text="Close", width=10, command=self.ok, default=ACTIVE)
        w2 = Button(box, text="Export", width=10, command=self.saveThenOk, default=ACTIVE)
        w1.pack(side=LEFT, padx=5, pady=5)
        w2.pack(side=RIGHT, padx=5, pady=5)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()

   def saveThenOk(self):
     val = tkFileDialog.asksaveasfilename(initialdir='.',initialfile=self.name + '_composite.png',filetypes=[("png files","*.png")],defaultextension='.png')
     if (val is not None and len(val) > 0):
       # to cover a bug in some platforms
       if not val.endswith('.png'):
          val = val + '.png'
       self.im.save(val)
       self.ok()

