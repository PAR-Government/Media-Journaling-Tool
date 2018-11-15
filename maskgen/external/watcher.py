import os
import tkMessageBox
import ttk
from Tkinter import *
from exporter import ExportManager

class ExportWatcherDialog(Toplevel):
    def __init__(self, parent, export_manager):
        """

        :param parent:
        :param export_manager:
        @type export_manager: ExportManager
        """
        self.parent = parent
        self.export_manager = export_manager
        self.export_manager.set_notifier(self)
        Toplevel.__init__(self, parent)
        self.progress = {}
        self.createWidgets()

    def _delete_window(self):
        print "delete_window"
        self.export_manager.set_notifier()
        Toplevel.destroy(self)

    def createWidgets(self):
        self.mainFrame = Frame(self)
        self.header = Frame(self.mainFrame)
        self.headerlbl = Label(self.header, text='File Name \t\t Progress/Status \t')
        self.headerlbl.pack()
        self.header.pack()
        self.mainFrame.pack()
        self.update_data()
        self.protocol("WM_DELETE_WINDOW", self._delete_window)

    def __call__(self,*args):
        current_processes = self.export_manager.get_current()
        if args[0] not in current_processes or args[0] not in self.progress:
            self.update_data()
        else:
            self.progress[args[0]].update(*current_processes[args[0]])

    def update_data(self):
        history = self.export_manager.get_all()
        for name, tuple_ in history.iteritems():
            if name not in self.progress:
                ep = ExportProgress(self, name, tuple_[0], tuple_[1])
                ep.pack()
                self.progress[name] = ep
            else:
                self.progress[name].update(*tuple_)

    def forget(self, name):
        self.export_manager.forget(name)
        if name  in self.progress:
            self.progress[name].grid_forget()
            self.progress[name].destroy()
            self.progress.pop(name)


class ExportProgress(Frame):
    def __init__(self, parent, name, timestamp, status):
        """

        :param parent:
        :param name:
        :param timestamp:
        :param status:
        @type timestamp: float
        @type export_manager: ExportManager
        """
        self.parent = parent
        self.name = name

        Frame.__init__(self,parent.mainFrame)
        self.pb = ttk.Progressbar(self)
        self.percentlbltxt = StringVar()
        self.percentlbltxt.set(status)
        self.percentlbl = Label(self, textvariable=self.percentlbltxt)
        self.prjlbl = Label(self,text= name + ":")
        self.prjlbl.grid(row=0,column=0)
        self.pb.grid(row=0,column=1)
        self.percentlbl.grid(row=0,column=2)
        self.stoptxt = StringVar()
        self.stoptxt.set('Remove')
        self.stop = Button(self, textvariable=self.stoptxt, command=self.stop, width=10,state=ACTIVE)
        self.stop.grid(column=3, row=0, sticky=E, padx=5, pady=5)
        self.update(timestamp, status)

    def update(self, timestamp, status):
        if status == 'DONE':
            self.stoptxt.set('Remove')
            self.percentlbltxt.set('Complete')
            self.setpb(99.999999)
        elif status == 'FAIL':
            self.stoptxt.set('Restart')
            self.percentlbltxt.set('Failed')
        else:
            self.stoptxt.set('Stop')
            try:
                self.setpb(float(status))
            except:
                self.setpb(0)
            self.percentlbltxt.set(status)
        return


    def setpb(self,x):
        self.pb['value']=x

    def stop(self):
        state = self.stoptxt.get()
        if state == 'Stop':
            self.parent.export_manager.stop(self.name)
        elif state == 'Remove':
            self.parent.forget(self.name)
        else:
            if not self.parent.export_manager.restart(self.name):
                tkMessageBox.showerror('Restart','Cannot restart {}. File cannot be found.'.format(self.name))

