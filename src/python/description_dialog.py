from Tkinter import *
import Tkconstants, tkFileDialog, tkSimpleDialog
from PIL import Image, ImageTk
from autocomplete_it import AutocompleteEntryInText
from tool_set import imageResize
from scenario_model import ProjectModel,Modification

def opfromitem(item):
   return (item[0] if type(item) is tuple else item)

def descfromitem(item):
   return (item[1] if type(item) is tuple else '')

def getCategory(ops, mod):
    if (mod.category is not None):
       return mod.category
    if (mod.operationName is not None):
       matches = [i[0] for i in ops.items() if (mod.operationName in i[1])]
       if (len(matches)>0):
          return matches[0]
    return None

class DescriptionCaptureDialog(tkSimpleDialog.Dialog):

   description = None
   im = None
   myops = []
   photo=None
   c= None

   def __init__(self, parent,im, myops,name, description=None):
      self.myops = myops
      self.im = im
      self.parent = parent
      self.value_of_combo=''
      self.description=description
      tkSimpleDialog.Dialog.__init__(self, parent, name)
      
   def newcategory(self, event):
      if (self.myops.has_key(self.e1.get())):
        oplist = [opfromitem(x) for x in self.myops[self.e1.get()]]
        desclist = [descfromitem(x) for x in self.myops[self.e1.get()]]
        self.e2.set_completion_list(oplist)
        self.e3.delete(0)
        self.e3.insert(0,desclist[0] if len(desclist)>0 else '')
      else:
        self.e2.set_completion_list([])
        self.e3.delete(0)

   def newselection(self, event):
      self.value_of_combo = self.e2.get()

   def body(self, master):
      self.photo = ImageTk.PhotoImage(imageResize(self.im,(250,250)))
      self.c = Canvas(master, width=250, height=250)
      self.c.create_image(125,125,image=self.photo, tag='imgd')
      self.c.grid(row=0, column=0, columnspan=2)
      Label(master, text="Category").grid(row=1)
      Label(master, text="Operation:").grid(row=2)
      Label(master, text="Description:").grid(row=3)

      opv = []
      cats = self.myops.keys()
      if (len(cats)>0):
         opv = [opfromitem(x) for x in self.myops[cats[0]]]
      self.e1 = AutocompleteEntryInText(master,values=cats,takefocus=False)
      self.e2 = AutocompleteEntryInText(master,values=opv,takefocus=False)
      self.e1.bind("<Return>", self.newcategory)
      self.e1.bind("<<ComboboxSelected>>", self.newcategory)
      self.e2.bind("<Return>", self.newselection)
      self.e2.bind("<<ComboboxSelected>>", self.newselection)
      self.e3 = Entry(master)

      if (len(cats)>0):
        self.e3.insert(0,descfromitem(self.myops[cats[0]][0]))

      self.value_of_combo = self.e2.get()

      self.e1.grid(row=1, column=1)
      self.e2.grid(row=2, column=1)
      self.e3.grid(row=3, column=1)

      if self.description is not None:
         self.e1.set_completion_list(self.myops.keys(),initialValue=getCategory(self.myops,self.description))
         oplist = [opfromitem(x) for x in self.myops[self.e1.get()]]
         self.e2.set_completion_list(oplist,self.description.operationName)
         if (self.description.additionalInfo is not None):
            self.e3.delete(0)
            self.e3.insert(0,self.description.additionalInfo)

      return self.e1 # initial focus

   def cancel(self):
       tkSimpleDialog.Dialog.cancel(self)

   def apply(self):
       self.description = Modification(self.value_of_combo,self.e3.get())

