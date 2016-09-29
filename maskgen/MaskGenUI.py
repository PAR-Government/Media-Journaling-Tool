import argparse

from botocore.exceptions import ClientError
from graph_canvas import MaskGraphCanvas
from scenario_model import *
from description_dialog import *
from software_loader import loadOperations, loadSoftware, getOperation
from tool_set import *
from group_manager import GroupManagerDialog
from maskgen_loader import MaskGenLoader
from group_operations import CopyCompressionAndExifGroupOperation
from web_tools import *

"""
  Main UI Driver for MaskGen
"""

"""
  Profiles are used to customize the bevahior depending on the type of project.
  There are two profiles: video and image
"""


def toFileTypeString(types):
    str = ''
    for ft in types:
        str += ft[1] + ' '
    return str


def fromFileTypeString(types, profileTypes):
    typelist = types.split(' ')
    result = []
    for ft in typelist:
        ft = ft.strip()
        if len(ft) == 0:
            continue
        ptype = [x for x in profileTypes if x[1] == ft]
        if len(ptype) > 0:
            result.append(ptype[0])
        else:
            result.append((ft, ft))
    return result


def projectProperties():
    return [('User Name', 'username', 'string'), ('Organization', 'organization', 'string'),
            ('Description', 'projectdescription', 'text'), ('Technical Summary', 'technicalsummary', 'text'),
            ('Manipulation Category', 'manipulationcategory', 'list', ('Provenance', '2-Unit', '4-Unit', '6-Unit')),
            ('Manipulation Pixel Size', 'manipulationpixelsize', 'list', ('Small', 'Medium', 'Large')),
            ('Remove', 'remove', 'yesno'),
            ('Splice', 'splice', 'yesno'), ('Clone', 'clone', 'yesno'), ('Resize', 'resize', 'yesno'),
            ('Seam Carving', 'seamcarving', 'yesno'), ('Warping', 'warping', 'yesno'),
            ('Blur Local', 'blurlocal', 'yesno'),
            ('Healing Local', 'healinglocal', 'yesno'),
            ('Histogram Normalization Global', 'histogramnormalizationglobal', 'yesno'),
            ('Other Enhancements', 'otherenhancements', 'yesno'), ('Man-Made', 'manmade', 'yesno'),
            ('Face', 'face', 'yesno'), ('People', 'people', 'yesno'), ('Large Man-Made', 'largemanmade', 'yesno'),
            ('Landscape', 'landscape', 'yesno'), ('Other Subjects', 'othersubjects', 'yesno'),
            ('PRNU', 'prnu', 'yesno'), ('Image Compression', 'imagecompression', 'yesno'),
            ('Laundering: Social Media', 'launderingsocialmedia', 'yesno'),
            ('Laundering: Median Filtering', 'launderingmedianfiltering', 'yesno')]


class UIProfile:
    suffixes = ["*.nef", ".jpg", ".png", ".tiff", "*.bmp", ".avi", ".mp4", ".mov", "*.wmv"]
    operations = 'operations.json'
    software = 'software.csv'
    name = 'Image/Video'

    def getFactory(self):
        return imageProjectModelFactory

    def addProcessCommand(self, menu, parent):
        menu.add_command(label="Create JPEG/TIFF", command=parent.createJPEGorTIFF, accelerator="Ctrl+J")
        menu.add_separator()

    def addAccelerators(self, parent):
        parent.bind_all('<Control-j>', lambda event: parent.after(100, parent.createJPEGorTIFF))


