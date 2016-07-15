from Tkinter import *
from group_filter import GroupFilter,GroupFilterLoader
import plugins
import Tkconstants, tkFileDialog, tkSimpleDialog
from PIL import Image, ImageTk
from tool_set import imageResize,fixTransparency

class GroupManagerDialog(tkSimpleDialog.Dialog):

   gfl=None
   checkboxes = {}
   lastselection = None

   def __init__(self, parent):
     self.parent = parent
     self.gfl = GroupFilterLoader()
     tkSimpleDialog.Dialog.__init__(self, parent, "Group Manager")

   def body(self, master):
     self.yScroll = Scrollbar(master, orient=VERTICAL)
     self.yScroll.grid(row=0, column=2, sticky=N+S)
     self.groupBox = Listbox(master, yscrollcommand=self.yScroll.set)
     self.yScroll['command'] = self.groupBox.yview
     for name in self.gfl.getGroupNames():
        self.groupBox.insert(END,name)
     self.groupBox.grid(row=0, column=0,columnspan=2, sticky=N+S+E+W)
     self.groupBox.bind("<<ListboxSelect>>",self.newgroup)
     self.addImage = ImageTk.PhotoImage(imageResize(Image.open("icons/add.png"),(16,16)))
     self.subImage = ImageTk.PhotoImage(imageResize(Image.open("icons/subtract.png"),(16,16)))
     self.addb = Button(master,image=self.addImage,text="Add",command=self.addgroup)
     self.addb.grid(row=1,column=0)
     self.subb = Button(master,image=self.subImage,text="Sub",command=self.subgroup)
     self.subb.grid(row=1,column=1)
     self.buttonFrame = VerticalScrolledFrame(master, bd=1, relief=SUNKEN)
     self.buttonFrame.grid(row=0,column=3)

     plugins.loadPlugins()     
     r = 0
     for name in plugins.getOperationNames():
       var = IntVar()
       self.checkboxes[name]=(var,Checkbutton(self.buttonFrame.interior, text=name, variable=var))
       self.checkboxes[name][1].grid(row=r,sticky=W)
       r+=1
     
   def addgroup(self):
     d = tkSimpleDialog.askstring("Add Group", "Name",parent=self)
     if d is not None:
         self.gfl.add(GroupFilter(d,[]))
         self.groupBox.insert(END,d)

   def subgroup(self):
      if len(self.groupBox.curselection()) > 0:
        index = int(self.groupBox.curselection()[0])
        value = self.groupBox.get(index)
        self.gfl.remove(value)
        self.groupBox.delete(index)

   def apply(self):
      if len(self.groupBox.curselection()) > 0:
        index = int(self.groupBox.curselection()[0])
        value = self.groupBox.get(index)
        self.savecondition(value)
      self.gfl.save()
      return

   def savecondition(self,grpName):
      grp = self.gfl.getGroup(grpName)
      grp.filters=[]
      for k,v in self.checkboxes.iteritems():
         if v[0].get() > 0:
             grp.filters.append(k)

   def newgroup(self, event):
      if self.lastselection is not None:
        self.savecondition(self.lastselection)
      index = int(self.groupBox.curselection()[0])
      value = self.groupBox.get(index)
      self.lastselection= value
      grp = self.gfl.getGroup(value)
      for k,v in self.checkboxes.iteritems():
         v[0].set(0)
      if grp is not None:
          for f in grp.filters:
             if f in self.checkboxes:
                 self.checkboxes[f][0].set(1)
      
class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    
    """
    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)            

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

        return
