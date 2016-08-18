from Tkinter import *
from datetime import datetime
import tkMessageBox
from group_filter import GroupFilter,GroupFilterLoader
import Tkconstants, tkFileDialog, tkSimpleDialog
from PIL import Image, ImageTk
from autocomplete_it import AutocompleteEntryInText
from tool_set import imageResize,imageResizeRelative, fixTransparency,openImage,openFile,validateTimeString,validateCoordinates
from scenario_model import Modification
from software_loader import Software, SoftwareLoader, getOS, getOperations,getOperationsByCategory,getOperation
import os
import numpy as np
from tkintertable import TableCanvas, TableModel

def promptForParameter(parent,dir,argumentTuple,filetypes, initialvalue):
    """
     argumentTuple is (name,dict(values, type,descriptipn))
     type is list, imagefile, donor, float, int, time.  float and int have a range in the follow format: [-80:80]
      
    """
    res = None
    if argumentTuple[1]['type'] == 'imagefile':
       val = tkFileDialog.askopenfilename(initialdir = dir, title = "Select " + argumentTuple[0],filetypes = filetypes)
       if (val != None and len(val)> 0):
           res=val
    elif argumentTuple[1]['type'] == 'xmpfile':
       val = tkFileDialog.askopenfilename(initialdir = dir, title = "Select " + argumentTuple[0],filetypes = [('XMP','*.xmp')])
       if (val != None and len(val)> 0):
           res=val
    elif argumentTuple[1]['type'].startswith('donor'):
       d = ImageNodeCaptureDialog(parent, parent.scModel)
       res = d.selectedImage
    elif argumentTuple[1]['type'].startswith('float'):
       v = argumentTuple[1]['type']
       vals = [float(x) for x in v[v.rfind('[')+1:-1].split(':')]
       res = tkSimpleDialog.askfloat("Set Parameter " + argumentTuple[0], argumentTuple[1]['description'],minvalue=vals[0],maxvalue=vals[1], \
          parent=parent, initialvalue=initialvalue)
    elif argumentTuple[1]['type'].startswith('int'):
       v = argumentTuple[1]['type']
       vals = [int(x) for x in v[v.rfind('[')+1:-1].split(':')]
       res = tkSimpleDialog.askinteger("Set Parameter " + argumentTuple[0], argumentTuple[1]['description'],minvalue=vals[0],maxvalue=vals[1], \
         parent=parent,initialvalue=initialvalue)
    elif argumentTuple[1]['type'] == 'list':
       d = SelectDialog(parent,"Set Parameter " + argumentTuple[0],argumentTuple[1]['description'],argumentTuple[1]['values'])
       res = d.choice
    elif argumentTuple[1]['type'] == 'time':
       d = EntryDialog(parent,"Set Parameter " + argumentTuple[0],argumentTuple[1]['description'],validateTimeString,initialvalue=initialvalue)
       res = d.choice
    elif argumentTuple[1]['type'] == 'coordinates':
       d = EntryDialog(parent,"Set Parameter " + argumentTuple[0],argumentTuple[1]['description'],validateCoordinates,initialvalue=initialvalue)
       res = d.choice
    else:
       d = EntryDialog(parent,"Set Parameter " + argumentTuple[0],argumentTuple[1]['description'],None,initialvalue=initialvalue)
       res = d.choice
    return res
    
def getCategory(mod):
    ops = getOperations()
    if mod.category is not None and len(mod.category)>0:
       return mod.category
    if mod.operationName in ops:
      return ops[mod.operationName].category
    return None

def tupletostring(tuple):
   strv = ''
   for item in tuple[1:]:
     if type(item) is str:
       strv = strv + item + ' '
     else:
       strv = strv + str(item) + ' '
   return strv

