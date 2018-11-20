import tkMessageBox
import ttk
from Tkinter import *
from exporter import ExportManager
from threading import Lock

class ExportWatcherDialog(Toplevel):
    def __init__(self, parent, export_manager):
        """

        :param parent:
        :param export_manager:
        @type export_manager: ExportManager
        """
        self.parent = parent
        self.export_manager = export_manager
        self.export_manager.add_notifier(self)
        Toplevel.__init__(self, parent)
        self.progress = {}
        self.lock = Lock()
        self.createWidgets()

    def _delete_window(self):
        self.export_manager.remove_notifier(self)
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
        if args[0] not in self.progress:
            self.update_data()
        else:
            with self.lock:
                self.progress[args[0]].update(args[1],args[2])

    def update_data(self):
        history = self.export_manager.get_all()
        for name, tuple_ in history.iteritems():
            ep = None
            with self.lock:
                if name not in self.progress:
                    ep = ExportProgress(self, name, tuple_[0], tuple_[1])
                    self.progress[name] = ep
                else:
                    self.progress[name].update(*tuple_)
            if ep is not None:
                ep.pack()

    def forget(self, name):
        self.export_manager.forget(name)
        frame = None
        with self.lock:
            if name in self.progress:
                frame = self.progress[name]
                self.progress.pop(name)
        frame.grid_forget()
        frame.destroy()


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
        self.timestamp = timestamp
        self.process_status = status

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
        self.timestamp = timestamp
        self.process_status = status
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
                self.parent.forget(self.name)

