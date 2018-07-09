import maskgen.scenario_model
import os
import maskgen.image_graph
import Tkinter
from Tkinter import Toplevel
from Tkinter import *
import ttk

class ExportWatcherDialouge(Toplevel):
    def __init__(self, parent):
        self.parent = parent
        Toplevel.__init__(self, parent)
        self.exdir = os.path.join(os.path.expanduser('~'),'ExportLogs')

    def createWidgets(self):
        mainFrame = Frame(self)



class ExportProgress(Frame):
    def __init__(self, parent, tfile):
        self.parent = parent
        self.file = tfile
        Frame.__init__(self,parent)
        self.pb = ttk.Progressbar(self)
        self.percentlbltxt = StringVar()
        self.percentlbltxt = self.getdata()
        self.percentlbl = Label(self, textVariable=self.percentlbltxt)
        self.prjlbl = Label(self,text= os.path.splitext(os.path.split(tfile)[1])[0])

    def getdata(self):
        f = (open(self.file))
        data = f.readlines()
        f.close()
        self.pid = int(data[0])
        if len(data>1):
            percent = data[-1][-4:-1]
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

    def setpb(self,x):
        self.pb.step(x - self.pb.location)