class PropertyDialog(tkSimpleDialog.Dialog):

   parent = None
   cancelled = True

   def __init__(self, parent, properties):
     self.parent = parent
     self.properties = properties
     self.values = [None for prop in properties]
     tkSimpleDialog.Dialog.__init__(self, parent, "Project Properties")

   def body(self, master):
        row = 0
        for prop in self.properties:
           Label(master, text=prop[0]).grid(row=row,sticky=W)
           if prop[2] == 'list':
             self.values[row] = AutocompleteEntryInText(master,values=prop[3],takefocus=(row == 0),initialValue=self.parent.scModel.getProjectData(prop[1]))
           elif prop[2] == 'text':
             self.values[row] = Text(master,takefocus=(row==0),width=80, height=3,relief=RAISED,borderwidth=2)
             v = self.parent.scModel.getProjectData(prop[1])
             if v:
                 self.values[row].insert(1.0,v)
           else:
             self.values[row] = Entry(master,takefocus=(row==0),width=80)
             v = self.parent.scModel.getProjectData(prop[1])
             if v:
                 self.values[row].insert(0,v)
           self.values[row].grid(row=row,column=1,sticky=E+W)
           row+=1

   def cancel(self):
      if self.cancelled:
         self.description = None
      tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
      self.cancelled = False
      i = 0
      for prop in self.properties:
          v= self.values[i].get() if prop[2] != 'text' else self.values[i].get(1.0,END).strip()
          if v and len(v) > 0:
            self.parent.scModel.setProjectData(prop[1],v)
          i+=1

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

   def __init__(self, parent,uiProfile,dir,im,name, description=None):
      self.dir = dir
      self.uiProfile = uiProfile
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
          ok &= (arg in self.argvalues and len(str(self.argvalues[arg])) > 0)
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
        for k,v in op.mandatoryparameters.iteritems():
            self.__addToBox(k,True)
            self.arginfo.append((k,v))
            self.mandatoryinfo.append(k)
        for k,v in op.optionalparameters.iteritems():
            self.__addToBox(k,False)
            self.arginfo.append((k,v))
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
            self.inputMaskName = self.description.inputMaskName
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
          argumentTuple = self.arginfo[index]
          res = promptForParameter(self, self.dir,argumentTuple, self.uiProfile.filetypes, \
             self.argvalues[argumentTuple[0]] if argumentTuple[0] in self.argvalues else None)
          if argumentTuple[0] == 'inputmaskname' and res:
            self.inputMaskName = res
          if res is not None:
            self.argvalues[argumentTuple[0]] = res
            self.argBox.delete(index)
            sep = '*: ' if argumentTuple[0] in self.mandatoryinfo else ': '
            self.argBox.insert(index,argumentTuple[0] + sep + str(res))
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
       self.description.setAdditionalInfo(self.e3.get(1.0,END).strip())
       self.description.setInputMaskName(self.inputMaskName)
       self.description.setArguments({k:v for (k,v) in self.argvalues.iteritems() if k in [x[0] for x in self.arginfo]})
       self.description.setSoftware(Software(self.e4.get(),self.e5.get()))
       if (self.softwareLoader.add(self.description.software)):
          self.softwareLoader.save()

