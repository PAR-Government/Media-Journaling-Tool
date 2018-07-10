import maskgen.scenario_model
import os
import maskgen.image_graph
import tkMessageBox
from Tkinter import *
import ttk

class ExportWatcherDialouge(Toplevel):
    def __init__(self, parent):
        self.parent = parent
        Toplevel.__init__(self, parent)
        self.exdir = os.path.join(os.path.expanduser('~'),'ExportLogs')
        self.createWidgets()

    def createWidgets(self):
        mainFrame = Frame(self)
        for f in os.listdir(self.exdir):
            ep = ExportProgress(mainFrame,os.path.join(self.exdir,f))
            ep.pack()
        mainFrame.pack()


class ExportProgress(Frame):
    def __init__(self, parent, tfile):
        self.parent = parent
        self.file = tfile
        Frame.__init__(self,parent)
        self.pb = ttk.Progressbar(self)
        self.percentlbltxt = StringVar()
        self.percentlbltxt.set(self.getdata()[1])
        self.percentlbl = Label(self, textvariable=self.percentlbltxt)
        self.prjlbl = Label(self,text= os.path.splitext(os.path.split(tfile)[1])[0] + ":")
        self.prjlbl.grid(row=0,column=0)
        self.pb.grid(row=0,column=1)
        self.percentlbl.grid(row=0,column=2)
        Button(self, text='STOP', command=self.stop, width=20).grid(column=3, row=0, sticky=E, padx=5,
                                                                                    pady=5)
        self.update()

    def getdata(self):
        f = (open(self.file))
        data = f.readlines()
        f.close()
        self.pid = int(data[0])
        if len(data)>1:
            start = data[-1].index('(')+1 if '(' in data[-1] else 0
            end = data[-1].index('%') if '%' in data[-1] else 2
            percent = data[-1][start:end]
            if percent.lower() == 'do':
                percent = 100, 'Complete'
            else:
                percent = int(percent),'Working {}%'.format(percent)
            return percent
        return 0, "Initiating"

    def getPid(self):
        return self.pid

    def update(self):
        try:
            os.kill(self.pid,0)
        except WindowsError:
            pass
        except Exception:
            status,text = self.getdata()
            if text != 'Complete':
                self.percentlbltxt.set('FAILED')
            else:
                self.setpb(99.999999)
            return
        status, text = self.getdata()
        self.setpb(status)
        self.percentlbltxt.set(text)
        self.percentlbl.after(1000, self.update, )

    def setpb(self,x):
        self.pb['value']=x

    def stop(self):
        try:
            return
            os.kill(self.pid, 7)
        except:
            tkMessageBox.showerror("Stop Failed", "Failed to stop export process possible lack of permissions")