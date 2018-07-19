import os
import tkMessageBox
from Tkinter import *
import ttk

from maskgen.export.lock_handler import get_lock_handler


class ExportWatcherDialouge(Toplevel):
    def __init__(self, parent):
        self.parent = parent
        Toplevel.__init__(self, parent)
        self.exdir = os.path.join(os.path.expanduser('~'),'ExportLogs')
        self.files = []
        self.createWidgets()

    def createWidgets(self):
        self.mainFrame = Frame(self)
        self.header = Frame(self.mainFrame)
        self.headerlbl = Label(self.header, text='File Name \t\t Progress/Status \t')
        self.headerlbl.pack()
        self.header.pack()
        if not os.path.isdir(self.exdir):
            os.mkdir(self.exdir)
        self.checkDir()
        self.mainFrame.pack()
        self.after(1000,self.checkDir)

    def checkDir(self):
        for f in os.listdir(self.exdir):
            if f not in self.files:
                self.files.append(f)
                ep = ExportProgress(self.mainFrame,os.path.join(self.exdir,f))
                ep.pack()

class ExportProgress(Frame):
    def __init__(self, parent, tfile):
        self.parent = parent
        self.file = tfile
        Frame.__init__(self,parent)
        self.locks = get_lock_handler()
        self.locks.new(tfile)
        self.pb = ttk.Progressbar(self)
        self.percentlbltxt = StringVar()
        self.percentlbltxt.set(self.getdata()[1])
        self.percentlbl = Label(self, textvariable=self.percentlbltxt)
        self.prjlbl = Label(self,text= os.path.splitext(os.path.split(tfile)[1])[0] + ":")
        self.prjlbl.grid(row=0,column=0)
        self.pb.grid(row=0,column=1)
        self.percentlbl.grid(row=0,column=2)
        self.stop = Button(self, text='STOP', command=self.stop, width=10)
        self.stop.grid(column=3, row=0, sticky=E, padx=5, pady=5)
        self.stopped = False
        self.removebtn = Button(self, text='Remove', command=self.remove, width=10)
        self.removebtn.grid(column=4, row=0, sticky=E, padx=5, pady=5)
        self.update()

    def getdata(self):
        self.locks.get(self.file).acquire(True)
        f = (open(self.file))
        data = f.readlines()
        f.close()
        self.locks.get(self.file).release()
        self.pid = int(data[0])
        if len(data)>1:
            start = data[-1].index('(')+1 if '(' in data[-1] else 0
            end = data[-1].index('%') if '%' in data[-1] else 2
            percent = data[-1][start:end]
            if percent.lower() == 'do':
                percent = 100, 'Complete'
            elif percent.lower() == 'fa':
                percent = 0, 'Failed'
            else:
                percent = float(percent),'Working {}%'.format(percent)
            return percent
        return 0, "Initiating"

    def getPid(self):
        return self.pid

    def update(self):
        # This causes control-C event but was a good thought
        # try:
        #     os.kill(self.pid,0)
        # except WindowsError:
        #     pass
        # except Exception:
        #     status,text = self.getdata()
        #     if text != 'Complete':
        #         self.percentlbltxt.set('FAILED')
        #     else:
        #         self.setpb(99.999999)
        #     return

        status, text = self.getdata()
        if text == 'Complete':
            self.percentlbltxt.set('Complete')
            self.setpb(99.999999)
            self.stop.configure(state=DISABLED)
            #return
        elif text == 'Failed':
            self.stop.configure(state=DISABLED)
            self.percentlbltxt.set('Failed')
        else:
            self.stop.configure(state=ACTIVE)
            self.setpb(status)
            self.percentlbltxt.set(text)
        if not self.stopped:
            self.percentlbl.after(1000, self.update, )
        return


    def remove(self):
        if self.percentlbltxt.get() in ['Failed','Complete','STOPPED']:
            os.remove(self.file)
            self.grid_forget()
            self.destroy()
    def setpb(self,x):
        self.pb['value']=x
    def stop(self):
        try:
            os.kill(self.pid, 7)
            self.stop.configure(state=DISABLED)
            self.percentlbltxt.set('STOPPED')
            self.stopped = True
        except:
            tkMessageBox.showerror("Stop Failed", "Failed to stop export process possible lack of permissions")
