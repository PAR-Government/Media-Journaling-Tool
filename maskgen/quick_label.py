import argparse

from maskgen.scenario_model import *
from maskgen.description_dialog import *
from maskgen.tool_set import *
from maskgen.maskgen_loader import MaskGenLoader
import shutil
import tarfile


def extract_archive(fname, dir):
    try:
        archive = tarfile.open(fname, "r:gz", errorlevel=2)
    except Exception as e:
        try:
            archive = tarfile.open(fname, "r", errorlevel=2)
        except Exception as e:
            print e
            return False

    if not os.path.exists(dir):
        os.mkdir(dir)
    archive.extractall(dir)
    archive.close()

    return True

def pick_projects(directory):
    """
    Finds all subdirectories in directory containing a .json file
    :param directory: string containing directory of subdirectories to search
    :return: list projects found under the given directory
    """
    ext = '.json'
    subs = [x[0] for x in os.walk(directory)]
    projects = []

    for sub in subs:
        for f in os.listdir(sub):
            if f.endswith(ext):
                projects.append(os.path.join(sub,f))
                break
    return projects

def pick_zipped_projects(directory):
    """
    Finds all subdirectories in directory containing a .json file
    :param directory: string containing directory of subdirectories to search
    :return: list projects found under the given directory
    """
    ext = '.tgz'
    subs = [x[0] for x in os.walk(directory)]
    projects = []

    for sub in subs:
        for f in os.listdir(sub):
            if f.endswith(ext):
                projects.append(os.path.join(sub,f))
    return projects

class QuickLabel(Frame):
    prefLoader = MaskGenLoader()
    img1 = None
    img2 = None
    img1c = None
    img2c = None
    img1oc = None
    img2oc = None
    l1 = None
    currentProject = None
    zippedProject = -1
    edgesToSee = list()
    zippedProjects = list()
    name = ''
    tempdir = None


    def drawState(self):
        sim = self.scModel.startImage()
        nim = self.scModel.nextImage()
        self.img1 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(sim, (500, 500), nim.size)).toPIL())
        self.img2 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(nim, (500, 500), sim.size)).toPIL())
        self.img3 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(nim, (500, 500), sim.size)).toPIL())
        self.img1c.config(image=self.img1)
        self.img2c.config(image=self.img2)
        self.img3c.config(image=self.img3)
        self.l1.config(text=self.scModel.startImageName())
        self.maskvar.set(self.scModel.maskStats())

    def gquit(self,event):
        self.file.close()
        Frame.quit(self)

    def gnext(self,event):
        if self.zippedProject >= 0:
           if self.selectionBox.get() == '':
               return
           self.file.write(self.currentProject.getName() + ',' + self.nextEdge[0][0] +',' + self.nextEdge[0][1] + ',' + self.selectionBox.get() + '\n')
           self.file.flush()
        if self.currentProject is None or len(self.edgesToSee) == 0:
            if self.currentProject is not None:
               print 'Project updated [' + str(self.count) + '/' + str(self.total) + '] ' + self.name
               self.count += 1
            self.zippedProject += 1
            if self.tempdir is not None:
                shutil.rmtree(self.tempdir)
            if self.zippedProject < len(self.zippedProjects):
                self.tempdir = tempfile.mkdtemp()
                if extract_archive(self.zippedProjects[self.zippedProject], self.tempdir):
                   projects = pick_projects(self.tempdir)
                   self.name = projects[0]
                   self.currentProject= ImageProjectModel(projects[0])
                   self.edgesToSee = [y for y in [
                       (x,self.currentProject.getGraph().get_edge(x[0],x[1])) for x in self.currentProject.getGraph().get_edges()]
                                      if y[1]['op'] in  ['PasteSplice',"PasteDuplicate"]]
            else:
                print 'done'
                self.gquit(None)
                return
        if len(self.edgesToSee) == 0:
            return self.gnext(None)
        self.nextEdge = self.edgesToSee[0]
        self.edgesToSee = self.edgesToSee[1:]
        self.sim = self.currentProject.getGraph().get_image(self.nextEdge[0][0])
        self.nim = self.currentProject.getGraph().get_image(self.nextEdge[0][1])
        mask = self.currentProject.getGraph().get_edge_image(self.nextEdge[0][0], self.nextEdge[0][1], 'maskname')
        self.img1 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(self.sim[0], (500, 500), self.nim[0].size)).toPIL())
        self.img2 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(self.nim[0], (500, 500), self.sim[0].size)).toPIL())
        self.img3 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(mask[0], (500, 500), mask[0].size)).toPIL())
        self.img1c.config(image=self.img1)
        self.img2c.config(image=self.img2)
        self.img3c.config(image=self.img3)
        d = self.nextEdge[1]['description'] if 'description' in self.nextEdge[1] else ''
        self.l2.config(text=d)
        self.l1.config(text=os.path.split(self.nim[1])[1])

    def openStartImage(self):
        openFile(self.sim[1])

    def openNextImage(self):
            openFile(self.nim[1])

    def _setTitle(self):
        self.master.title("Semantics Updater")

    def createWidgets(self):
        self._setTitle()

        self.bind_all('<Control-q>', self.gquit)
        self.bind_all('<Control-n>', self.gnext)

        self.grid()
        self.master.rowconfigure(0, weight=1)
        self.master.rowconfigure(1, weight=1)
        self.master.rowconfigure(2, weight=1)
        self.master.rowconfigure(3, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.master.columnconfigure(1, weight=1)

        img1f = img2f = self.master

        self.img1 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "black"))
        self.img2 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "black"))
        self.img3 = ImageTk.PhotoImage(Image.new("RGB", (500, 500), "black"))

        self.img1c = Button(img1f, width=250, command=self.openStartImage, image=self.img1)
        self.img1c.grid(row=1, column=0)
        self.img2c = Button(img1f, width=250, command=self.openNextImage, image=self.img2)
        self.img2c.grid(row=1, column=1)
        self.img3c = Button(img1f, width=250, command=self.openStartImage, image=self.img3)
        self.img3c.grid(row=1, column=2)

        self.l1 = Label(img1f, text="")
        self.l1.grid(row=0, column=0,columnspan=2)

        iframe = Frame(self.master, bd=2, relief=SUNKEN)
        iframe.grid_rowconfigure(0, weight=1)
        iframe.grid_columnconfigure(0, weight=1)
        self.selectionBox = ttk.Combobox(iframe, values=["landscape","other","people","face","natural object","man-made object","large man-made object"], takefocus=True)
        self.selectionBox.grid(row=0, column=0)
        Button(iframe,  command=lambda: self.gnext(None), text='Next').grid(row=0,column=1)
        self.l2 = Label(img1f, text="")
        self.l2.grid(row=2,column=0)
        iframe.grid(row=2,column=1, columnspan=2)
        self.gnext(None)




    def __init__(self, dir, master=None):
        Frame.__init__(self, master)
        self.zippedProjects = pick_zipped_projects(dir)
        self.total = len(self.zippedProjects)
        self.count = 1
        self.createWidgets()
        self.file = open('semantics.csv','w')


def main(argv=None):
    if (argv is None):
        argv = sys.argv

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--projectdir', help=' directory of projects', nargs=1)
    args = parser.parse_args()
    root = Tk()

    gui = QuickLabel(args.projectdir[0])
    gui.mainloop()


if __name__ == "__main__":
    sys.exit(main())
