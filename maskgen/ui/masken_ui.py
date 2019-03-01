# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import argparse

import matplotlib

matplotlib.use("TkAgg")

from maskgen.SystemCheckTools import VersionChecker
from botocore.exceptions import ClientError
from maskgen.ui.graph_canvas import MaskGraphCanvas
from maskgen.scenario_model import *
from maskgen.userinfo import setPwdX,CustomPwdX
from maskgen.ui.description_dialog import *
from maskgen.loghandling import set_logging_level
from maskgen.group_filter import  GroupFilterLoader
from maskgen.tool_set import *
from maskgen.group_manager import GroupManagerDialog
from maskgen import maskGenPreferences
from maskgen.software_loader import operationVersion, getPropertiesBySourceType
from maskgen.group_operations import CopyCompressionAndExifGroupOperation
from maskgen.external.web_tools import *
from maskgen.graph_rules import processProjectProperties
from maskgen.validation.core import ValidationAPIComposite
from maskgen.ui.mask_frames import HistoryDialog
from maskgen.ui.plugin_builder import PluginBuilder
from maskgen.graph_output import ImageGraphPainter
from maskgen.ui.CompositeViewer import CompositeViewDialog
import logging
from maskgen.ui.AnalysisViewer import AnalsisViewDialog,loadAnalytics
from maskgen.graph_output import check_graph_status
from maskgen.updater import UpdaterGitAPI, OperationsUpdaterGitAPI
from maskgen.mask_rules import Jpeg2000CompositeBuilder, ColorCompositeBuilder, HDF5CompositeBuilder
import maskgen.preferences_initializer
from maskgen.software_loader import getMetDataLoader
from cachetools import LRUCache
from maskgen.ui.ui_tools import ProgressBar, AddRemove
from maskgen.services.probes import archive_probes, ProbeGenerator, ProbeSetBuilder, DetermineTaskDesignation, fetch_qaData_designation
from maskgen.external.watcher import ExportWatcherDialog
from maskgen.external.exporter import ExportManager
import wrapt
from maskgen.ui.QAExtreme import QAProjectDialog
from maskgen.qa_logic import ValidationData
from maskgen.notifiers import getNotifier


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

    def addProcessCommand(self, menu, parent):
        menu.add_command(label="Create JPEG/TIFF", command=parent.createJPEGorTIFF, accelerator="Ctrl+J")
        menu.add_separator()

    def addAccelerators(self, parent):
        parent.bind_all('<Control-j>', lambda event: parent.after(100, parent.createJPEGorTIFF))


class UserPropertyChange(ProperyChangeAction):

    """
    Customized actions to take for specific properties.
    When a user is changed, change the name of the user in the current memory image.
    Prompt to see if the journal should be updated with the new name.
    """

    def __init__(self, scModel):
        self.scModel = scModel

    def setvalue(self, oldvalue, newvalue):
        newName = newvalue.lower()
        setPwdX(CustomPwdX(newName))
        self.scModel.setProjectData('username', newName)
        if oldvalue != newvalue:
            if tkMessageBox.askyesno("Username", "Retroactively apply to this project?"):
                self.scModel.getGraph().replace_attribute_value('username', oldvalue, newName)


def _external_export_notify(name=None,
                            exporter=None,
                            location=None,
                            creator=None,
                            additional_message=None,
                            qacomment=None,
                            project_type=None):
    prefLoader = MaskGenLoader()
    from maskgen.notifiers import getNotifier
    notifiers = getNotifier(prefLoader)
    comment = 'Exported by ' + exporter
    comment = comment + '\n {}: {}'.format('location', location)
    comment = comment + '\n {}: {}'.format('additional_message', additional_message)
    comment = comment + '\n Journal Comment: ' + qacomment if qacomment is not None else comment
    notifiers.notifier.update_journal_status(name,
                                             creator,
                                             comment,
                                             project_type)