class DescriptionViewDialog(tkSimpleDialog.Dialog):

   description = None
   im = None
   photo=None
   c= None
   metadiff = None

   def __init__(self,parent,dir,im,name,description=None,metadiff=None):
      self.im = im
      self.dir = dir
      self.parent = parent
      self.description=description if description is not None else Modification('','')
      self.metadiff = metadiff
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      vscrollbar = Scrollbar(master, orient=VERTICAL)
      Label(master, text="Operation:",anchor=W,justify=LEFT).grid(row=0, column=0,sticky=W)
      Label(master, text="Description:",anchor=W,justify=LEFT).grid(row=1, column=0,sticky=W)
      Label(master, text="Software:",anchor=W,justify=LEFT).grid(row=2, column=0,sticky=W)
      Label(master, text=getCategory(self.description),anchor=W,justify=LEFT).grid(row=0, column=1,sticky=W)
      Label(master, text=self.description.operationName,anchor=W,justify=LEFT).grid(row=0,column=2,sticky=W)
      Label(master, text=self.description.additionalInfo,anchor=W,justify=LEFT).grid(row=1, column=1,columnspan=3,sticky=W)
      Label(master, text=self.description.getSoftwareName(),anchor=W,justify=LEFT).grid(row=2, column=1,sticky=W)
      Label(master, text=self.description.getSoftwareVersion(),anchor=W,justify=LEFT).grid(row=2, column=2,sticky=W)
      row=3
      if len(self.description.arguments)>0:
        Label(master, text='Parameters:',anchor=W,justify=LEFT).grid(row=row, column=0,columnspan=4,sticky=W)
        row+=1
        for argname,argvalue in self.description.arguments.iteritems(): 
             Label(master, text='      ' + argname + ': ' + str(argvalue),justify=LEFT).grid(row=row, column=0, columnspan=4,sticky=W)
             row+=1
      if self.description.inputMaskName is not None:
        self.inputmaskframe = ButtonFrame(master,self.description.inputMaskName, self.dir, \
             label='Mask ('+self.description.inputMaskName+'):',isMask=True,preserveSnapshot=True)
        self.inputmaskframe.grid(row=row, column=0, columnspan=4,sticky=E+W)
        row+=1
      if self.metadiff is not None:
        sections = self.metadiff.getSections()
        Label(master, text=self.metadiff.getMetaType() +' Changes:',anchor=W,justify=LEFT).grid(row=row, column=0,columnspan=2 if sections else 4,sticky=E+W)
        self.metaBox = MetaDiffTable(master,self.metadiff)
        if sections is not None:
           self.sectionBox = Spinbox(master,values=['Section ' + section for section in sections], command=self.changeSection)
           self.sectionBox.grid(row=row,column=1,columnspan=2,sticky=SE+NW)
        row+=1
        self.metaBox.grid(row=row,column=0, columnspan=4,sticky=E+W)
        row+=1
      if self.description.maskSet is not None:
        self.maskBox = MaskSetTable(master,self.description.maskSet,openColumn=3,dir=self.dir)
        self.maskBox.grid(row=row,column=0, columnspan=4,sticky=SE+NW)
        row+=1

   def changeSection(self):
      self.metaBox.setSection(self.sectionBox.get()[8:])

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
      tkSimpleDialog.Dialog.__init__(self, parent, "Select " + scModel.getTypeName() + " Node")

   def body(self, master):
      Label(master, text=self.scModel.getTypeName() + " Name:",anchor=W,justify=LEFT).grid(row=0, column=0,sticky=W)
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
      Label(iframe, text='  '.join([key + ': ' + str(value) for key,value in self.analysis.items()]),anchor=W,justify=LEFT).grid(row=0, column=0,sticky=W)
      iframe.grid(row=1,column=0,columnspan=2, sticky=N+S+E+W)

   def buttonbox(self):
        box = Frame(self)
        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()


class VideoCompareDialog(tkSimpleDialog.Dialog):
   
   def __init__(self,parent,im,mask,name, analysis,dir):
      self.im  = im
      self.dir = dir
      self.mask = mask
      self.analysis = analysis
      tkSimpleDialog.Dialog.__init__(self, parent, "Compare to " + name)

   def body(self, master):
      row = 0
      metadiff = self.analysis['metadatadiff']
      maskSet = self.analysis['videomasks']
      sections = metadiff.getSections()
      Label(master, text=metadiff.getMetaType() +' Changes:',anchor=W,justify=LEFT).grid(row=row, column=0,columnspan=2 if sections else 4,sticky=E+W)
      self.metaBox = MetaDiffTable(master,metadiff)
      if sections is not None:
         self.sectionBox = Spinbox(master,values=['Section ' + section for section in sections], command=self.changeSection)
         self.sectionBox.grid(row=row,column=1,columnspan=2,sticky=SE+NW)
      row+=1
      self.metaBox.grid(row=row,column=0, columnspan=4,sticky=E+W)
      row+=1
      if maskSet is not None:
        self.maskBox = MaskSetTable(master,maskSet,openColumn=3,dir=self.dir)
        self.maskBox.grid(row=row,column=0, columnspan=4,sticky=SE+NW)
      row+=1

   def changeSection(self):
      self.metaBox.setSection(self.sectionBox.get()[8:])

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
        operation = getOperation(op['operation'][0])
        if arginfo is not None:
          arg = arginfo[index]
          argumentTuple = (arg[0],operation.mandatoryparameters[arg[0]]) if operation is not None and arg[0] in operation.mandatoryparameters else None
          argumentTuple = (arg[0],operation.optionalparameters[arg[0]]) if operation is not None and arg[0] in operation.optionalparameters else argumentTuple
          argumentTuple = ('donor',{'type':'donor','description':'Donor'}) if arg[0] == 'donor' else argumentTuple
          argumentTuple = ('inputmaskname', {'type':'imagefile','description':'Input Mask File'}) if arg[0] == 'inputmaskname' else argumentTuple
          argumentTuple = (arg[0],{'type':'string','description': arg[2] if len(arg) > 2 else 'Not Available'}) if argumentTuple is None else argumentTuple
          res = promptForParameter(self, self.dir, argumentTuple, self.parent.uiProfile.filetypes, arg[1])
          if res is not None:
            self.argvalues[arg[0]] = res
            self.argBox.delete(index)
            self.argBox.insert(index,arg[0] + ': ' + str(res))
           
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