class MakeGenUI(Frame):
    prefLoader = MaskGenLoader()
    img1 = None
    img2 = None
    img3 = None
    img1c = None
    img2c = None
    img3c = None
    img1oc = None
    img2oc = None
    img3oc = None
    scModel = None
    l1 = None
    l2 = None
    l3 = None
    processmenu = None
    mypluginops = {}
    nodemenu = None
    edgemenu = None
    filteredgemenu = None
    canvas = None
    errorlistDialog = None
    exportErrorlistDialog = None
    uiProfile = UIProfile()
    menuindices = {}

    gfl = GroupFilterLoader()

    if prefLoader.get_key('username') is not None:
        setPwdX(CustomPwdX(prefLoader.get_key('username')))

    def _check_dir(self, dir):
        set = [filename for filename in os.listdir(dir) if filename.endswith('.json')]
        return not len(set) > 0

    def setSelectState(self, state):
        self.processmenu.entryconfig(1, state=state)
        self.processmenu.entryconfig(2, state=state)
        self.processmenu.entryconfig(3, state=state)
        self.processmenu.entryconfig(4, state=state)
        self.processmenu.entryconfig(5, state=state)

    def new(self):
        val = tkFileDialog.askopenfilename(initialdir=self.scModel.get_dir(), title="Select base image file",
                                           filetypes=getFileTypes())
        if val is None or val == '':
            return
        dir = os.path.split(val)[0]
        if (not self._check_dir(dir)):
            tkMessageBox.showinfo("Error", "Directory already associated with a project")
            return
        self.scModel.startNew(val, suffixes=self.uiProfile.suffixes,
                              organization=self.prefLoader.get_key('organization'))
        if self.scModel.getProjectData('typespref') is None:
            self.scModel.setProjectData('typespref', getFileTypes())
        self._setTitle()
        self.drawState()
        self.canvas.update()
        self.setSelectState('disabled')
        self.getproperties()

    def about(self):
        tkMessageBox.showinfo('About', 'Version: ' + self.scModel.getVersion())

    def open(self):
        val = tkFileDialog.askopenfilename(initialdir=self.scModel.get_dir(), title="Select project file",
                                           filetypes=[("json files", "*.json")])
        if (val != None and len(val) > 0):
            self.scModel.load(val)
            if self.scModel.getProjectData('typespref') is None:
                self.scModel.setProjectData('typespref', getFileTypes())
            self._setTitle()
            self.drawState()
            self.canvas.update()
            if (self.scModel.start is not None):
                self.setSelectState('normal')

    def add(self):
        val = tkFileDialog.askopenfilenames(initialdir=self.scModel.get_dir(), title="Select image file(s)",
                                            filetypes=self.getPreferredFileTypes())
        if (val != None and len(val) > 0):
            self.updateFileTypes(val[0])
            try:
                self.canvas.addNew([self.scModel.addImage(f) for f in val])
                self.processmenu.entryconfig(self.menuindices['undo'], state='normal')
            except IOError:
                tkMessageBox.showinfo("Error", "Failed to load image " + self.scModel.startImageName())
            self.setSelectState('normal')

    def save(self):
        self.scModel.save()

    def saveas(self):
        val = tkFileDialog.asksaveasfile(initialdir=self.scModel.get_dir(), title="Save As",
                                         filetypes=[("json files", "*.json")])
        if (val is not None and len(val.name) > 0):
            dir = os.path.abspath(os.path.split(val.name)[0])
            if (dir == os.path.abspath(self.scModel.get_dir())):
                tkMessageBox.showwarning("Save As", "Cannot save to the same directory\n(%s)" % dir)
            else:
                self.scModel.saveas(val.name)
                self._setTitle()
            val.close()

    def export(self):
        errorList = self.scModel.validate()
        if errorList is not None and len(errorList) > 0:
            errorlistDialog = DecisionListDialog(self, errorList, "Validation Errors")
            errorlistDialog.wait(self)
            if not errorlistDialog.isok:
                return
        val = tkFileDialog.askdirectory(initialdir='.', title="Export To Directory")
        if (val is not None and len(val) > 0):
            errorList = self.scModel.export(val)
            if len(errorList) > 0:
                if self.exportErrorlistDialog is None:
                    self.exportErrorlistDialog = ListDialog(self, errorList, "Export Errors")
                else:
                    self.exportErrorlistDialog.setItems(errorList)
            else:
                tkMessageBox.showinfo("Export", "Complete")

    def exporttoS3(self):
        errorList = self.scModel.validate()
        if errorList is not None and len(errorList) > 0:
            errorlistDialog = DecisionListDialog(self, errorList, "Validation Errors")
            errorlistDialog.wait(self)
            if not errorlistDialog.isok:
                return
        info = self.prefLoader.get_key('s3info')
        val = tkSimpleDialog.askstring("S3 Bucket/Folder", "Bucket/Folder",
                                       initialvalue=info if info is not None else '')
        if (val is not None and len(val) > 0):
            try:
                errorList = self.scModel.exporttos3(val)
                if len(errorList) > 0:
                    if self.exportErrorlistDialog is None:
                        self.exportErrorlistDialog = ListDialog(self, errorList, "Export Errors")
                    else:
                        self.exportErrorlistDialog.setItems(errorList)
                else:
                    tkMessageBox.showinfo("Export to S3", "Complete")
                    self.prefLoader.save('s3info', val)
            except IOError:
                tkMessageBox.showinfo("Error", "Failed to upload export")

    def createJPEGorTIFF(self):
        msg, pairs = CopyCompressionAndExifGroupOperation(self.scModel).performOp(self.master)
        if msg is not None:
            tkMessageBox.showwarning("Error", msg)
            if not pairs:
                return
        if len(pairs) == 0:
            tkMessageBox.showwarning("Warning", "Leaf image nodes with base JPEG images do not exist in this project")
        for pair in pairs:
            self.canvas.add(pair[0], pair[1])
        self.drawState()

    def setorganization(self):
        name = self.prefLoader.get_key('organization')
        if name is None:
            name = 'Performer'
        newName = tkSimpleDialog.askstring("Set Organization", "Name", initialvalue=name)
        if newName is not None:
            self.prefLoader.save('organization', newName)
            self.scModel.setProjectData('organization', newName)

    def setusername(self):
        name = get_username()
        newName = tkSimpleDialog.askstring("Set Username", "Username", initialvalue=name)
        if newName is not None:
            self.prefLoader.save('username', newName)
            setPwdX(CustomPwdX(self.prefLoader.get_key('username')))
            self.scModel.setProjectData('username', newName)

    def setPreferredFileTypes(self):
        filetypes = self.getPreferredFileTypes()
        newtypesStr = tkSimpleDialog.askstring("Set File Types", "Types", initialvalue=toFileTypeString(filetypes))
        if newtypesStr is not None:
            self.prefLoader.save('filetypes', fromFileTypeString(newtypesStr, getFileTypes()))
            self.scModel.setProjectData('typespref', fromFileTypeString(newtypesStr, getFileTypes()))

    def undo(self):
        self.scModel.undo()
        self.drawState()
        self.canvas.update()
        self.processmenu.entryconfig(self.menuindices['undo'], state='disabled')
        self.setSelectState('disabled')

    def updateFileTypes(self, filename):
        if filename is None or len(filename) == 0:
            return

        suffix = filename[filename.rfind('.'):]
        place = 0
        top = None
        allPlace = 0
        prefs = self.getPreferredFileTypes()
        for pref in prefs:
            if pref[1] == '*.*':
                allPlace = place
            if pref[1] == '*' + suffix:
                top = pref
                break
            place += 1
        if top is not None and place > 0:
            prefs[place] = prefs[0]
            prefs[0] = top
            self.scModel.setProjectData('typespref', prefs)
        elif top is None and allPlace > 0:
            top = prefs[0]
            prefs[0] = prefs[allPlace]
            prefs[allPlace] = top

    def getPreferredFileTypes(self):
        return [tuple(x) for x in self.scModel.getProjectData('typespref')]

    def nextadd(self):
        val = tkFileDialog.askopenfilename(initialdir=self.scModel.get_dir(), title="Select image file",
                                           filetypes=self.getPreferredFileTypes())
        self.updateFileTypes(val)
        file, im = self.scModel.openImage(val)
        if (file is None or file == ''):
            return
        filetype = fileType(file)
        d = DescriptionCaptureDialog(self, self.uiProfile, self.scModel.getStartType(), filetype,
                                     self.scModel.get_dir(), im, os.path.split(file)[1])
        if (
                    d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            msg, status = self.scModel.addNextImage(file, mod=d.description)
            if msg is not None:
                tkMessageBox.showwarning("Auto Connect", msg)
            if status:
                self.drawState()
                self.canvas.add(self.scModel.start, self.scModel.end)
                self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def nextauto(self):
        destination = self.scModel.scanNextImageUnConnectedImage()
        if destination is None:
            tkMessageBox.showwarning("Auto Connect", "No suitable loaded images found")
            return
        im, filename = self.scModel.getImageAndName(destination)
        filetype = fileType(filename)
        d = DescriptionCaptureDialog(self, self.uiProfile, self.scModel.getStartType(), filetype,
                                     self.scModel.get_dir(), im, os.path.split(filename)[1])
        if (
                    d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            self.scModel.connect(destination, mod=d.description)
            self.drawState()
            self.canvas.add(self.scModel.start, self.scModel.end)
            self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def nextautofromfile(self):
        im, filename = self.scModel.scanNextImage()
        if (filename is None):
            tkMessageBox.showwarning("Auto Connect", "Next image file cannot be automatically determined")
            return
        filetype = fileType(filename)
        d = DescriptionCaptureDialog(self, self.uiProfile, self.scModel.getStartType(), filetype,
                                     self.scModel.get_dir(), im, os.path.split(filename)[1])
        if (
                    d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            msg, status = self.scModel.addNextImage(filename, mod=d.description)
            if msg is not None:
                tkMessageBox.showwarning("Auto Connect", msg)
            if status:
                self.drawState()
                self.canvas.add(self.scModel.start, self.scModel.end)
                self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def resolvePluginValues(self, args):
        result = {}
        for k, v in args.iteritems():
            result[k] = v
        result['sendNotifications'] = False
        return result

    def _addPairs(self, pairs):
        for pair in pairs:
            self.canvas.add(pair[0], pair[1])
        if len(pairs) > 0:
            self.drawState()
            self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def nextfilter(self):
        im, filename = self.scModel.currentImage()
        if (im is None):
            return
        d = FilterCaptureDialog(self, self.scModel.get_dir(), im, plugins.getOperations(), os.path.split(filename)[1],
                                self.scModel)
        if d.optocall is not None:
            msg, pairs = self.scModel.imageFromPlugin(d.optocall, im, filename, **self.resolvePluginValues(d.argvalues))
            if msg is not None:
                tkMessageBox.showwarning("Next Filter", msg)
            self._addPairs(pairs)

    def nextfiltergroup(self):
        im, filename = self.scModel.currentImage()
        if (im is None):
            return
        if len(self.gfl.getGroupNames()) == 0:
            tkMessageBox.showwarning("Next Group Filter", "No groups found")
            return
        d = FilterGroupCaptureDialog(self, im, os.path.split(filename)[1])
        if d.getGroup() is not None:
            start = self.scModel.operationImageName()
            end = None
            ok = False
            for filter in self.gfl.getGroup(d.getGroup()).filters:
                msg, pairs = self.scModel.imageFromPlugin(filter, im, filename)
                self._addPairs(pairs)
                if msg is not None:
                    tkMessageBox.showwarning("Next Filter", msg)
                    break
                ok = True
                end = self.scModel.nextId()
                # reset back to the start image
                self.scModel.selectImage(start)
            # select the last one completed
            self.scModel.select((start, end))
            self.drawState()
            if ok:
                self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def nextfiltergroupsequence(self):
        im, filename = self.scModel.currentImage()
        if (im is None):
            return
        if len(self.gfl.getGroupNames()) == 0:
            tkMessageBox.showwarning("Next Group Filter", "No groups found")
            return
        d = FilterGroupCaptureDialog(self, im, os.path.split(filename)[1])
        if d.getGroup() is not None:
            for filter in self.gfl.getGroup(d.getGroup()).filters:
                msg, pairs = self.scModel.imageFromPlugin(filter, im, filename)
                if msg is not None:
                    tkMessageBox.showwarning("Next Filter", msg)
                    break
                self._addPairs(pairs)
                im, filename = self.scModel.getImageAndName(self.scModel.end)
            self.drawState()
            self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def openStartImage(self):
        sim = self.scModel.getStartImageFile()
        openFile(sim)

    def openNextImage(self):
        if self.scModel.end:
            nim = self.scModel.getNextImageFile()
            openFile(nim)

    def openMaskImage(self):
        return

    def drawState(self):
        sim = self.scModel.startImage()
        nim = self.scModel.nextImage()
        self.img1 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(sim, (250, 250), nim.size)))
        self.img2 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(nim, (250, 250), sim.size)))
        self.img3 = ImageTk.PhotoImage(imageResizeRelative(self.scModel.maskImage(), (250, 250), nim.size))
        self.img1c.config(image=self.img1)
        self.img2c.config(image=self.img2)
        self.img3c.config(image=self.img3)
        self.l1.config(text=self.scModel.startImageName())
        self.l2.config(text=self.scModel.nextImageName())
        self.maskvar.set(self.scModel.maskStats())

    def doneWithWindow(self, window):
        if window == self.errorlistDialog:
            self.errorlistDialog = None
        if window == self.exportErrorlistDialog:
            self.exportErrorlistDialog = None

    def fetchS3(self):
        import graph_rules
        info = self.prefLoader.get_key('s3info')
        val = tkSimpleDialog.askstring("S3 Bucket/Folder", "Bucket/Folder",
                                       initialvalue=info if info is not None else '')
        if (val is not None and len(val) > 0):
            try:
                loadS3([val])
                self.prefLoader.save('s3info', val)
                loadOperations(self.uiProfile.operations)
                loadSoftware(self.uiProfile.software)
                graph_rules.setup()
            except ClientError as e:
                tkMessageBox.showwarning("S3 Download failure", str(e))

    def validate(self):
        errorList = self.scModel.validate()
        if (self.errorlistDialog is None):
            self.errorlistDialog = ListDialog(self, errorList, "Validation Errors")
        else:
            self.errorlistDialog.setItems(errorList)

    def getproperties(self):
        d = PropertyDialog(self, projectProperties())

    def groupmanager(self):
        d = GroupManagerDialog(self)

    def quit(self):
        self.save()
        Frame.quit(self)

    def gquit(self, event):
        self.quit()

    def gopen(self, event):
        self.open()

    def gnew(self, event):
        self.new()

    def gsave(self, event):
        self.save()

    def gundo(self, next):
        self.undo()

    def compareto(self):
        self.canvas.compareto()

    def viewcomposite(self):
        im = self.scModel.constructComposite()
        if im is not None:
            CompositeViewDialog(self, self.scModel.start, im)

    def connectto(self):
        self.drawState()
        self.canvas.connectto()
        self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def exportpath(self):
        val = tkFileDialog.askdirectory(initialdir='.',
                                        title="Export " + self.scModel.startImageName() + " To Directory")
        if (val is not None and len(val) > 0):
            self.scModel.export_path(val)
            tkMessageBox.showinfo("Export", "Complete")

    def selectLink(self, start, end):
        if start == end:
            end = None
        self.scModel.select((start, end))
        self.drawState()
        if end is not None:
            self.canvas.showEdge(start, end)
        else:
            self.canvas.showNode(start)
        self.setSelectState('normal')

    def select(self):
        self.drawState()
        self.setSelectState('normal')

    def changeEvent(self, recipient, eventType):
        if eventType == 'label' and self.canvas is not None:
            self.canvas.redrawNode(recipient)
        #        elif eventType == 'connect':
        #           self.canvas.showEdge(recipient[0],recipient[1])

    def remove(self):
        self.canvas.remove()
        self.drawState()
        self.processmenu.entryconfig(self.menuindices['undo'], state='normal')
        self.setSelectState('disabled')

    def edit(self):
        im, filename = self.scModel.currentImage()
        if (im is None):
            return
        d = DescriptionCaptureDialog(self, self.uiProfile, self.scModel.getStartType(), self.scModel.getEndType(),
                                     self.scModel.get_dir(), im, os.path.split(filename)[1],
                                     description=self.scModel.getDescription())
        if (
                    d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            self.scModel.update_edge(d.description)
        self.drawState()

    def view(self):
        im, filename = self.scModel.currentImage()
        if (im is None):
            return
        d = DescriptionViewDialog(self, self.scModel.get_dir(), im, os.path.split(filename)[1],
                                  description=self.scModel.getDescription(), metadiff=self.scModel.getMetaDiff())

    def viewselectmask(self):
        im, filename = self.scModel.getSelectMask()
        if (im is None):
            return
        name = self.scModel.start + ' to ' + self.scModel.end
        d = CompositeCaptureDialog(self, self.scModel.getStartType(), self.scModel.getEndType(), self.scModel.get_dir(),
                                   im, name, self.scModel.getDescription())
        if not d.cancelled:
            self.scModel.update_edge(d.modification)

    def _setTitle(self):
        self.master.title(os.path.join(self.scModel.get_dir(), self.scModel.getName()))

    def createWidgets(self):
        self._setTitle()

        menubar = Menu(self)

        exportmenu = Menu(tearoff=0)
        exportmenu.add_command(label="To File", command=self.export, accelerator="Ctrl+E")
        exportmenu.add_command(label="To S3", command=self.exporttoS3)

        settingsmenu = Menu(tearoff=0)
        settingsmenu.add_command(label="Username", command=self.setusername)
        settingsmenu.add_command(label="Organization", command=self.setorganization)
        settingsmenu.add_command(label="File Types", command=self.setPreferredFileTypes)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="About", command=self.about)
        filemenu.add_command(label="Open", command=self.open, accelerator="Ctrl+O")
        filemenu.add_command(label="New", command=self.new, accelerator="Ctrl+N")
        filemenu.add_command(label="Save", command=self.save, accelerator="Ctrl+S")
        filemenu.add_command(label="Save As", command=self.saveas)
        filemenu.add_separator()
        filemenu.add_cascade(label="Export", menu=exportmenu)
        filemenu.add_command(label="Validate", command=self.validate)
        filemenu.add_command(label="Fetch Meta-Data(S3)", command=self.fetchS3)
        filemenu.add_command(label="Group Manager", command=self.groupmanager)
        filemenu.add_separator()
        filemenu.add_cascade(label="Settings", menu=settingsmenu)
        filemenu.add_cascade(label="Properties", command=self.getproperties)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")

        menubar.add_cascade(label="File", menu=filemenu)

        self.processmenu = Menu(menubar, tearoff=0)
        self.processmenu.add_command(label="Add " + self.uiProfile.name, command=self.add, accelerator="Ctrl+A")
        self.processmenu.add_command(label="Next w/Auto Pick", command=self.nextauto, accelerator="Ctrl+P",
                                     state='disabled')
        self.processmenu.add_command(label="Next w/Auto Pick from File", command=self.nextautofromfile,
                                     state='disabled')
        self.processmenu.add_command(label="Next w/Add", command=self.nextadd, accelerator="Ctrl+L", state='disabled')
        self.processmenu.add_command(label="Next w/Filter", command=self.nextfilter, accelerator="Ctrl+F",
                                     state='disabled')
        self.processmenu.add_command(label="Next w/Filter Group", command=self.nextfiltergroup, state='disabled')
        self.processmenu.add_command(label="Next w/Filter Sequence", command=self.nextfiltergroupsequence,
                                     state='disabled')
        self.processmenu.add_separator()
        self.uiProfile.addProcessCommand(self.processmenu, self)
        self.processmenu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z", state='disabled')
        self.menuindices['undo'] = self.processmenu.index(END)
        menubar.add_cascade(label="Process", menu=self.processmenu)
        self.master.config(menu=menubar)
        self.bind_all('<Control-q>', self.gquit)
        self.bind_all('<Control-o>', self.gopen)
        self.bind_all('<Control-s>', self.gsave)
        self.bind_all('<Control-a>', lambda event: self.after(100, self.add))
        self.bind_all('<Control-n>', self.gnew)
        self.bind_all('<Control-p>', lambda event: self.after(100, self.nextauto))
        self.bind_all('<Control-l>', lambda event: self.after(100, self.nextadd))
        self.bind_all('<Control-f>', lambda event: self.after(100, self.nextfilter))
        self.bind_all('<Control-z>', self.gundo)
        self.uiProfile.addAccelerators(self)

        self.grid()
        self.master.rowconfigure(0, weight=1)
        self.master.rowconfigure(1, weight=1)
        self.master.rowconfigure(2, weight=1)
        self.master.rowconfigure(3, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.master.columnconfigure(1, weight=1)
        self.master.columnconfigure(2, weight=1)

        img1f = img2f = img3f = self.master

        self.img1 = ImageTk.PhotoImage(Image.new("RGB", (250, 250), "black"))
        self.img2 = ImageTk.PhotoImage(Image.new("RGB", (250, 250), "black"))
        self.img3 = ImageTk.PhotoImage(Image.new("RGB", (250, 250), "black"))

        self.img1c = Button(img1f, width=250, command=self.openStartImage, image=self.img1)
        self.img1c.grid(row=1, column=0)
        self.img2c = Button(img1f, width=250, command=self.openNextImage, image=self.img2)
        self.img2c.grid(row=1, column=1)
        self.img3c = Button(img1f, width=250, command=self.openMaskImage, image=self.img3)
        self.img3c.grid(row=1, column=2)

        self.l1 = Label(img1f, text="")
        self.l1.grid(row=0, column=0)
        self.l2 = Label(img2f, text="")
        self.l2.grid(row=0, column=1)
        self.l3 = Label(img3f, text="")
        self.l3.grid(row=0, column=2)

        self.nodemenu = Menu(self.master, tearoff=0)
        self.nodemenu.add_command(label="Select", command=self.select)
        self.nodemenu.add_command(label="Remove", command=self.remove)
        self.nodemenu.add_command(label="Connect To", command=self.connectto)
        self.nodemenu.add_command(label="Export", command=self.exportpath)
        self.nodemenu.add_command(label="Compare To", command=self.compareto)
        self.nodemenu.add_command(label="View Composite", command=self.viewcomposite)

        self.edgemenu = Menu(self.master, tearoff=0)
        self.edgemenu.add_command(label="Select", command=self.select)
        self.edgemenu.add_command(label="Remove", command=self.remove)
        self.edgemenu.add_command(label="Edit", command=self.edit)
        self.edgemenu.add_command(label="Inspect", command=self.view)
        self.edgemenu.add_command(label="Composite Mask", command=self.viewselectmask)

        self.filteredgemenu = Menu(self.master, tearoff=0)
        self.filteredgemenu.add_command(label="Select", command=self.select)
        self.filteredgemenu.add_command(label="Remove", command=self.remove)
        self.filteredgemenu.add_command(label="Inspect", command=self.view)
        self.filteredgemenu.add_command(label="Composite Mask", command=self.viewselectmask)

        iframe = Frame(self.master, bd=2, relief=SUNKEN)
        iframe.grid_rowconfigure(0, weight=1)
        iframe.grid_columnconfigure(0, weight=1)
        self.maskvar = StringVar()
        Message(iframe, textvariable=self.maskvar, width=750).grid(row=0, sticky=W + E)
        iframe.grid(row=2, column=0, rowspan=1, columnspan=3, sticky=N + S + E + W)

        mframe = Frame(self.master, bd=2, relief=SUNKEN)
        mframe.grid_rowconfigure(0, weight=1)
        mframe.grid_columnconfigure(0, weight=1)
        self.vscrollbar = Scrollbar(mframe, orient=VERTICAL)
        self.hscrollbar = Scrollbar(mframe, orient=HORIZONTAL)
        self.vscrollbar.grid(row=0, column=1, sticky=N + S)
        self.hscrollbar.grid(row=1, column=0, sticky=E + W)
        self.canvas = MaskGraphCanvas(mframe, self.uiProfile, self.scModel, self.graphCB, width=768, height=512,
                                      scrollregion=(0, 0, 4000, 4000), yscrollcommand=self.vscrollbar.set,
                                      xscrollcommand=self.hscrollbar.set)
        self.canvas.grid(row=0, column=0, sticky=N + S + E + W)
        self.vscrollbar.config(command=self.canvas.yview)
        self.hscrollbar.config(command=self.canvas.xview)
        mframe.grid(row=3, column=0, rowspan=1, columnspan=3, sticky=N + S + E + W)

        if (self.scModel.start is not None):
            self.setSelectState('normal')
            self.drawState()

    def graphCB(self, event, eventName):
        if eventName == 'rcNode':
            self.nodemenu.post(event.x_root, event.y_root)
        elif eventName == 'rcEdge':
            self.edgemenu.post(event.x_root, event.y_root)
        elif eventName == 'rcNonEditEdge':
            self.filteredgemenu.post(event.x_root, event.y_root)
        elif eventName == 'n':
            self.drawState()

    def __init__(self, dir, master=None, pluginops={}, base=None, uiProfile=UIProfile()):
        Frame.__init__(self, master)
        self.uiProfile = uiProfile
        self.mypluginops = pluginops
        tuple = createProject(dir, notify=self.changeEvent, base=base, suffixes=uiProfile.suffixes,
                              projectModelFactory=uiProfile.getFactory(),
                              organization=self.prefLoader.get_key('organization'))
        if tuple is None:
            print 'Invalid project director ' + dir
            sys.exit(-1)
        self.scModel = tuple[0]
        if self.scModel.getProjectData('typespref') is None:
            preferredFT = self.prefLoader.get_key('filetypes')
            if preferredFT:
                self.scModel.setProjectData('typespref', preferredFT)
            else:
                self.scModel.setProjectData('typespref', getFileTypes())
        self.createWidgets()
        if tuple[1]:
            self.getproperties()


def main(argv=None):
    if (argv is None):
        argv = sys.argv

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--imagedir', help='image directory', nargs=1)
    parser.add_argument('--base', help='base image or video', nargs=1)
    parser.add_argument('--s3', help="s3 bucket/directory ", nargs='+')
    parser.add_argument('--http', help="http address and header params", nargs='+')
    imgdir = ['.']
    argv = argv[1:]
    uiProfile = UIProfile()
    args = parser.parse_args(argv)
    if args.imagedir is not None:
        imgdir = args.imagedir
    if args.http is not None:
        loadHTTP(args.http)
    elif args.s3 is not None:
        loadS3(args.s3)
    loadOperations(uiProfile.operations)
    loadSoftware(uiProfile.software)
    root = Tk()

    gui = MakeGenUI(imgdir[0], master=root, pluginops=plugins.loadPlugins(),
                    base=args.base[0] if args.base is not None else None, uiProfile=uiProfile)
    gui.mainloop()


if __name__ == "__main__":
    sys.exit(main())
