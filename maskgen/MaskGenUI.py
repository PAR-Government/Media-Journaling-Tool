import argparse
import matplotlib
matplotlib.use("TkAgg")

from botocore.exceptions import ClientError
from software_loader import  getProjectProperties,getSemanticGroups,operationVersion,getPropertiesBySourceType
from graph_canvas import MaskGraphCanvas
from scenario_model import *
from description_dialog import *
from group_filter import  GroupFilterLoader
from tool_set import *
from group_manager import GroupManagerDialog
from maskgen_loader import MaskGenLoader
from group_operations import CopyCompressionAndExifGroupOperation
from web_tools import *
from graph_rules import processProjectProperties
from mask_frames import HistoryDialog
from plugin_builder import PluginBuilder
from graph_output import ImageGraphPainter
from CompositeViewer import CompositeViewDialog
from notifiers import  getNotifier
import logging
from AnalysisViewer import AnalsisViewDialog,loadAnalytics
from graph_output import check_graph_status
from maskgen.updater import UpdaterGitAPI
from mask_rules import Jpeg2000CompositeBuilder, CompositeBuilder
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


class UIProfile:
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
    l1 = None
    l2 = None
    l3 = None
    processmenu = None
    mypluginops = {}
    nodemenu = None
    edgemenu = None
    filteredgemenu = None
    groupmenu = None
    canvas = None
    errorlistDialog = None
    exportErrorlistDialog = None
    uiProfile = UIProfile()
    notifiers = getNotifier(prefLoader)
    menuindices = {}
    scModel = None
    """
    @type scModel: ImageProjectModel
    """


    if prefLoader.get_key('username') is not None:
        setPwdX(CustomPwdX(prefLoader.get_key('username')))

    def _check_dir(self, dir):
        set = [filename for filename in os.listdir(dir) if filename.endswith('.json')]
        return not len(set) > 0

    def setSelectState(self, state):
        self.processmenu.entryconfig(2, state=state)
        self.processmenu.entryconfig(3, state=state)
        self.processmenu.entryconfig(4, state=state)
        self.processmenu.entryconfig(5, state=state)

    def new(self):
        val = tkFileDialog.askopenfilename(initialdir=self.scModel.get_dir(), title="Select base image file",
                                           filetypes=self.getMergedFileTypes())
        if val is None or val == '':
            return
        dir = os.path.split(val)[0]
        if (not self._check_dir(dir)):
            tkMessageBox.showinfo("Error", "Directory already associated with a project")
            return
        self.scModel.startNew(val, suffixes=self.getMergedSuffixes(),
                              organization=self.prefLoader.get_key('organization'))
        self.updateFileTypePrefs()
        self._setTitle()
        self.drawState()
        self.canvas.update()
        self.setSelectState('disabled')
        self.getproperties()

    def about(self):
        tkMessageBox.showinfo('About', 'Version: ' + self.scModel.getVersion() +
                              ' \nProject Version: ' + self.scModel.getGraph().getProjectVersion() +
                              ' \nOperations: ' + operationVersion() )

    def _merge_project(self, path):
        model = ImageProjectModel(path)
        self.scModel.mergeProject(model)
        self.canvas.reformat()

    def _open_project(self, path):
        self.scModel.load(path)
        if self.scModel.getProjectData('typespref') is None:
            self.scModel.setProjectData('typespref', getFileTypes(), excludeUpdate=True)
        self._setTitle()
        self.drawState()
        self.canvas.update()
        if (self.scModel.start is not None):
            self.setSelectState('normal')
        #if operationVersion() not in self.scModel.getGraph().getDataItem('jt_upgrades'):
            #tkMessageBox.showwarning("Warning", "Operation file is too old to handle project")

        export_info = graph_rules.get_journal_exporttime(self.scModel.getName(), self.prefLoader.get_key("apitoken"), self.prefLoader.get_key("apiurl"))

        if export_info and self.scModel.getProjectData("exporttime") is not None:
            local_journal = datetime.strptime(self.scModel.getProjectData("exporttime"), "%Y-%m-%d %H:%M:%S")
            browser_journal = datetime.strptime(export_info, "%Y-%m-%d %H:%M:%S")

            if local_journal < browser_journal:
                tkMessageBox.showwarning("Journal Version Warning", "The browser version of this journal is newer.")

    def open(self):
        val = tkFileDialog.askopenfilename(initialdir=self.scModel.get_dir(), title="Select project file",
                                           filetypes=[("json files", "*.json"),("tgz files", "*.tgz")])
        if (val != None and len(val) > 0):
            try:
                self._open_project(val)
            except Exception as e:
                backup = val + '.bak'
                if os.path.exists(backup):
                    if tkMessageBox.askquestion('Project Corruption Error',str(e) + ".  Do you want to restore from the backup?") == 'yes':
                        shutil.copy(backup, val)
                        self._open_project(val)
                else:
                    tkMessageBox.showerror('Project Corruption Error',str(e))

    def addcgi(self):
        self.add(cgi=True)

    def add(self,cgi=False):
        val = tkFileDialog.askopenfilenames(initialdir=self.scModel.get_dir(), title="Select image file(s)",
                                            filetypes=self.getMergedFileTypes())
        if (val != None and len(val) > 0):
            self.updateFileTypes(val[0])
            try:
                totalSet = sorted(val, key=lambda f: os.stat(os.path.join(f)).st_mtime)
                self.canvas.addNew([self.scModel.addImage(f,cgi=cgi) for f in totalSet])
                self.processmenu.entryconfig(self.menuindices['undo'], state='normal')
            except IOError as e:
                tkMessageBox.showinfo("Error", "Failed to load image {}: {}".format(self.scModel.startImageName(),
                                                                                    str(e)))
            self.setSelectState('normal')

    def save(self):
        self.scModel.save()

    def savegraphimage(self):
        val = tkFileDialog.asksaveasfile(initialdir=self.scModel.get_dir(), title="Output Project Image Name",
                                         filetypes=[("png", "*.png")])
        if (val is not None and len(val.name) > 0):
            option = self.prefLoader.get_key('graph_plugin_name')
            openFile(ImageGraphPainter(self.scModel.getGraph()).outputToFile(val,
                                                                    options={'use_plugin_name':option}
                                                                    ))

    def saveas(self):
        val = tkFileDialog.askdirectory(initialdir=self.scModel.get_dir(), title="Save As")
        if (val is not None and len(val) > 0):
            dir = val
            if (dir == os.path.abspath(self.scModel.get_dir())):
                tkMessageBox.showwarning("Save As", "Cannot save to the same directory\n(%s)" % dir)
            else:
                contents = os.listdir(dir)
                if len(contents) > 0:
                    tkMessageBox.showwarning("Save As", "Directory is not empty\n(%s)" % dir)
                else:
                    self.scModel.saveas(dir)
                    self._setTitle()
            #val.close()

    def recomputeallrmask(self):
        for edge_id in self.scModel.getGraph().get_edges():
            self.scModel.reproduceMask(edge_id=edge_id)

    def recomputeedgemask(self):
        analysis_params = {}
        if self.scModel.getEndType() == 'video':
            d = ItemDescriptionCaptureDialog(self,
                                             {
                                                 'video compare': self.scModel.getEdgeItem('video difference',
                                                                                        default='opencv')
                                             },
                                             {
                                                 "video compare": {
                                                     "type": "list",
                                                     "source": "video",
                                                     "values": [
                                                         "opencv",
                                                         "ffmpeg"
                                                     ],
                                                     "description": "FFMPEG is faster but less accurate"
                                                 }
                                             },
                                             'Mask Reconstruct')
            analysis_params = d.argvalues
        errors = self.scModel.reproduceMask(analysis_params=analysis_params)
        nim = self.scModel.nextImage()
        self.img3 = ImageTk.PhotoImage(imageResizeRelative(self.scModel.maskImage(), (250, 250), nim.size).toPIL())
        self.img3c.config(image=self.img3)
        self.maskvar.set(self.scModel.maskStats())
        if errors is not None and len(errors) > 0:
            tkMessageBox.showerror('Recompute Mask Error','\n'.join(errors[(max(0,len(errors)-5)):]))

    def recomputedonormask(self):

        d = ItemDescriptionCaptureDialog(self,
                                         {
                                            'homography': self.scModel.getEdgeItem('homography',default='RANSAC-4'),
                                            'homography max matches': self.scModel.getEdgeItem('homography max matches', default=10000)
                                         },
                                         {
                                             "homography": {
                                                 "type": "list",
                                                 "source": "image",
                                                 "values": [
                                                     "None",
                                                     "Map",
                                                     "All",
                                                     "LMEDS",
                                                     "RANSAC-3",
                                                     "RANSAC-4",
                                                     "RANSAC-5"
                                                 ],
                                                 "description": "Tune transform during composite mask generation"
                                             },
                                             "homography max matches": {
                                                 "type": "int[20:10000]",
                                                 "description": "Maximum number of matched feature points used to compute the homography."
                                             }
                                         },
                                         'Mask Reconstruct')
        if d.argvalues is None:
            return
        skipDonorAnalysis =  'homography' in d.argvalues and d.argvalues['homography'] == 'None'
        errors = self.scModel.reproduceMask(skipDonorAnalysis=skipDonorAnalysis,analysis_params=d.argvalues)
        nim = self.scModel.nextImage()
        self.img3 = ImageTk.PhotoImage(imageResizeRelative(self.scModel.maskImage(), (250, 250), nim.size).toPIL())
        self.img3c.config(image=self.img3)
        if errors is not None and len(errors) > 0:
            tkMessageBox.showerror('Recompute Mask Error','\n'.join(errors[(max(0,len(errors)-5)):]))

    def _preexport(self):
        if self.scModel.hasSkippedEdges():
            if not tkMessageBox.askokcancel('Skipped Link Masks','Some link are missing edge masks and analysis. \n' +
                                                          'The link analysis will begin now and may take a while.'):
                return False
        errorList = self.scModel.validate(external=True)
        if errorList is not None and len(errorList) > 0:
            errorlistDialog = DecisionListDialog(self, errorList, "Validation Errors")
            errorlistDialog.wait(self)
            if not errorlistDialog.isok:
                return
        self.scModel.executeFinalNodeRules()
        processProjectProperties(self.scModel)
        self.getproperties()
        return True

    def export(self):
        if not self._preexport():
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
        if not self._preexport():
            return
        info = self.prefLoader.get_key('s3info')
        val = tkSimpleDialog.askstring("S3 Bucket/Folder", "Bucket/Folder",
                                       initialvalue=info if info is not None else '')
        if (val is not None and len(val) > 0):
            try:
                errorList = self.scModel.exporttos3(val)
                uploaded = self.prefLoader.get_key('lastlogupload')
                uploaded = exportlogsto3(val,uploaded)
                # preserve the file uploaded
                if uploaded is not None:
                    self.prefLoader.save('lastlogupload',uploaded)
                if len(errorList) > 0:
                    if self.exportErrorlistDialog is None:
                        self.exportErrorlistDialog = ListDialog(self, errorList, "Export Errors")
                    else:
                        self.exportErrorlistDialog.setItems(errorList)
                else:
                    tkMessageBox.showinfo("Export to S3", "Complete")
                    self.prefLoader.save('s3info', val)
            except IOError as e:
                logging.getLogger('maskgen').warning("Failed to upload project: " + str(e))
                tkMessageBox.showinfo("Error", "Failed to upload export.  Check log file details.")
            except ClientError as e:
                logging.getLogger('maskgen').warning("Failed to upload project: " + str(e))
                tkMessageBox.showinfo("Error", "Failed to upload export")

    def _promptRotate(self,donor_im,rotated_im, orientation):
        dialog = RotateDialog(self.master, donor_im, rotated_im, orientation)
        return dialog.rotate

    def createJPEGorTIFF(self):
        msg, pairs = CopyCompressionAndExifGroupOperation(self.scModel).performOp(promptFunc=self._promptRotate)
        if msg is not None:
            tkMessageBox.showwarning("Error", msg)
            if not pairs:
                return
        if len(pairs) == 0:
            tkMessageBox.showwarning("Warning", "Leaf image nodes with base JPEG or TIFF images do not exist in this project")
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

    def setautosave(self):
        autosave_decision = self.prefLoader.get_key('autosave')
        d = SelectDialog(self,
                         "AutoSave",
                         "Autosave every 'n' seconds. 0 turns off AutoSave",
                         ['0', '60', '300', '600', 'L'],
                         initial_value=autosave_decision)
        new_autosave_decision = d.choice if d.choice is not None else autosave_decision
        self.prefLoader.save('autosave', new_autosave_decision)
        autosave_decision = float(autosave_decision) if autosave_decision is not None and autosave_decision != 'L'  else 0.0
        new_autosave_decision = float(new_autosave_decision) if new_autosave_decision and new_autosave_decision != 'L'else 0.0
        if new_autosave_decision != autosave_decision:
            cancel_execute(saveme)
            if new_autosave_decision > 0:
                 execute_every(new_autosave_decision, saveme, saver=self)


    def setusername(self):
        name = get_username()
        newName = tkSimpleDialog.askstring("Set Username", "Username", initialvalue=name)
        if newName is not None:
            newName = newName.lower()
            self.prefLoader.save('username', newName)
            setPwdX(CustomPwdX(self.prefLoader.get_key('username')))
            oldName = self.scModel.getProjectData('username')
            self.scModel.setProjectData('username', newName)
            if tkMessageBox.askyesno("Username", "Retroactively apply to this project?"):
                self.scModel.getGraph().replace_attribute_value('username', oldName, newName)

    def setproperty(self, key, value):
        token = self.prefLoader.get_key(key)
        newTokenStr = tkSimpleDialog.askstring(value, value, initialvalue=token)
        if newTokenStr is not None:
            self.prefLoader.save(key, newTokenStr)

    def setPreferredFileTypes(self):
        filetypes = self.getPreferredFileTypes()
        newtypesStr = tkSimpleDialog.askstring("Set File Types", "Types", initialvalue=toFileTypeString(filetypes))
        if newtypesStr is not None:
            self.prefLoader.save('filetypes', fromFileTypeString(newtypesStr, getFileTypes()))
            self.scModel.setProjectData('typespref', fromFileTypeString(newtypesStr, getFileTypes()),excludeUpdate=True)

    def setSkipStatus(self):
        skip_compare_status = 'yes' if self.prefLoader.get_key('skip_compare') else 'no'
        d = SelectDialog(self,
                         "Skip Link Comparison",
                         "Link Comparison is temporarily skipped until validation",
                         ['yes', 'no'],
                         initial_value=skip_compare_status)
        skip_compare_status = d.choice if d.choice is not None else skip_compare_status
        self.prefLoader.save('skip_compare',skip_compare_status=='yes')

    def setSkipThreads(self):
        skipped_threads = self.prefLoader.get_key('skipped_threads',2)
        d = SelectDialog(self,
                         "Skip Link Threads",
                         "Link Comparison threads used during validation",
                         [2, 3, 4],
                         initial_value=skipped_threads)
        skipped_threads = d.choice if d.choice is not None else skipped_threads
        self.prefLoader.save('skipped_threads',int(skipped_threads))

    def undo(self):
        self.scModel.undo()
        self.drawState()
        self.canvas.update()
        self.processmenu.entryconfig(self.menuindices['undo'], state='disabled')
        self.setSelectState('disabled')

    def updateFileTypePrefs(self):
        if self.scModel.getProjectData('typespref') is None:
            preferredFT = self.prefLoader.get_key('filetypes')
            if preferredFT is not None:
                self.scModel.setProjectData('typespref', preferredFT,excludeUpdate=True)
            else:
                self.scModel.setProjectData('typespref', getFileTypes(),excludeUpdate=True)

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
            self.scModel.setProjectData('typespref', prefs,excludeUpdate=True)
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
        d = DescriptionCaptureDialog(self, self.uiProfile, self.scModel, filetype,
                                      im, os.path.split(file)[1])
        if (
                    d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            msg, status = self.scModel.addNextImage(file, mod=d.description)
            if msg is not None:
                tkMessageBox.showwarning("Auto Connect", msg)
            if status:
                self.drawState()
                self.canvas.add(self.scModel.start, self.scModel.end)
                self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def nodeedit(self):
        im, filename = self.scModel.currentImage()
        if (im is None):
            return

        d = ItemDescriptionCaptureDialog(self, self.scModel.getCurrentNode(),
                                         getPropertiesBySourceType(self.scModel.getStartType()),
                                         filename)
        if (d.argvalues is not None):
            self.scModel.update_node(d.argvalues)
        self.drawState()


    def imageanalysis(self):
        d = AnalsisViewDialog(self, 'Final Image Analysis', self.scModel,nodes=[self.scModel.start])

    def nextauto(self):
        destination = self.scModel.scanNextImageUnConnectedImage()
        if destination is None:
            tkMessageBox.showwarning("Auto Connect", "No suitable loaded images found")
            return
        im, filename = self.scModel.getImageAndName(destination)
        filetype = fileType(filename)
        d = DescriptionCaptureDialog(self, self.uiProfile, self.scModel, filetype,
                                      im, os.path.split(filename)[1])
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
        d = DescriptionCaptureDialog(self, self.uiProfile, self.scModel, filetype,
                                     im, os.path.split(filename)[1])
        if (
                    d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            msg, status = self.scModel.addNextImage(filename, mod=d.description, position=self.scModel._getCurrentPosition((0,75)))
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
        d = FilterCaptureDialog(self,
                                self.gfl,
                                self.scModel)
        if d.optocall is not None:
            grp = self.gfl.getGroup(d.optocall)
            if grp is None:
                grp = GroupFilter(d.optocall,[d.optocall])
            msg,pairs =self.scModel.imageFromGroup(grp, software=d.softwaretouse,
                                                          **self.resolvePluginValues(d.argvalues))
            self._addPairs(pairs)
            if msg is not None and len(msg) > 1:
                tkMessageBox.showwarning("Next Filter {}".format(filter), msg)
            self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

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
                msg, pairs = self.scModel.imageFromPlugin(filter)
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

    def renamefinal(self):
        for node in self.scModel.renameFileImages():
            self.canvas.redrawNode(node)

    def openStartImage(self):
        sim = self.scModel.getStartImageFile()
        openFile(sim)

    def openNextImage(self):
        if self.scModel.end:
            nim = self.scModel.getNextImageFile()
            openFile(nim)

    def openMaskImage(self):
        imname = self.scModel.maskImageName()
        if imname != '':
            openFile(os.path.join(self.scModel.get_dir(),imname))

    def drawState(self):
        sim = self.scModel.startImage()
        nim = self.scModel.nextImage()
        self.img1 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(sim, (250, 250), sim.size)).toPIL())
        self.img2 = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(nim, (250, 250), nim.size)).toPIL())
        self.img3 = ImageTk.PhotoImage(imageResizeRelative(self.scModel.maskImage(), (250, 250), nim.size).toPIL())
        self.img1c.config(image=self.img1)
        self.img2c.config(image=self.img2)
        self.img3c.config(image=self.img3)
        self.l1.config(text=self.scModel.startImageName())
        self.l2.config(text=self.scModel.nextImageName())
        self.l3.config(text=self.scModel.maskImageName())
        self.maskvar.set(self.scModel.maskStats())

    def doneWithWindow(self, window):
        if window == self.errorlistDialog:
            self.errorlistDialog = None
        if window == self.exportErrorlistDialog:
            self.exportErrorlistDialog = None

    def finalimageanalysis(self):
        d = AnalsisViewDialog(self,'Final Image Analysis',self.scModel)

    def cloneinputmask(self):
        self.scModel.fixInputMasks()

    def openS3(self):
        val = tkSimpleDialog.askstring("S3 File URL", "URL",
                                       initialvalue='')
        if (val is not None and len(val) > 0):
            self._open_project(fetchbyS3URL(val))

    def installPluginFromS3(self):
        val = tkSimpleDialog.askstring("S3 File URL", "URL",
                                       initialvalue='')
        if (val is not None and len(val) > 0):
            plugins.installPlugin(fetchbyS3URL(val))

    def fetchS3(self):
        info = self.prefLoader.get_key('s3info')
        val = tkSimpleDialog.askstring("S3 Bucket/Folder", "Bucket/Folder",
                                       initialvalue=info if info is not None else '')
        if (val is not None and len(val) > 0):
            try:
                loadS3([val])
                self.prefLoader.save('s3info', val)
            except ClientError as e:
                tkMessageBox.showwarning("S3 Download failure", str(e))

    def validate(self):
        errorList = self.scModel.validate(external=True)
        if (self.errorlistDialog is None):
            self.errorlistDialog = ListDialog(self, errorList, "Validation Errors")
        else:
            self.errorlistDialog.setItems(errorList)

    def getsystemproperties(self):
        d = SystemPropertyDialog(self,self.getSystemPreferences(),self.prefLoader)

    def getproperties(self):
        graph_rules.setProjectSummary(self.scModel)
        d = PropertyDialog(self, getProjectProperties(),scModel=self.scModel, dir=self.scModel.get_dir())

    def pluginbuilder(self):
        d = PluginBuilder(self,self.scModel.getGroupOperationLoader())

    def reloadplugins(self):
        plugins.loadPlugins(reload=True)

    def updates(self):
        plugins.loadPlugins(reload=True)

    def groupmanager(self):
        d = GroupManagerDialog(self,GroupFilterLoader())

    def operationsgroupmanager(self):
        d = GroupManagerDialog(self, self.scModel.getGroupOperationLoader())

    def merge(self):
        val = tkFileDialog.askopenfilename(initialdir=self.scModel.get_dir(), title="Select project file",
                                           filetypes=[("json files", "*.json"), ("tgz files", "*.tgz")])
        if val is None or val == '':
            return
        try:
            self._merge_project(val)
        except Exception as e:
            backup = val + '.bak'
            if os.path.exists(backup):
                if tkMessageBox.askquestion('Project Corruption Error',
                                            str(e) + ".  Do you want to restore from the backup?") == 'yes':
                    shutil.copy(backup, val)
                    self._merge_project(val)
            else:
                tkMessageBox.showerror('Project Corruption Error', str(e))

    def quit(self):
        self.save()
        Frame.quit(self)
        quit()

    def quitnosave(self):
        Frame.quit(self)
        quit()

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
        probes = self.scModel.constructPathProbes()
        if probes is not None:
            composite = probes[-1].composites['color']['image']
            CompositeViewDialog(self, self.scModel.start, composite, self.scModel.startImage())

    def viewmaskoverlay(self):
        mask = self.scModel.maskImage()
        if mask is not None:
            selectImage = self.scModel.nextImage()
            if selectImage.size != mask.size:
                selectImage = self.scModel.startImage()
            CompositeViewDialog(self, self.scModel.start, mask, selectImage)

    def viewtransformed(self):
        transformed = self.scModel.getTransformedMask()
        if len(transformed)> 0:
            CompositeViewDialog(self, self.scModel.start, transformed[0][0], self.scModel.getImage(transformed[0][1]))

    def renametobase(self):
        self.scModel.renametobase()
        self._setTitle()

    def systemcheck(self):
        errors = [graph_rules.test_api(prefLoader.get_key('apitoken'), prefLoader.get_key('apiurl')),
                  video_tools.ffmpegToolTest(), exif.toolCheck(), selfVideoTest(),
                  check_graph_status(),
                  self.notifiers.check_status()]
        error_count = 0
        for error in errors:
            if error is not None:
                logging.getLogger('maskgen').error(error)
                error_count += 1
        logging.getLogger('maskgen').info('System check complete')
        if error_count > 0:
           tkMessageBox.showinfo("System Check", " ".join([error for error in errors if error is not None]))
        return error_count == 0

    def viewdonor(self):
        im,baseIm = self.scModel.getDonorAndBaseImage()
        if im is not None:
            CompositeViewDialog(self, self.scModel.start, im, baseIm)

    def compress(self):
        newnode = self.scModel.compress(force=True)
        if newnode is not None:
            tkMessageBox.showinfo("Compress","Compressed as file " + newnode  + ".")
            self.canvas.redrawNode(self.scModel.start)
        else:
            tkMessageBox.showinfo("Compress", "Node not eligble for compression or error occurred.")

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

    def selectgroup(self):
        d = SelectDialog(self, "Set Semantic Group", 'Select a semantic group for these operations.', getSemanticGroups())
        res = d.choice
        if res is not None and len(res) > 0:
            for start in self.groupselection:
                for end in self.groupselection:
                    edge = self.scModel.getGraph().get_edge(start,end)
                    if edge is not None:
                        grps = self.scModel.getSemanticGroups(start,end)
                        if res not in grps:
                            grps.append(res)
                            self.scModel.setSemanticGroups(start,end,grps)

    def removegroup(self):
        if tkMessageBox.askyesno(title='Remove Group', message='Are you sure you want to remove this group of nodes?'):
            for name in self.groupselection:
                self.scModel.selectImage(name)
                self.remove()

    def select(self):
        self.drawState()
        self.setSelectState('normal')

    def changeEvent(self, recipient, eventType, **kwargs):
        if eventType == 'label' and self.canvas is not None:
            self.canvas.redrawNode(recipient)
            return True
        if eventType in ['connect','add','remove','undo']:
            if prefLoader.get_key('autosave','') == 'L':
                try:
                    self.scModel.save()
                except Exception as e:
                    logging.getLogger('maskgen').error('Failed to incrementally save {}'.format(str(e)))
        if eventType == 'export':
            qacomment = self.scModel.getProjectData('qacomment')
            validation_person = self.scModel.getProjectData('validatedby')
            comment = 'Exported by ' + self.prefLoader.get_key('username')
            for k,v in kwargs.iteritems():
                comment = comment + '\n {}: {}'.format(k,v)
            comment = comment + '\n Journal Comment: ' + qacomment if qacomment is not None else comment
            if validation_person is not None:
                comment = comment + '\n Validated By: ' + validation_person
            return self.notifiers.update_journal_status(self.scModel.getName(),
                                                 self.scModel.getGraph().getCreator().lower(),
                                                 comment,
                                                 self.scModel.getGraph().get_project_type())
        #        elif eventType == 'connect':
        #           self.canvas.showEdge(recipient[0],recipient[1])
        return True

    def remove(self):
        self.canvas.remove()
        self.drawState()
        self.processmenu.entryconfig(self.menuindices['undo'], state='normal')
        self.setSelectState('disabled')

    def history(self):
        h = HistoryDialog(self,self.scModel)

    def edit(self):
        im, filename = self.scModel.currentImage()
        if (im is None):
            return
        d = DescriptionCaptureDialog(self, self.uiProfile, self.scModel, self.scModel.getEndType(),
                                     im, os.path.split(filename)[1],
                                     description=self.scModel.getDescription())
        if (
                    d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
            self.scModel.update_edge(d.description)
        self.drawState()

    def view(self):
        im, filename = self.scModel.currentImage()
        if (im is None):
            return
        d = DescriptionViewDialog(self, self.scModel, os.path.split(filename)[1],
                                  description=self.scModel.getDescription(), metadiff=self.scModel.getMetaDiff())

    def viewselectmask(self):
        d = CompositeCaptureDialog(self,self.scModel)
        if not d.cancelled:
            self.scModel.updateSelectMask(d.selectMasks)
            self.scModel.update_edge(d.modification)

    def createProbes(self):
        for edge_id in self.scModel.getGraph().get_edges():
            edge = self.scModel.getGraph().get_edge(edge_id[0], edge_id[1])
            op = self.scModel.gopLoader.getOperation(edge['op'])
            if mask_rules.isEdgeLocalized(edge_id,edge, op):
                logging.getLogger('maskgen').info('Eligible edge {} to {} op: {}'.format(
                    edge_id[0], edge_id[1],edge['op']
                ))
        ps = self.scModel.getProbeSet(compositeBuilders=[ColorCompositeBuilder, Jpeg2000CompositeBuilder])

    def startQA(self):
        if self.scModel.getProjectData('validation') == 'yes':
            tkMessageBox.showinfo('QA', 'QA validation completed on ' + self.scModel.getProjectData('validationdate') +
                               ' by ' + self.scModel.getProjectData('validatedby') + '.')
        d = QAViewDialog(self)

    def comments(self):
        d = CommentViewer(self)

    def reformatgraph(self):
        self.canvas.reformat()

    def _setTitle(self):
        self.master.title(os.path.join(self.scModel.get_dir(), self.scModel.getName()))

    def createWidgets(self):
        from functools import partial
        self._setTitle()

        menubar = Menu(self)

        exportmenu = Menu(tearoff=0)
        exportmenu.add_command(label="To File", command=self.export, accelerator="Ctrl+E")
        exportmenu.add_command(label="To S3", command=self.exporttoS3)

        settingsmenu = Menu(tearoff=0)
        settingsmenu.add_command(label="System Properties", command=self.getsystemproperties)
        settingsmenu.add_command(label="File Types", command=self.setPreferredFileTypes)
        settingsmenu.add_command(label="Skip Link Compare", command=self.setSkipStatus)
        settingsmenu.add_command(label="Skip Link Threads", command=self.setSkipThreads)
        settingsmenu.add_command(label="Autosave", command=self.setautosave)
        for k,v in self.notifiers.get_properties().iteritems():
            settingsmenu.add_command(label=v, command=partial(self.setproperty,k,v))

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="About", command=self.about)
        filemenu.add_command(label="Open", command=self.open, accelerator="Ctrl+O")
        filemenu.add_command(label="Open S3", command=self.openS3, accelerator="Ctrl+O")
        filemenu.add_command(label="Merge", command=self.merge)
        filemenu.add_command(label="New", command=self.new, accelerator="Ctrl+N")
        filemenu.add_command(label="Save", command=self.save, accelerator="Ctrl+S")
        filemenu.add_command(label="Save As", command=self.saveas)
        filemenu.add_command(label="Save Graph Image",command=self.savegraphimage)
        filemenu.add_separator()
        filemenu.add_cascade(label="Export", menu=exportmenu)
        filemenu.add_command(label="Fetch Meta-Data(S3)", command=self.fetchS3)
        filemenu.add_command(label="Fetch Plugin from S3",command=self.installPluginFromS3)
        filemenu.add_command(label="Build Plugin...", command=self.pluginbuilder)
        filemenu.add_command(label="Filter Group Manager", command=self.groupmanager)
        filemenu.add_command(label="Operations Group Manager", command=self.operationsgroupmanager)
        filemenu.add_separator()
        filemenu.add_cascade(label="Settings", menu=settingsmenu)
        filemenu.add_cascade(label="Properties", command=self.getproperties)
        filemenu.add_cascade(label="Rename to Base Image", command=self.renametobase)
        filemenu.add_cascade(label="System Check", command=self.systemcheck)
        filemenu.add_cascade(label="Reload Plugins", command=self.reloadplugins)
        #filemenu.add_cascade(label="Last Updates", command=self.updates)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
        filemenu.add_command(label="Quit without Save", command=self.quitnosave)

        menubar.add_cascade(label="File", menu=filemenu)

        self.processmenu = Menu(menubar, tearoff=0)
        self.processmenu.add_command(label="Add " + self.uiProfile.name, command=self.add, accelerator="Ctrl+A")
        self.processmenu.add_command(label="Add CGI", command=self.addcgi)
        self.processmenu.add_command(label="Next w/Auto Pick", command=self.nextauto, accelerator="Ctrl+P",
                                     state='disabled')
        self.processmenu.add_command(label="Next w/Auto Pick from File", command=self.nextautofromfile,
                                     state='disabled')
        self.processmenu.add_command(label="Next w/Add", command=self.nextadd, accelerator="Ctrl+L", state='disabled')
        self.processmenu.add_command(label="Next w/Filter", command=self.nextfilter, accelerator="Ctrl+F",
                                     state='disabled')
        self.processmenu.add_separator()
        self.uiProfile.addProcessCommand(self.processmenu, self)
        self.processmenu.add_command(label="Rename Final Images", command=self.renamefinal)
        self.processmenu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z", state='disabled')
        self.menuindices['undo'] = self.processmenu.index(END)
        menubar.add_cascade(label="Process", menu=self.processmenu)

        validationmenu = Menu(menubar, tearoff=0)
        validationmenu.add_command(label='History',command=self.history)
        validationmenu.add_command(label="Validate", command=self.validate)
        validationmenu.add_command(label="QA...", command=self.startQA)
        validationmenu.add_command(label="View Comments", command=self.comments)
        validationmenu.add_command(label="Clone Input Mask", command=self.cloneinputmask)
        validationmenu.add_command(label="Final Image Analysis", command=self.finalimageanalysis)
        validationmenu.add_command(label="Probes",command=self.createProbes)
        validationmenu.add_command(label="Recompute All Masks", command=self.recomputeallrmask)

        menubar.add_cascade(label="Validation", menu=validationmenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_command(label='Reformat', command=self.reformatgraph)

        menubar.add_cascade(label="View", menu=viewmenu)

        self.master.config(menu=menubar)
        self.bind_all('<Control-q>', self.gquit)
        self.bind_all('<Control-o>', self.gopen)
        self.bind_all('<Control-s>', self.gsave)
        self.bind_all('<Control-a>', lambda event: self.after(100, self.add))
        self.bind_all('<Control-n>', self.gnew)
        self.bind_all('<Control-p>', lambda event: self.after(100, self.nextauto))
        self.bind_all('<Control-e>', lambda event: self.after(100, self.export))
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
        self.img1c.grid_propagate(False)
        self.img2c = Button(img1f, width=250, command=self.openNextImage, image=self.img2)
        self.img2c.grid(row=1, column=1)
        self.img2c.grid_propagate(False)
        self.img3c = Button(img1f, width=250, command=self.openMaskImage, image=self.img3)
        self.img3c.grid(row=1, column=2)
        self.img3c.grid_propagate(False)

        self.l1 = Label(img1f, text="")
        self.l1.grid(row=0, column=0)
        self.l1.grid_propagate(False)
        self.l2 = Label(img2f, text="")
        self.l2.grid(row=0, column=1)
        self.l2.grid_propagate(False)
        self.l3 = Label(img3f, text="")
        self.l3.grid(row=0, column=2)
        self.l3.grid_propagate(False)

        self.nodemenu = Menu(self.master, tearoff=0)
        self.nodemenu.add_command(label="Select", command=self.select)
        self.nodemenu.add_command(label="Remove", command=self.remove)
        self.nodemenu.add_command(label="Connect To", command=self.connectto)
        self.nodemenu.add_command(label="Export", command=self.exportpath)
        self.nodemenu.add_command(label="Compare To", command=self.compareto)
        self.nodemenu.add_command(label="View Composite", command=self.viewcomposite)
        self.nodemenu.add_command(label="View Donor", command=self.viewdonor)
        self.nodemenu.add_command(label="Compress", command=self.compress)
        self.nodemenu.add_command(label="Analyze", command=self.imageanalysis)
        self.nodemenu.add_command(label="Edit", command=self.nodeedit)

        self.edgemenu = Menu(self.master, tearoff=0)
        self.edgemenu.add_command(label="Select", command=self.select)
        self.edgemenu.add_command(label="Remove", command=self.remove)
        self.edgemenu.add_command(label="Edit", command=self.edit)
        self.edgemenu.add_command(label="Inspect", command=self.view)
        self.edgemenu.add_command(label="Composite Mask", command=self.viewselectmask)
        self.edgemenu.add_command(label="View Transformed Mask", command=self.viewtransformed)
        self.edgemenu.add_command(label="View Overlay Mask", command=self.viewmaskoverlay)
        self.edgemenu.add_command(label="Recompute Mask", command=self.recomputeedgemask)

        self.filteredgemenu = Menu(self.master, tearoff=0)
        self.filteredgemenu.add_command(label="Select", command=self.select)
        self.filteredgemenu.add_command(label="Remove", command=self.remove)
        self.filteredgemenu.add_command(label="Inspect", command=self.view)
        self.filteredgemenu.add_command(label="Composite Mask", command=self.viewselectmask)
        self.filteredgemenu.add_command(label="Recompute", command=self.recomputedonormask)

        self.groupmenu = Menu(self.master, tearoff=0)
        self.groupmenu.add_command(label="Semantic Group", command=self.selectgroup)
        self.groupmenu.add_command(label="Remove", command=self.removegroup)

        iframe = Frame(self.master, bd=2, relief=SUNKEN)
        iframe.grid_rowconfigure(0, weight=1)
        iframe.grid_columnconfigure(0, weight=1)
        self.maskvar = StringVar()
        Message(iframe, textvariable=self.maskvar, width=750).grid(row=0, sticky=W + E)
        iframe.grid(row=2, column=0, rowspan=1, columnspan=3, sticky=N + S + E + W)
        #iframe.grid_propagate(False)

        mframe = Frame(self.master, bd=2, relief=SUNKEN)
        mframe.grid_rowconfigure(0, weight=5)
        mframe.grid_columnconfigure(0, weight=5)
        self.vscrollbar = Scrollbar(mframe, orient=VERTICAL)
        self.hscrollbar = Scrollbar(mframe, orient=HORIZONTAL)
        self.vscrollbar.grid(row=0, column=1, sticky=N + S)
        self.hscrollbar.grid(row=1, column=0, sticky=E + W)
        self.canvas = MaskGraphCanvas(mframe, self.uiProfile, self.scModel, self.graphCB, width=768, height=512,
                                      scrollregion=(0, 0, 20000, 20000), yscrollcommand=self.vscrollbar.set,
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
        elif eventName == 'rcGroup':
            self.groupselection = event.items
            self.groupmenu.post(event.x_root, event.y_root)
        elif eventName == 'n':
            self.drawState()

    def getMergedSuffixes(self):
        filetypes = self.prefLoader.get_key('filetypes')
        filetypes = [] if filetypes is None else filetypes
        types = [x[1] for x in filetypes]
        for suffix in getFileTypes():
            if suffix[1] not in types:
                types.append(suffix[1])
        types = [suffix[suffix.rfind('.'):] for suffix in types]
        return types

    def getMergedFileTypes(self):
        filetypes = self.prefLoader.get_key('filetypes')
        filetypes = [] if filetypes is None else filetypes
        types = [tuple(x) for x in filetypes]
        tset = set([x[1] for x in types])
        for suffix in getFileTypes():
            if suffix[1] not in tset:
                types.append(suffix)
        return types

    def getSystemPreferences(self):
        props =  [ProjectProperty(name='username',
                                  type='text',
                                  description='User Name',
                                  information='Journal User Name'),
                ProjectProperty(name='organization', type='text',
                                description='Organization',
                                information="journal user's organization"),
                ProjectProperty(name='apiurl', type='text',
                                description="API URL",
                                information='Validation API URL'),
                ProjectProperty(name='apitoken', type='text',
                                description="API Token",
                                information = 'Validation API URL')
                ]
        for k, v in self.notifiers.get_properties().iteritems():
            props.append(ProjectProperty(name=k, type='text', description=k,
                                         information='notification property'))
        return props

    def __init__(self, dir, master=None, base=None, uiProfile=UIProfile()):
        Frame.__init__(self, master)
        self.uiProfile = uiProfile
        self.mypluginops = plugins.loadPlugins()
        self.gfl = GroupFilterLoader()
        tuple = createProject(dir, notify=self.changeEvent, base=base, suffixes=self.getMergedSuffixes(),
                              projectModelFactory=uiProfile.getFactory(),
                              organization=self.prefLoader.get_key('organization'))
        if tuple is None:
            logging.getLogger('maskgen').warning( 'Invalid project director ' + dir)
            sys.exit(-1)
        self.scModel = tuple[0]
        self.updateFileTypePrefs()
        self.createWidgets()
        self.startedWithNewProject = tuple[1]

    def initCheck(self):
        if self.prefLoader.get_key('username',None) is None:
            self.getsystemproperties()
        sha, message =  UpdaterGitAPI().isOutdated()
        if sha is not None:
            tkMessageBox.showinfo('Update to JT Available','New version: {}, Last update message: {}'.format(sha, message))
        if self.startedWithNewProject:
            self.getproperties()


def saveme(saver=None):
    """

    :param gui:
    :return:
    @type gui: MakeGenUI
    """
    saver.save()


def do_every (interval, worker_func, iterations = 0):
  if iterations != 1:
    threading.Timer (
      interval,
      do_every, [interval, worker_func, 0 if iterations == 0 else iterations-1]
    ).start ()


def headless_systemcheck(prefLoader):
    notifiers = getNotifier(prefLoader)
    errors = [graph_rules.test_api(prefLoader.get_key('apitoken'), prefLoader.get_key('apiurl')),
              video_tools.ffmpegToolTest(), exif.toolCheck(), selfVideoTest(),
              check_graph_status(),
              notifiers.check_status()]
    error_count = 0
    for error in errors:
        if error is not None:
            logging.getLogger('maskgen').error(error)
            error_count += 1
    logging.getLogger('maskgen').info('System check complete')
    return error_count == 0

def main(argv=None):
    if (argv is None):
        argv = sys.argv

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--imagedir', help='image directory', required=False)
    parser.add_argument('--test',action='store_true', help='For testing')
    parser.add_argument('--base', help='base image or video',  required=False)
    parser.add_argument('--s3', help="s3 bucket/directory ", nargs='+')
    parser.add_argument('--http', help="http address and header params", nargs='+')

    imgdir = None
    argv = argv[1:]
    uiProfile = UIProfile()
    args = parser.parse_args(argv)

    if args.imagedir is not None:
        imgdir = args.imagedir
    if args.http is not None:
        loadHTTP(args.http)
    elif args.s3 is not None:
        loadS3(args.s3)

    loadAnalytics()
    graph_rules.setup()

    prefLoader = MaskGenLoader()
    if args.test:
        if not headless_systemcheck(prefLoader):
            sys.exit(1)
        return
    root = Tk()
    gui = MakeGenUI(imgdir, master=root,
                    base=args.base if args.base is not None else None, uiProfile=uiProfile)

    #root.protocol("WM_DELETE_WINDOW", lambda: gui.quit())
    interval =  prefLoader.get_key('autosave')
    if interval and interval not in [ '0' , 'L']:
        execute_every(float(interval),saveme, saver=gui)

    gui.after_idle(gui.initCheck)
    gui.mainloop()


if __name__ == "__main__":
    sys.exit(main())
