from Tkinter import *
import ttk
import tkFont
 
class HistoryFrame(ttk.Frame):

    modifications = []

    def __init__(self, master):
        ttk.Frame.__init__(self, master)
        self.parent = master
        self.createWidgets()

    def focus(self):
        return self.tree.focus()

    def createWidgets(self):
         
        # create the tree and scrollbars
        self.dataCols = ('Operation', 'Mask Name', 'Description')
        self.tree = ttk.Treeview(columns=self.dataCols,show='headings',selectmode='browse',displaycolumns='#all')
        self.tree.column('Operation', width=250 )
        self.tree.column('Mask Name', width=250)
        self.tree.column('Description', width=1000)
        self.tree.heading("Operation", text="Operation")
        self.tree.heading("Mask Name", text="Mask Name")
        self.tree.heading("Description", text="Description")
         
        ysb = ttk.Scrollbar(orient=VERTICAL, command= self.tree.yview)
        xsb = ttk.Scrollbar(orient=HORIZONTAL, command= self.tree.xview)
        self.tree['yscroll'] = ysb.set
        self.tree['xscroll'] = xsb.set
         
        # add tree and scrollbars to frame
        self.tree.grid(in_=self, row=0, column=0, sticky=NSEW)
        ysb.grid(in_=self, row=0, column=1, sticky=NS)
        xsb.grid(in_=self, row=1, column=0, sticky=EW)
         
    def clearData(self):
      for mod in self.modifications:
        self.tree.delete(mod.maskFileName)

    def loadData(self, modifications):
        self.modifications = modifications
                 
        # configure column headings
        i = 1
        for c in self.dataCols:
            self.tree.heading(c, text=c.title())
#                              command=lambda c=c: self._column_sort(c, MCListDemo.SortDir))           
            self.tree.column(c, width=tkFont.Font().measure(c.title())*i)
            i+=1

        # add data to the tttk.Treeviewree
        for mod in modifications:
            addModification(mod)

    def addModification(self, mod):
        item = (mod.operationName, mod.maskFileName, mod.additionalInfo)
        self.tree.insert('', 'end',iid=mod.maskFileName, values=item)
             
            # and adjust column widths if necessary
        for idx, val in enumerate(item):
            iwidth = tkFont.Font().measure(val)
            if self.tree.column(self.dataCols[idx], 'width') < iwidth:
               self.tree.column(self.dataCols[idx], width = iwidth)
         
