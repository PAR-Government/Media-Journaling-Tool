import ttk
from Tkinter import *
import  tkSimpleDialog
import tkFont
from scenario_model import ImageProjectModel,Modification

class HistoryDialog(tkSimpleDialog.Dialog):

    def __init__(self, master,scModel):
        """

        :param master:
        :param scModel:
         @type scModel: ImageProjectModel
        """
        self.parent = master
        self.scModel = scModel
        tkSimpleDialog.Dialog.__init__(self, master,'History')

    def body(self, master):
        self.history_frame  =  HistoryFrame(master,self.scModel)
        self.history_frame.grid(row=0)

    #def buttons(self, frame):
    #    return Button(frame, text="OK", width=10, command=self.cancel, default=ACTIVE)

class HistoryFrame(Frame):

    """ Display a table of operations, in lieu of the graph view
    """
    modifications = []

    def __init__(self, master,scModel):
        """
               :param master:
               :param scModel:
                @type scModel: ImageProjectModel
        """
        Frame.__init__(self, master)
        self.createWidgets()
        self.loadData(scModel)

    def focus(self):
       return self.tree.focus()

    def createWidgets(self):
        # create the tree and scrollbars
        self.dataCols = ('Operation', 'Start', 'End', 'Time','User','Description')
        self.tree = ttk.Treeview(self, columns=self.dataCols,show='headings',selectmode='browse',displaycolumns='#all')
        self.tree.column('Operation', width=120 )
        self.tree.column('Start', width=120)
        self.tree.column('End', width=120)
        self.tree.column('User', width=120)
        self.tree.column('Time', width=120)
        self.tree.column('Description', width=750)
        self.tree.heading("Operation", text="Operation")
        self.tree.heading("Start", text="Start")
        self.tree.heading("End", text="End")
        self.tree.heading("User", text="User")
        self.tree.heading("Time", text="Time")
        self.tree.heading("Description", text="Description")
         
        ysb = ttk.Scrollbar(self,orient=VERTICAL, command= self.tree.yview)
        xsb = ttk.Scrollbar(self,orient=HORIZONTAL, command= self.tree.xview)
        self.tree['yscroll'] = ysb.set
        self.tree['xscroll'] = xsb.set
         
        # add tree and scrollbars to frame
        self.tree.grid(row=0, column=0, sticky=NSEW)
        ysb.grid( row=0, column=1, sticky=NS)
        xsb.grid(row=1, column=0, sticky=EW)
         
    def clearData(self):
       for mod in self.modifications:
         self.tree.delete(mod.maskFileName)
       self.modifications = []

    def loadData(self, scModel):
        """
        :param scModel:
        :return: None
        @type scModel : ImageProjectModel
        """
        self.modifications = sorted(scModel.getDescriptions(), key=lambda mod: mod.ctime, reverse=True)
        for moddata in self.modifications:
            self._load(moddata)

    def _load(self, mod):
        """
        :param start:
        :param end:
        :param mod:
        :return:
        @type start: str
        @type end: str
        @type mod: Modification
        """
        item = (mod.operationName, mod.start,mod.end, mod.ctime, mod.username, mod.additionalInfo)
        self.tree.insert('', 'end',iid=mod.inputMaskName, values=item)
        # and adjust column widths if necessary
        for idx, val in enumerate(item):
            iwidth = tkFont.Font().measure(val)
            if self.tree.column(self.dataCols[idx], 'width') < iwidth:
               self.tree.column(self.dataCols[idx], width = iwidth)
         