class MakeGenUI(Frame):
    prefLoader = maskGenPreferences
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
    nodemenu = None
    edgemenu = None
    filteredgemenu = None
    image_cache = LRUCache(maxsize=36)
    groupmenu = None
    canvas = None
    uiProfile = UIProfile()
    notifiers = getNotifier(prefLoader)
    validator = ValidationAPIComposite(prefLoader,external=True)
    menuindices = {}
    scModel = None
    """
    @type scModel: ImageProjectModel
    """




    def _check_dir(self, dir):
        set = [filename for filename in os.listdir(dir) if filename.endswith('.json')]
        return not len(set) > 0

    def setSelectState(self, state):
        self.processmenu.entryconfig(2, state=state)
        self.processmenu.entryconfig(3, state=state)
        self.processmenu.entryconfig(4, state=state)
        self.processmenu.entryconfig(5, state=state)

    def new(self):
        file_path = tkFileDialog.askopenfilename(initialdir=self.scModel.get_dir(), title="Select base image file",
                                           filetypes=self.getMergedFileTypes())
        if file_path is None or file_path == '':
            return
        dir = os.path.split(file_path)[0]
        if (not self._check_dir(dir)):
            tkMessageBox.showinfo("Error", "Directory already associated with a project")
            return

        newProject = createProject(dir, base=file_path, suffixes=self.getMergedSuffixes(), tool='jtui',
                                     organization=self.prefLoader.get_key('organization'), username=self.get_username())
        if newProject is not None:
            self.scModel.__wrapped__ = newProject[0]
        self.scModel.__wrapped__.set_notifier(self.changeEvent)
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
        self.scModel.__wrapped__ = loadProject(path, username=self.get_username(), tool='jtui')
        self.scModel.set_notifier(self.changeEvent)
        if self.scModel.getProjectData('typespref') is None:
            self.scModel.setProjectData('typespref', getFileTypes(), excludeUpdate=True)
        self._setTitle()
        self.drawState()
        self.canvas.update()
        if self.scModel.start is not None:
            self.setSelectState('normal')
        try:
            export_info = self.validator.get_journal_exporttime(self.scModel.getName())

            if export_info is not None:
                if self.scModel.getProjectData("exporttime") is None:
                    tkMessageBox.showwarning("Journal Version Warning",
                                             "This version of the journal was not exported. Please check the browser for the latest version.")
                else:
                    local_journal = datetime.strptime(self.scModel.getProjectData("exporttime"), "%Y-%m-%d %H:%M:%S")
                    browser_journal = datetime.strptime(export_info, "%Y-%m-%d %H:%M:%S")

                    if local_journal < browser_journal:
                        tkMessageBox.showwarning("Journal Version Warning", "The browser version of this journal is newer.")
        except:
            tkMessageBox.showwarning("Journal Version Warning", "Unable to contact browser to verify if browser has a newer version of the journal.")

    def open(self):
        val = tkFileDialog.askopenfilename(initialdir=self.scModel.get_dir(), title="Select project file",
                                           filetypes=[("json files", "*.json"),("tgz files", "*.tgz")])
        if (val != None and len(val) > 0):
            try:
                self._open_project(val)
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                logging.getLogger('maskgen').error(
                    ' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                backup = val + '.bak'
                if os.path.exists(backup):
                    if tkMessageBox.askquestion('Possible Project Corruption Error',str(e) + ".  Do you want to restore from the backup?") == 'yes':
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
                ids = [self.scModel.addImage(f,cgi=cgi) for f in totalSet]
                self.canvas.select(ids[-1])
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

    def get_username(self):
            return self.prefLoader.get_key('username',default_value=get_username())

    def recomputeallrmask(self):
        for edge_id in self.scModel.getGraph().get_edges():
            self.scModel.reproduceMask(edge_id=edge_id)

    def fixit(self):
        video_tools.fixVideoMasks(self.scModel.getGraph(),self.scModel.start,
                                  self.scModel.getGraph().get_edge(self.scModel.start,self.scModel.end))

    def add_substitute_mask(self):
        edge = self.scModel.getGraph().get_edge(self.scModel.start,self.scModel.end)
        dialog = SubstituteMaskCaptureDialog(self, self.scModel)
        result = dialog.use_as_substitute.get()
        vidInputMask = getValue(edge, 'arguments.videoinputmaskname', '')
        vidInputMask = os.path.join(self.scModel.get_dir(), vidInputMask)
        if result == 'yes' and os.path.exists(vidInputMask) and not dialog.cancelled:
            self.scModel.removeSubstituteMasks()
            self.scModel.addSubstituteMasks(filename=vidInputMask)
        elif result == 'no' and self.scModel.hasSubstituteMasks():
            self.scModel.removeSubstituteMasks()
            self.scModel.notify((self.scModel.start, self.scModel.end), 'update_edge')

    def recomputeedgemask(self):
        analysis_params = {}
        errors = self.scModel.reproduceMask(analysis_params=analysis_params)
        nim = self.scModel.nextImage()
        self.img3 = ImageTk.PhotoImage(imageResizeRelative(self.scModel.maskImage(), (250, 250), nim.size).toPIL())
        self.img3c.config(image=self.img3)
        self.maskvar.set(self.scModel.maskStats())
        if errors is not None and len(errors) > 0:
            tkMessageBox.showerror('Recompute Mask Error','\n'.join(errors[(max(0,len(errors)-5)):]))

    def recomputedonormask(self):
        params = {}
        result = self.scModel.getCreatingOperation(self.scModel.end)
        if result is not None:
            args = result[1].getDonorProcessor(self.scModel.getLinkTool(self.scModel.start, self.scModel.end).getDefaultDonorProcessor())(
                self.scModel.getGraph(),
                self.scModel.start,
                self.scModel.end,
                result[0],
                self.scModel.getImageAndName(self.scModel.start),
                self.scModel.getImageAndName(self.scModel.end)).arguments()
            if len(args) > 0:
                d = ItemDescriptionCaptureDialog(self,
                                                 extract_default_values(args),
                                                 args,
                                                 'Donor Mask Construct')
                if d.argvalues is None:
                    return

                params = d.argvalues
        errors = self.scModel.reproduceMask(argument_params=params)
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
        vd = ValidationData(self.scModel)
        if vd.get_state() != 'yes':
            errorList = self.scModel.validate(external=True,status_cb=self.progress_bar.postChange)
        else:
            errorList = None
        message = None
        if errorList is not None and len(errorList) > 0:
            errorlistDialog = DecisionValidationListDialog(self, errorList, "Validation Errors")
            errorlistDialog.wait(self)
            if errorlistDialog.errorMessagesIncomplete():
                message = 'Validation Errors Exist'
            if not errorlistDialog.isok or not errorlistDialog.autofixesComplete():
                return False, message
        self.scModel.executeFinalNodeRules()
        processProjectProperties(self.scModel)
        self.getproperties()
        return True, message

    def export(self):
        status, message = self._preexport()
        if not status:
            return None
        val = tkFileDialog.askdirectory(initialdir='.', title="Export To Directory")
        if (val is not None and len(val) > 0):
            path, errorList = self.scModel.export(val,notifier=self.progress_bar.postChange)
            if len(errorList) > 0:
                ValidationListDialog(self, errorList, "Export Errors")
                return None
            else:
                tkMessageBox.showinfo("Export", "Complete")
                return path
        return None

    def exporttoS3(self):
        #status, message = True, 'x'
        status, message = self._preexport()
        if not status:
            return
        info = self.prefLoader.get_key('s3info')
        val = tkSimpleDialog.askstring("S3 Bucket/Folder", "Bucket/Folder",
                                       initialvalue=info if info is not None else '')
        if (val is not None and len(val) > 0):
            try:
                path, errorlist = self.scModel.export(self.prefLoader.getTempDir(),notifier=self.progress_bar.postChange)
                #path, errorlist = "/Users/Eric Robertson/Documents/c54fe7c293c6d01dc8ed5c520a375f1e.tgz",[]
                if len(errorlist) > 0:
                    ValidationListDialog(self, errorlist, "Export Errors")
                else:
                    self._update_export_state(location=val,pathname=path, additional_message=message)
                    self.openManager()
                    self.exportManager.upload(path, val, remove_when_done=False)

                uploaded = self.prefLoader.get_key('lastlogupload')
                uploaded = exportlogsto3(val,uploaded)
                # preserve the file uploaded
                if uploaded is not None:
                    self.prefLoader.save('lastlogupload',uploaded)
                self.prefLoader.save('s3info', val)
            except IOError as e:
                logging.getLogger('maskgen').warning("Failed to upload project: " + str(e))
                tkMessageBox.showinfo("Error", "Failed to upload export.  Check log file details.")
            except ClientError as e:
                logging.getLogger('maskgen').warning("Failed to upload project: " + str(e))
                tkMessageBox.showinfo("Error", "Failed to upload export")

    def openManager(self):
        if self.exportWatcher is not None and self.exportWatcher.winfo_exists():
            self.exportWatcher.lift(self)
        else:
            self.exportWatcher = ExportWatcherDialog(self, self.exportManager)

    def _promptRotate(self,donor_im,rotated_im, orientation):
        dialog = RotateDialog(self.master, donor_im, rotated_im, orientation)
        return dialog.rotate

    def createJPEGorTIFF(self):
        msgs, pairs = CopyCompressionAndExifGroupOperation(self.scModel).performOp(promptFunc=self._promptRotate)
        if msgs is not None and len(msgs) > 0:
            ValidationListDialog(self,msgs, 'Compression Errors')
            if not pairs:
                return
        if len(pairs) == 0:
            tkMessageBox.showwarning("Warning", "Leaf image nodes with base JPEG or TIFF images do not exist in this project")
        for pair in pairs:
            self.canvas.add(pair[0], pair[1])
        self.drawState()


    def setautosave(self):
        autosave_decision = self.prefLoader.get_key('autosave',default_value='600')
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
            msgs, status = self.scModel.addNextImage(file, mod=d.description)
            if msgs is not None:
                ValidationListDialog(self,msgs,'Connect Errors')
            if status:
                self.drawState()
                #self.canvas.add(self.scModel.start, self.scModel.end)
                self.processmenu.entryconfig(self.menuindices['undo'], state='normal')

    def nodeproxy(self):
        d = FileCaptureDialog(self,'Proxy',self.scModel.get_dir(),self.scModel.getProxy())
        if not d.cancelled:
            self.scModel.setProxy(d.current_file)
            self.drawState()

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
            #self.canvas.add(self.scModel.start, self.scModel.end)
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
            msgs, status = self.scModel.addNextImage(filename, mod=d.description, position=self.scModel._getCurrentPosition((0,75)))
            if msgs is not None:
                ValidationListDialog(self,msgs,'Connect Errors')
            if status:
                self.drawState()
                #self.canvas.add(self.scModel.start, self.scModel.end)
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
            msgs,pairs =self.scModel.imageFromGroup(grp, software=d.softwaretouse,
                                                          **self.resolvePluginValues(d.argvalues))
            self._addPairs(pairs)
            if msgs is not None and len(msgs) > 0:
                ValidationListDialog(self, msgs, 'Group Errors')
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
                msgs, pairs = self.scModel.mediaFromPlugin(filter)
                self._addPairs(pairs)
                if msgs is not None:
                    ValidationListDialog(self, msgs, "Plugin Errors")
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

    def get_image_from_cache(self, cache_name, image, size):
        """

        :param cache_name:
        :param image:
        :return:
        @type image: ImageWrapper
        """
        mim_time = image.file_mtime()
        if cache_name in self.image_cache:
            cache_image, cache_mim_time = self.image_cache[cache_name]
            if cache_mim_time == mim_time:
                return cache_image
        item = fixTransparency(imageResizeRelative(image, (250, 250), size)).toPIL()
        self.image_cache[cache_name] = (item,mim_time)
        return item

    def drawState(self):

        start_cache_name = self.scModel.start if self.scModel.start else '#empty@'
        sim = self.get_image_from_cache(start_cache_name,
                                        self.scModel.startImage(),None)
        nim = self.get_image_from_cache(start_cache_name + '#end' if self.scModel.end is None else self.scModel.end,
                                        self.scModel.nextImage(), None)
        im = self.scModel.maskImage()
        mim = self.get_image_from_cache('#mask' if self.scModel.end is None else start_cache_name + self.scModel.end,
                                        im,
                                        im.size if im is not None else sim.size)


        self.img1 = ImageTk.PhotoImage(sim)
        self.img2 = ImageTk.PhotoImage(nim)
        self.img3 = ImageTk.PhotoImage(mim)
        self.img1c.config(image=self.img1)
        self.img2c.config(image=self.img2)
        self.img3c.config(image=self.img3)
        self.l1.config(text=self.scModel.startImageName())
        self.l2.config(text=self.scModel.nextImageName())
        self.l3.config(text=self.scModel.maskImageName())
        self.maskvar.set(self.scModel.maskStats())

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
                getMetDataLoader().reload()
                self.prefLoader.save('s3info', val)
            except ClientError as e:
                tkMessageBox.showwarning("S3 Download failure", str(e))

    def validate(self):
        errorList = self.scModel.validate(external=True,status_cb=self.progress_bar.postChange)
        ValidationListDialog(self, errorList, "Validation Errors")

    def getsystemproperties(self):
        d = SystemPropertyDialog(self,self.getSystemPreferences(), self.prefLoader,
                                 property_change_actions={'username': UserPropertyChange(self.scModel)})

    def getproperties(self):
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

    def invertinput(self):
        self.scModel.invertInputMask()

    def viewcomposite(self):
        probes = self.scModel.getPathExtender().constructPathProbes()
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
            CompositeViewDialog(self, self.scModel.start, transformed[0][0].finalMask(), self.scModel.getImage(transformed[0][2]))

    def renametobase(self):
        self.scModel.renametobase()
        self._setTitle()

    def systemcheck(self):
        vc = VersionChecker()
        errors = [self.validator.test(),
                  ffmpeg_api.ffmpeg_tool_check(),
                  exif.toolCheck(),
                  selfVideoTest(),
                  check_graph_status(),
                  self.notifiers.check_status(),
                  vc.check_ffmpeg(),
                  vc.check_opencv(),
                  vc.check_dot()]
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
        """
        :param redacted: list of paths to not include in the export
        :return:
        """
        val = tkFileDialog.askdirectory(initialdir='.',
                                        title="Export " + self.scModel.startImageName() + " To Directory")
        if (val is not None and len(val) > 0):
            self.scModel.export_path(val)
            tkMessageBox.showinfo("Export", "Complete")

    def selectLink(self, start, end):
        if start == end:
            end = None
        if self.scModel.select((start, end)):
            self.drawState()
            if end is not None:
                self.canvas.showEdge(start, end)
            else:
                self.canvas.showNode(start)
            self.setSelectState('normal')

    def editallsemanticgroups(self):
        self.editgroups(self.scModel.getGraph().get_nodes())

    def editgroups(self, groupselection):
        d = AddRemove(self, "Set Semantic Group", 'Select a semantic group for these operations.',
                      getSemanticGroups(), information="semanticgroup")
        res = d.choice
        if res[0] is not None and len(res[0]) > 0:
            for start in groupselection:
                for end in groupselection:
                    edge = self.scModel.getGraph().get_edge(start, end)
                    if edge is not None:
                        if edge['op'] == 'Donor':
                            continue
                        grps = self.scModel.getSemanticGroups(start, end)
                        if res[0] not in grps and res[1] == "add":
                            grps.append(res[0])
                            self.scModel.setSemanticGroups(start, end, grps)
                        if res[0] in grps and res[1] == "remove":
                            grps.remove(res[0])
                            self.scModel.setSemanticGroups(start, end, grps)

    def selectgroup(self):
        self.editgroups(self.groupselection)


    def removegroup(self):
        if tkMessageBox.askyesno(title='Remove Group', message='Are you sure you want to remove this group of nodes?'):
            for name in self.groupselection:
                self.scModel.selectImage(name)
                self.remove()

    def select(self):
        self.drawState()
        self.setSelectState('normal')

    def _update_export_state(self, location='', pathname='', additional_message=''):
        s3 = 's3:// ' + location + ('' if location.endswith('/') else '/') +  os.path.basename(pathname)
        qacomment = self.scModel.getProjectData('qacomment')
        validation_person = self.scModel.getProjectData('validatedby')
        comment = 'Exported by ' + self.prefLoader.get_key('username')
        comment = comment + '\n {}: {}'.format('location', s3)
        comment = comment + '\n {}: {}'.format('additional_message', additional_message)
        comment = comment + '\n Journal Comment: ' + qacomment if qacomment is not None else comment
        if validation_person is not None:
            comment = comment + '\n Validated By: ' + validation_person
        return self.notifiers.update_journal_status(self.scModel.getName(),
                                                    self.scModel.getGraph().getCreator().lower(),
                                                    comment,
                                                    self.scModel.getGraph().get_project_type())

    def changeEvent(self, recipient, eventType, **kwargs):
        # UI not setup yet.  Occurs when project directory is used at command line
        if self.canvas is None:
            return True
        if eventType == 'label' and self.canvas is not None:
            self.canvas.redrawNode(recipient)
            return True
        if eventType in ['connect','add','remove','undo']:
            if prefLoader.get_key('autosave','') == 'L':
                try:
                    self.scModel.save()
                except Exception as e:
                    logging.getLogger('maskgen').error('Failed to incrementally save {}'.format(str(e)))

        if eventType == 'connect':
            self.canvas.add(recipient[0],recipient[1])
        elif eventType == 'add':
            self.canvas.addNew(recipient)
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
        if tkMessageBox.askyesno('Archive','Archive Probes'):
            archive_probes(self.scModel,reproduceMask=False)
        else:
            builders = [ColorCompositeBuilder,Jpeg2000CompositeBuilder]  if self.scModel.getGraph().get_project_type() == 'image' else \
              [HDF5CompositeBuilder]
            generator = ProbeGenerator(scModel=self.scModel,
                                       processors=[ProbeSetBuilder(scModel=self.scModel,
                                                                   compositeBuilders=builders),
                                                   DetermineTaskDesignation(self.scModel, inputFunction=fetch_qaData_designation)])
            ps = generator(saveTargets=False, keepFailures=True)
            for probe in ps:
                logging.getLogger('maskgen').info('{},{},{},{},{},{},{},{}'.format(
                    probe.targetBaseNodeId,
                    probe.edgeId,
                    probe.targetMaskFileName,
                    probe.donorBaseNodeId,
                    probe.donorMaskFileName,
                    os.path.exists(os.path.join(self.scModel.get_dir(),probe.targetMaskFileName)) \
                        if probe.targetMaskFileName is not None else False,
                    os.path.exists(os.path.join(self.scModel.get_dir(), getValue(probe.composites, 'jp2.file name', ''))),
                    os.path.exists(os.path.join(self.scModel.get_dir(), getValue(probe.composites,'color.file name', '')))))
                if probe.targetVideoSegments is not None:
                    for segment in probe.targetVideoSegments:
                        logging.getLogger('maskgen').info('{},{},{},{},{},{},{},{}'.format(segment.starttime,
                                                                                           segment.startframe,
                                                                                           segment.endtime,
                                                                                           segment.endframe,
                                                                                           segment.filename,
                                                                                           segment.media_type,
                                                                                           segment.frames,
                                                                                           segment.error))

    def startQA(self):
        from maskgen.validation.core import hasErrorMessages
        total_errors = self.scModel.validate()
        if hasErrorMessages(total_errors, lambda x: True):
            tkMessageBox.showerror("Validation Errors!", "It seems this journal has unresolved validation errors. "
                                                         "Please address these and try again.")
            ValidationListDialog(self, total_errors, "Validation Errors")
            return
        if self.scModel.getProjectData('validation') == 'yes':
            tkMessageBox.showinfo('QA', 'QA validation completed on ' + self.scModel.getProjectData('validationdate') +
                               ' by ' + self.scModel.getProjectData('validatedby') + '.')
        d = QAProjectDialog(self)
        d.valid = True

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
        exportmenu.add_command(label="Manager", command=self.openManager)

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
        filemenu.add_cascade(label="Rename to Base", command=self.renametobase)
        filemenu.add_cascade(label="System Check", command=self.systemcheck)
        filemenu.add_cascade(label="Reload Plugins", command=self.reloadplugins)
        #filemenu.add_cascade(label="Last Updates", command=self.updates)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
        filemenu.add_command(label="Quit without Save", command=self.quitnosave)

        menubar.add_cascade(label="File", menu=filemenu)

        self.processmenu = Menu(menubar, tearoff=0)
        self.processmenu.add_command(label="Add Media", command=self.add, accelerator="Ctrl+A")
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
        self.processmenu.add_command(label="Rename Final Media", command=self.renamefinal)
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
        validationmenu.add_command(label="Edit All Semantic Groups", command=self.editallsemanticgroups,accelerator="Ctrl+Shift+G")

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
        self.nodemenu.add_command(label="Edit", command=self.nodeedit)
        self.nodemenu.add_command(label="Connect To", command=self.connectto)
        self.nodemenu.add_command(label="Export", command=self.exportpath)
        self.nodemenu.add_command(label="Compare To", command=self.compareto)
        self.nodemenu.add_command(label="View Composite", command=self.viewcomposite)
        self.nodemenu.add_command(label="View Donor", command=self.viewdonor)
        self.nodemenu.add_command(label="Remove", command=self.remove)
        self.nodemenu.add_command(label="Compress", command=self.compress)
        self.nodemenu.add_command(label="Analyze", command=self.imageanalysis)

        self.nodemenu.add_command(label="Proxy", command=self.nodeproxy)

        self.edgemenu = Menu(self.master, tearoff=0, postcommand=self.updateEdgeMenu)
        self.edgemenu.add_command(label="Select", command=self.select)
        self.edgemenu.add_command(label="Edit", command=self.edit)
        self.edgemenu.add_command(label="Inspect", command=self.view)
        self.edgemenu.add_command(label="Remove", command=self.remove)
        self.edgemenu.add_command(label="Composite Mask", command=self.viewselectmask)
        self.edgemenu.add_command(label="View Transformed Mask", command=self.viewtransformed)
        self.edgemenu.add_command(label="View Overlay Mask", command=self.viewmaskoverlay)
        self.edgemenu.add_command(label="Recompute Mask", command=self.recomputeedgemask)
        self.edgemenu.add_command(label="Invert Input Mask", command=self.invertinput)
        self.edgemenu.add_command(label="Substitute Mask", command=self.add_substitute_mask)

        self.filteredgemenu = Menu(self.master, tearoff=0)
        self.filteredgemenu.add_command(label="Select", command=self.select)
        self.filteredgemenu.add_command(label="Inspect", command=self.view)
        self.filteredgemenu.add_command(label="Remove", command=self.remove)
        self.filteredgemenu.add_command(label="Composite Mask", command=self.viewselectmask)
        self.filteredgemenu.add_command(label="Recompute", command=self.recomputeedgemask)

        self.donoredgemenu = Menu(self.master, tearoff=0)
        self.donoredgemenu.add_command(label="Select", command=self.select)
        self.donoredgemenu.add_command(label="Inspect", command=self.view)
        self.donoredgemenu.add_command(label="Remove", command=self.remove)
        self.donoredgemenu.add_command(label="Recompute", command=self.recomputedonormask)

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
        self.progress_bar = ProgressBar(self.master)
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky=S + E + W)
        self.progress_bar.grid_propagate(True)

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
        elif eventName == 'rcDonorEdge':
            self.donoredgemenu.post(event.x_root, event.y_root)
        elif eventName == 'rcGroup':
            self.groupselection = event.items
            self.groupmenu.post(event.x_root, event.y_root)
        elif eventName == 'n':
            self.drawState()

    def updateEdgeMenu(self):
        self.edgemenu.entryconfig(index=9, state=self.scModel.substitutesAllowed())

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
        props = [ProjectProperty(name='username',
                                 type=getMetDataLoader().getProperty('username').type,
                                 description='User Name',
                                 information='Journal User Name'),
                 ProjectProperty(name='organization', type='text',
                                 description='Organization',
                                 information="journal user's organization"),
                 ProjectProperty(name='log.validation', type='yesno',
                                 description="Log Validation Status",
                                 information='Log Validation'),
                 ProjectProperty(name='apiurl', type='text',
                                 description="API URL",
                                 information='Validation API URL'),
                 ProjectProperty(name='apitoken', type='text',
                                 description="API Token",
                                 information='Validation API URL'),
                 ProjectProperty(name='temp.dir',
                                 type='folder:' + os.path.expanduser('~'),
                                 description="Tempoary Directory for Export",
                                 information='Tempoary Directory for Export')

                 ]
        for k, v in self.notifiers.get_properties().iteritems():
            props.append(ProjectProperty(name=k, type='text', description=k,
                                         information='notification property'))
        return props

    def __init__(self, dir, master=None, base=None, uiProfile=UIProfile()):
        Frame.__init__(self, master)
        self.uiProfile = uiProfile
        self.exportManager = ExportManager()
        self.exportWatcher = None
        plugins.loadPlugins()
        self.gfl = GroupFilterLoader()
        newProject = createProject(dir, base=base,
                                   suffixes=self.getMergedSuffixes(),
                                   username=self.get_username(),
                                   organization=self.prefLoader.get_key('organization'),
                                   tool='jtui')
        if newProject is None:
            logging.getLogger('maskgen').warning( 'Invalid project director ' + dir)
            sys.exit(-1)
        self.scModel = wrapt.ObjectProxy(newProject[0])
        self.scModel.set_notifier(self.changeEvent)
        self.updateFileTypePrefs()
        self.createWidgets()
        self.startedWithNewProject = newProject[1]

    def initCheck(self):
        if self.prefLoader.get_key('username',None) is None:
            self.getsystemproperties()
        try:
            git_branch = self.prefLoader.get_key('git.branch',default_value='master')
            sha, message = UpdaterGitAPI(branch=git_branch).isOutdated()
            sha_op, message_op = OperationsUpdaterGitAPI(branch=git_branch).isOutdated()
            if sha is not None:
                update_message = 'Last Update message {0}'.format(message.encode('ascii', errors='xmlcharrefreplace')) \
                    if message else ''
                tkMessageBox.showinfo('Update to JT Available', 'New Version: {0} {1}'.format(sha, update_message))
            elif sha_op is not None:
                update_message = 'Last Update message {0}'.format(
                    message_op.encode('ascii', errors='xmlcharrefreplace')) if message_op else ''
                tkMessageBox.showinfo('Update to JT Available', 'New Version: {0} {1}'.format(sha_op, update_message))
        except:
            tkMessageBox.showwarning('JT Update Status', 'Unable to verify latest version of JT due to connection '
                                                         'error to GitHub. See logs for details')
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
    validator = ValidationAPIComposite(prefLoader,external=True)
    errors = [validator.test(),
              ffmpeg_api.ffmpeg_tool_check(),
              exif.toolCheck(),
              selfVideoTest(),
              check_graph_status(),
              notifiers.check_status()]
    error_count = 0
    for error in errors:
        if error is not None:
            logging.getLogger('maskgen').error(error)
            error_count += 1
    logging.getLogger('maskgen').info('System check complete')
    return error_count == 0