class ActionableTableCanvas(TableCanvas):

   def __init__(self, parent=None, model=None, width=None, height=None, openColumn=None, dir='.',**kwargs):
       self.openColumn = openColumn
       self.dir = dir
       TableCanvas.__init__(self,parent=parent,model=model,width=width,height=height,**kwargs)

   def handle_double_click(self, event):
      row = self.get_row_clicked(event)
      self.openFile(row)

   def openFile(self,row):
      model=self.getModel()      
      f = model.getValueAt(row,self.openColumn)
      openFile(os.path.join(self.dir,f))

   def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        defaultactions = {"Set Fill Color" : lambda : self.setcellColor(rows,cols,key='bg'),
                        "Set Text Color" : lambda : self.setcellColor(rows,cols,key='fg'),
                        "Open":  lambda : self.openFile(row),
                        "Copy" : lambda : self.copyCell(rows, cols),
                        "View Record" : lambda : self.getRecordInfo(row),
                        "Select All" : self.select_All,
                        "Filter Records" : self.showFilteringBar,
                        "Export csv": self.exportTable,
                        "Plot Selected" : self.plotSelected,
                        "Plot Options" : self.plotSetup,
                        "Export Table" : self.exportTable,
                        "Preferences" : self.showtablePrefs,
                        "Formulae->Value" : lambda : self.convertFormulae(rows, cols)}

        if self.openColumn:
          main = ["Open","Set Fill Color","Set Text Color","Copy"]
        else:
          main = ["Set Fill Color","Set Text Color","Copy"]
        general = ["Select All", "Filter Records", "Preferences"]
        filecommands = ['Export csv']
        plotcommands = ['Plot Selected','Plot Options']
        utilcommands = ["View Record", "Formulae->Value"]

        def createSubMenu(parent, label, commands):
            menu = Menu(parent, tearoff = 0)
            popupmenu.add_cascade(label=label,menu=menu)
            for action in commands:
                menu.add_command(label=action, command=defaultactions[action])
            return menu

        def add_commands(fieldtype):
            """Add commands to popup menu for column type and specific cell"""
            functions = self.columnactions[fieldtype]
            for f in functions.keys():
                func = getattr(self, functions[f])
                popupmenu.add_command(label=f, command= lambda : func(row,col))
            return

        popupmenu = Menu(self, tearoff = 0)
        def popupFocusOut(event):
            popupmenu.unpost()

        if outside == None:
            #if outside table, just show general items
            row = self.get_row_clicked(event)
            col = self.get_col_clicked(event)
            coltype = self.model.getColumnType(col)
            def add_defaultcommands():
                """now add general actions for all cells"""
                for action in main:
                    popupmenu.add_command(label=action, command=defaultactions[action])
                return

#            if self.columnactions.has_key(coltype):
#                add_commands(coltype)
            add_defaultcommands()

        for action in general:
            popupmenu.add_command(label=action, command=defaultactions[action])

        popupmenu.add_separator()
        createSubMenu(popupmenu, 'File', filecommands)
        createSubMenu(popupmenu, 'Plot', plotcommands)
        if outside == None:
            createSubMenu(popupmenu, 'Utils', utilcommands)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        return popupmenu


class MaskSetTable(Frame):

    section = None
    def __init__(self, master,items,openColumn=3,dir='.',**kwargs):
        self.items = items
        Frame.__init__(self, master,  **kwargs)
        self._drawMe(dir,openColumn)
  
    def _drawMe(self,dir,openColumn):
       model = TableModel()
       for c in self.items.columnNames:
          model.addColumn(c)
       model.importDict(self.items.columnValues)

       self.table = ActionableTableCanvas(self, model=model, rowheaderwidth=140, showkeynamesinheader=True,height=125,openColumn=openColumn,dir=dir)
       self.table.updateModel(model)
       self.table.createTableFrame()