def runui(argv=None):
    if (argv is None):
        argv = sys.argv

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--project', help='project directory', required=False)
    parser.add_argument('--test',action='store_true', help='For testing')
    parser.add_argument('--base', help='base image or video',  required=False)
    parser.add_argument('--s3', help="s3 bucket/directory ", nargs='+')
    parser.add_argument('--debug', help="debug logging ",action='store_true')
    parser.add_argument('--http', help="http address and header params", nargs='+')

    imgdir = None
    argv = argv[1:]
    logging.getLogger('maskgen').info('Version ' + maskgen.__version__)
    uiProfile = UIProfile()
    args = parser.parse_args(argv)

    if args.project is not None:
        imgdir = args.project
    if args.http is not None:
        loadHTTP(args.http)
    elif args.s3 is not None:
        loadS3(args.s3)

    loadAnalytics()
    prefLoader = maskGenPreferences
    maskgen.preferences_initializer.initialize(prefLoader)
    if args.test:
        if not headless_systemcheck(prefLoader):
            sys.exit(1)
        return
    if args.debug:
        set_logging_level(logging.DEBUG)
    root = Tk()
    gui = MakeGenUI(imgdir, master=root,
                    base=args.base if args.base is not None else None, uiProfile=uiProfile)

    #root.protocol("WM_DELETE_WINDOW", lambda: gui.quit())
    interval =  prefLoader.get_key('autosave')
    if interval and interval not in [ '0' , 'L']:
        execute_every(float(interval),saveme, saver=gui)

    gui.after_idle(gui.initCheck)
    gui.mainloop()