class MetaDiffTable(Frame):

    section = None
    def __init__(self, master,items,section=None,**kwargs):
        self.items = items
        self.section = section
        Frame.__init__(self, master, **kwargs)
        self._drawMe()
  
    def setSection(self,section):
        if section == self.section:
            return
        self.section = section
        self.table.getModel().setupModel(self.items.toColumns(section))
        self.table.redrawTable()

    def _drawMe(self):
       model = TableModel()
       for c in  self.items.getColumnNames(self.section):
          model.addColumn(c)
       model.importDict(self.items.toColumns(self.section))

       self.grid_rowconfigure(0, weight=1)
       self.grid_columnconfigure(0, weight=1)

       self.table = ActionableTableCanvas(self, model=model, rowheaderwidth=140, showkeynamesinheader=True,height=125)
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
      self.yscrollbar = Scrollbar(master,orient=VERTICAL)
      self.xscrollbar = Scrollbar(master,orient=HORIZONTAL)
      self.itemBox = Listbox(master,width=80,yscrollcommand=self.yscrollbar.set,xscrollcommand=self.xscrollbar.set)
      self.itemBox.bind("<Double-Button-1>", self.change)
      self.itemBox.grid(row=0,column=0, sticky=E+W)
      self.xscrollbar.config(command=self.itemBox.xview)
      self.xscrollbar.grid(row=1,column=0,stick=E+W)
      self.yscrollbar.config(command=self.itemBox.xview)
      self.yscrollbar.grid(row=0,column=1,stick=N+S)
      self.master.grid_rowconfigure(0, weight=1)
      self.master.grid_columnconfigure(0, weight=1)
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
          self.im = openImage(os.path.join(self.dir,self.modification.inputMaskName),isMask=True,preserveSnapshot=True)
          self.selectMaskName = self.modification.inputMaskName
       elif self.modification.changeMaskName is not None:
          self.im = openImage(os.path.join(self.dir,self.modification.changeMaskName),isMask=True,preserveSnapshot=True)
          self.selectMaskName = self.modification.changeMaskName
       else:
          self.im = Image.fromarray(np.zeros((250,250)))
       self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im,(250,250))))
       self.c.itemconfig(self.image_on_canvas, image = self.photo)

   def changemask(self):
        val = tkFileDialog.askopenfilename(initialdir = self.dir, title = "Select Input Mask", \
              filetypes = self.parent.uiProfile.filetypes)
        if (val != None and len(val)> 0):
            self.selectMaskName = val
            self.im = openImage(val,isMask=True,preserveSnapshot=os.path.split(os.path.abspath(val))[0]==dir)
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


class ButtonFrame(Frame):
 
   def __init__(self,master,fileName,dir,label=None,isMask=False,preserveSnapshot=False,**kwargs):
      Frame.__init__(self,master,**kwargs)
      self.fileName = fileName
      self.dir = dir
      Label(self, text=label if label else fileName,anchor=W,justify=LEFT).grid(row=0, column=0,sticky=W)
      img = openImage(os.path.join(dir,fileName),isMask=isMask,preserveSnapshot=preserveSnapshot)
      self.img = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(img,(125,125),img.size)))
      w = Button(self, text=fileName, width=10, command=self.openMask, default=ACTIVE,image=self.img)
      w.grid(row=1,sticky=E+W)

   def openMask(self):
      openFile(os.path.join(self.dir,self.fileName))


class SelectDialog(tkSimpleDialog.Dialog):

   cancelled = True

   def __init__(self, parent,name,description, values):
      self.description = description
      self.values = values
      self.parent = parent
      self.name  = name
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      Label(master, text=self.description).grid(row=0, sticky=W)
      self.e1 = AutocompleteEntryInText(master,values=self.values,takefocus=True)
      self.e1.grid(row=1, column=0)

   def cancel(self):
      if self.cancelled:
        self.choice = None
      tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
      self.cancelled = False
      self.choice = self.e1.get()

class EntryDialog(tkSimpleDialog.Dialog):

   cancelled = True

   def __init__(self, parent,name,description, validateFunc,initialvalue=None):
      self.description = description
      self.validateFunc = validateFunc
      self.parent = parent
      self.name  = name
      self.initialvalue = initialvalue
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def body(self, master):
      Label(master, text=self.description).grid(row=0, sticky=W)
      self.e1 = Entry(master,takefocus=True)
      if self.initialvalue:
        self.e1.insert(0,self.initialvalue)
      self.e1.grid(row=1, column=0)

   def cancel(self):
      if self.cancelled:
         self.choice = None
      tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
      self.cancelled = False
      self.choice = self.e1.get()

   def validate(self): 
      v = self.e1.get()
      if self.validateFunc and not self.validateFunc(v):
         tkMessageBox.showwarning(
              "Bad input",
              "Illegal values, please try again"
         )
         return 0
      return 1
