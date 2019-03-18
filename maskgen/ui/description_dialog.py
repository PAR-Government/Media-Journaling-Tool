# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import matplotlib
matplotlib.use("TkAgg")
import ttk
import tkMessageBox
from maskgen.group_filter import GroupFilterLoader
import  tkFileDialog, tkSimpleDialog
from PIL import ImageTk
from maskgen.ui.autocomplete_it import AutocompleteEntryInText
from maskgen.tool_set import imageResize, imageResizeRelative, fixTransparency, openImage, openFile, validateTimeString, \
    validateCoordinates, getMaskFileTypes, getImageFileTypes, videofiletypes, coordsFromString, IntObject, get_icon,convertToVideo
from maskgen.scenario_model import Modification,ImageProjectModel
from maskgen.services.probes import CompositeExtender
from maskgen.video_tools import get_start_frame_from_segment, get_start_time_from_segment, get_file_from_segment,\
    get_end_frame_from_segment
from maskgen.support import getValue
import numpy as np
from tkintertable import TableCanvas, TableModel
from maskgen.image_wrap import ImageWrapper
from functools import partial
from maskgen.group_filter import GroupOperationsLoader
from maskgen.ui.PictureEditor import PictureEditor
from maskgen.ui.CompositeViewer import  ScrollCompositeViewer
from maskgen.validation.core import ValidationMessage,Severity
from maskgen.ui.semantic_frame import *
from maskgen.ui.ui_tools import SelectDialog, EntryDialog, TimeWidget


def resolve_argument_type(arg_type, source_type):
    """
    Alter type based on source file type
    :param arg_type:
    :param source_type:
    :return:
    """
    if arg_type == "frame_or_time":
        if source_type == "audio":
           return "time"
        else:
            return "int[0:1000000000]"  # Frame Number
    return arg_type

def checkMandatory(grpLoader, operationName, sourcefiletype, targetfiletype, argvalues):
    """

    :param grpLoader:
    :param operationName:
    :param sourcefiletype:
    :param targetfiletype:
    :param argvalues:
    :return:
    @type grpLoader: GroupOperationsLoader
    """
    ok = True
    op = grpLoader.getOperationWithGroups(operationName,fake=True)
    for k, v in op.mandatoryparameters.iteritems():
        if 'source' in v and v['source'] != sourcefiletype:
            continue
        if 'target' in v and v['target'] != targetfiletype:
            continue
        ok &= (k in argvalues and argvalues[k] is not None and len(str(argvalues[k])) > 0)
    for k, v in op.optionalparameters.iteritems():
        if 'source' in v and v['source'] != sourcefiletype:
            continue
        if 'target' in v and v['target'] != targetfiletype:
            continue
        if 'rule' in v and len(v['rule']) > 0:
            nomatches = [rk for rk, rv in v['rule'].iteritems() if rk in argvalues and argvalues[rk] not in rv]
            ok &= (len(nomatches) > 0 or
                   (k in argvalues and argvalues[k] is not None and len(str(argvalues[k])) > 0))
    if op.parameter_dependencies is not None:
        for param_name, param_requirements in op.parameter_dependencies.iteritems():
            if param_name in argvalues and argvalues[param_name] in param_requirements:
                checks = param_requirements[argvalues[param_name]]
                if type(checks) in [str, unicode]:
                    checks = [checks]
                for check_name in checks:
                    ok &= (check_name in argvalues and argvalues[check_name] is not None and len(str(argvalues[check_name])) > 0)
    return ok

def checkValue(name, value_type, value):
    """
    Check the value given the type
    :param name:
    :param type:
    :param value:
    :return: None,error message if invalid or value,None if valid
    @type name: str
    @type value: str
    @rtype: (str,str)
    """
    if value is not None and (type(value) != 'str' or len(value) > 0):
        if value_type.startswith('float'):
            try:
                vals = [float(x) for x in value_type[value_type.rfind('[') + 1:-1].split(':')]
            except ValueError:
                vals = [-sys.float_info.max, sys.float_info.max]
            try:
                value = float(value)
                if value < vals[0] or value > vals[1]:
                    raise ValueError(value)
            except:
                return None, 'Invalid value for ' + name + '; not in range ' + str(vals[0]) + ' to ' + str(
                    vals[1])
        elif value_type.startswith('int'):
            try:
                vals = [int(x) for x in value_type[value_type.rfind('[') + 1:-1].split(':')]
            except ValueError:
                vals = [-sys.maxint, sys.maxint]
            try:
                value = int(value)
                if value < vals[0] or value > vals[1]:
                    raise ValueError(value)
            except:
                return None, 'Invalid value for ' + name + '; not in range ' + str(vals[0]) + ' to ' + str(
                    vals[1])
        elif value_type == 'time':
            if not validateTimeString(value):
                return None, 'Invalid time value for ' + name + '; not in format 00:00:00.000000 for time or 0 for frame number'
        elif value_type == 'coordinates':
            if not validateCoordinates(value):
                return None, 'Invalid coordinate value for ' + name + '; not (0,0) format'
    return value, None


def fillTextVariable(obj, row, event):
    """
    Call back for a StringVar or Text Widget object
    get the object's text widget at row and pull the text
    :param obj: PropertyFrame widgets
    :param row:  row number of the widet
    :param event: not used
    :return:
    @type obj: PropertyFrame
    @type row: int
    """
    obj.values[row].set(obj.widgets[row].get(1.0, END))


def promptForURLAndFillButtonText(obj, id, row):
    """
    Prompt for a URL.
    Set the button's text, identify by the id.
    :param obj:
    :param dir: Starting place for file inspection
    :param id: button identitifer
    :param row:
    :param filetypes:
    @type obj: PropertyFrame
    @type row: int
    @type filetypes: [(str,str)]
    :return:
    """
    var = obj.values[row]
    val = URLCaptureDialog(obj, var.get().split('\n'))
    url_string = '\n'.join(val.urls).strip()
    var.set(url_string)
    items = [re.sub('^http[s]*://', '', item) for item in val.urls]
    obj.buttons[id].configure(text=' '.join(items)[:40],
                               width=len(' '.join(items)),
                               height =(len(val.urls))+1)

def promptForFileAndFillButtonText(obj, dir, id, row, filetypes):
    """
    Prompt for a file given the file types.
    Set the button's text, identify by the id.
    :param obj:
    :param dir: Starting place for file inspection
    :param id: button identitifer
    :param row:
    :param filetypes:
    @type obj: PropertyFrame
    @type row: int
    @type filetypes: [(str,str)]
    :return:
    """
    if '*.*' in [t[1] for t in filetypes]:
        filetypes = []
    val = tkFileDialog.askopenfilename(initialdir=dir, title="Select " + id,
                                       filetypes=filetypes)
    var = obj.values[row]
    if val is not None and len(val) > 0:
        var.set(val)
    else:
        var.set('')
        val = None
    obj.buttons[id].configure(text=os.path.split(val)[1] if (val is not None and len(val) > 0) else ' ' * 30)


def promptForFolderAndFillButtonText(obj, dir, id, row):
    """
    Prompt for a folder given the file types.
    Set the button's text, identify by the id.
    :param obj:
    :param dir: Starting place for browser
    :param id: button identitifer
    :param row:
    @type obj: PropertyFrame
    @type row: int
    :return:
    """
    val = tkFileDialog.askdirectory(initialdir=dir, title="Select " + id)
    var = obj.values[row]
    if val is not None and len(val) > 0:
        var.set(val)
    else:
        val = None
    obj.buttons[id].configure(text=os.path.split(val)[1] if (val is not None and len(val) > 0) else ' ' * 30)


def promptForBoxPairAndFillButtonText(obj, id, row):
    """
    Prompt for a donor and place the name in the button text
    Set the variable to the  selected image node name
    :param obj:
    :param id:
    :param var:
    @type obj: PropertyFrame
    @type row: int
    :return:
    """
    extra_args = obj.extra_args
    var = obj.values[row]
    initial_value  = var.get()
    full_value_left = '(0,0,{},{})'.format(extra_args['start_im'].size[0],extra_args['start_im'].size[1])
    full_value_right = '(0,0,{},{})'.format(extra_args['end_im'].size[0], extra_args['end_im'].size[1])
    parts =  initial_value.split(':') if initial_value is not None and len(initial_value) > 0 \
        else [full_value_left,full_value_right,'0']
    left_box = coordsFromString(parts[0])
    right_box = coordsFromString(parts[1])
    angle = int(float(parts[2]))
    d = PointsViewDialog (obj,left_box, right_box,angle,
                          extra_args['start_im'], extra_args['end_im'],
                          extra_args['model'],
                          op=extra_args['op'],
                          argument_name=id)
    if not d.cancelled:
        res = d.getStringConfiguration()
        var.set(res if (res is not None and len(res) > 0) else None)
        obj.buttons[id].configure(text=res if (res is not None and len(res) > 0) else '')

def promptForDonorandFillButtonText(obj, id, row):
    """
    Prompt for a donor and place the name in the button text
    Set the variable to the  selected image node name
    :param obj:
    :param id:
    :param var:
    @type obj: PropertyFrame
    @type row: int
    :return:
    """
    d = ImageNodeCaptureDialog(obj, obj.propertyFunction.scModel)
    res = d.selectedImage
    var = obj.values[row]
    var.set(res if (res is not None and len(res) > 0) else None)
    obj.buttons[id].configure(text=res if (res is not None and len(res) > 0) else '')

def promptForParameter(parent, dir, argumentTuple, filetypes, initialvalue):
    """
     argumentTuple is (name,dict(values, type,descriptipn))
     type is list, imagefile, donor, float, int, time.  float and int have a range in the follow format: [-80:80]

    """
    res = None
    if argumentTuple[1]['type'] == 'file:image':
        val = tkFileDialog.askopenfilename(initialdir=dir, title="Select " + argumentTuple[0], filetypes=filetypes)
        if (val != None and len(val) > 0):
            res = val
    elif argumentTuple[1]['type'].startswith('file:'):
        prop = argumentTuple[1]['type']
        typematch = '*.' + prop[prop.find(':') + 1:]
        typename = prop[prop.find(':') + 1:].upper()
        val = tkFileDialog.askopenfilename(initialdir=dir, title="Select " + argumentTuple[0],
                                           filetypes=[(typename, typematch)])
        if (val != None and len(val) > 0):
            res = val
    elif argumentTuple[1]['type'].startswith('fileset:'):
        initialdir_parts = tuple(argumentTuple[1]['type'][8:].split('/'))
        initialdir = os.path.join(*tuple(initialdir_parts))
        val = tkFileDialog.askopenfilename(initialdir=initialdir, title="Select " + argumentTuple[0],
                                           filetypes=[('Text', '*.txt')])
        if (val != None and len(val) > 0):
            res = val
    elif argumentTuple[1]['type'].startswith('donor'):
        d = ImageNodeCaptureDialog(parent, parent.scModel)
        res = d.selectedImage
    elif argumentTuple[1]['type'].startswith('float'):
        v = argumentTuple[1]['type']
        vals = [float(x) for x in v[v.rfind('[') + 1:-1].split(':')]
        res = tkSimpleDialog.askfloat("Set Parameter " + argumentTuple[0], argumentTuple[1]['description'],
                                      minvalue=vals[0], maxvalue=vals[1],
                                      parent=parent, initialvalue=initialvalue)
    elif argumentTuple[1]['type'].startswith('int'):
        v = argumentTuple[1]['type']
        vals = [int(x) for x in v[v.rfind('[') + 1:-1].split(':')]
        res = tkSimpleDialog.askinteger("Set Parameter " + argumentTuple[0], argumentTuple[1]['description'],
                                        minvalue=vals[0], maxvalue=vals[1],
                                        parent=parent, initialvalue=initialvalue)
    elif argumentTuple[1]['type'] == 'list':
        d = SelectDialog(parent, "Set Parameter " + argumentTuple[0], argumentTuple[1]['description'],
                         argumentTuple[1]['values'])
        res = d.choice
    elif argumentTuple[1]['type'] == 'yesno':
        d = SelectDialog(parent, "Set Parameter " + argumentTuple[0], argumentTuple[1]['description'], ['yes', 'no'])
        res = d.choice
    elif argumentTuple[1]['type'] == 'time':
        d = EntryDialog(parent, "Set Parameter " + argumentTuple[0], argumentTuple[1]['description'],
                        validateTimeString, initialvalue=initialvalue)
        res = d.choice
    elif argumentTuple[1]['type'] == 'coordinates':
        d = EntryDialog(parent, "Set Parameter " + argumentTuple[0], argumentTuple[1]['description'],
                        validateCoordinates, initialvalue=initialvalue)
        res = d.choice
    elif argumentTuple[1]['type'].startswith('listfromfile:'):
        filename = getFileName(argumentTuple[1]['type'][13:])
        if not os.path.isfile(filename):
            d = EntryDialog(parent, "Set Parameter " + argumentTuple[0], argumentTuple[1]['description'], None,
                            initialvalue=initialvalue)
            res = d.choice
        else:
            with open(filename) as f:
                values = sorted(f.read().splitlines())
            d = SelectDialog(parent, "Set Parameter " + argumentTuple[0], argumentTuple[1]['description'], values)
            res = d.choice
    else:
        d = EntryDialog(parent, "Set Parameter " + argumentTuple[0], argumentTuple[1]['description'], None,
                        initialvalue=initialvalue)
        res = d.choice
    return res


def getCategory(grpLoader,mod):
    """

    :param grpLoader:
    :param mod:
    :return:
     @type grpLoader: GroupOperationsLoader
     @mod mod: Operation
    """
    if mod.category is not None and len(mod.category) > 0:
        return mod.category
    return grpLoader.getCategoryForOperation(mod.operationName)

def tupletostring(tuple):
    strv = ''
    for item in tuple[1:]:
        if type(item) is str:
            strv = strv + item + ' '
        else:
            strv = strv + str(item) + ' '
    return strv


def viewInfo(description_information):
    tkMessageBox.showinfo(description_information[0],
                          description_information[1] if description_information[1] is not None else 'Undefined')


class MyDropDown(OptionMenu):

    var = None
    command = None

    def __init__(self, master, oplist, initialValue=None,command=None):
        if initialValue is None:
            initialValue = oplist[0] if len(oplist) > 0 else ''
        self.var = StringVar()
        self.var.set(initialValue)
        self.command = command
        OptionMenu.__init__(self, master, self.var,'')
        for val in oplist:
            self.children['menu'].add_command(label=val, command=lambda v=self.var, l=val: self.set(l))

    def set_completion_list(self, values, initialValue=None):
        if initialValue is None:
            initialValue = values[0] if len(values) > 0 else ''
        if initialValue not in values:
            initialValue = ''
        self.children['menu'].delete(0, END)
        for val in values:
            self.children['menu'].add_command(label=val, command=lambda v=self.var, l=val: self.set(l))
        self.var.set(initialValue)

    def get(self):
        return self.var.get()

    def set(self,v):
        self.var.set(v)
        if self.command is not None:
            self.command(self.var.get())

    def bind(self, name, command):
        self.command = command

class PropertyFunction:
    """
    Set and Get values for a property for a given name.
    Used by general UI frames and property updaters, regardless of the source of the property (e.g. node, edge, system).
    """

    def getValue(self, name):
        return None

    def setValue(self, name,value):
        return None

class DescriptionCaptureDialog(Toplevel):
    photo = None
    c = None

    def __init__(self, parent, uiProfile, scModel, targetfiletype, end_im, name, description=None):
        """

        :param parent:
        :param uiProfile:
        :param scModel:
        :param targetfiletype:
        :param im:
        :param name:
        :param description:
        @type scModel: ImageProjectModel
        """
        self.im = None
        self.dir = scModel.get_dir()
        self.uiProfile = uiProfile
        self.end_im = end_im
        self.start_im = scModel.startImage()
        self.parent = parent
        self.cancelled = True
        self.argBox = None
        self.scModel = scModel
        self.argvalues = {}
        self.arginfo = []
        self.op = None
        self.inputMaskName = None
        self.sourcefiletype = scModel.getStartType()
        self.targetfiletype = targetfiletype
        self.argvalues = description.arguments if description is not None else {}
        self.description = description if description is not None else Modification('', '')
        self.softwareLoader = SoftwareLoader()
        Toplevel.__init__(self, parent)
        self.withdraw()  # remain invisible for now
        # If the master is not viewable, don't
        # make the child transient, or else it
        # would be opened withdrawn
        if parent.winfo_viewable():
            self.transient(parent)

        self.title(name)
        self.parent = parent
        self.result = None
        body = Frame(self)
        self.initial_focus = self.body(body)
        body.pack_propagate(True)
        self.buttonbox()
        body.pack(padx=5, pady=5)

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        if self.parent is not None:
            self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                      parent.winfo_rooty() + 50))

        self.deiconify()  # become visibile now

        self.initial_focus.focus_set()

        # wait for window to appear on screen before calling grab_set
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def destroy(self):
        '''Destroy the window'''
        self.initial_focus = None
        Toplevel.destroy(self)

    def newsoftware(self, event):
        sname = self.e4.get()
        self.e5.set_completion_list(self.softwareLoader.get_versions(sname,software_type=self.sourcefiletype),
                                    initialValue=self.softwareLoader.get_preferred_version(name=sname))

    def buildArgBox(self, opname):
        if self.argBox is not None:
            self.argBox.destroy()
        for argumentTuple in self.arginfo:

            if argumentTuple[0] not in self.argvalues and \
                'defaultvalue' in argumentTuple[1]:
                self.argvalues[argumentTuple[0]] = argumentTuple[1]['defaultvalue']

        properties = [ProjectProperty(name=argumentTuple[0],
                                      description=argumentTuple[0],
                                      information=argumentTuple[1]['description'] if 'description' in argumentTuple[1] else '',
                                      type=resolve_argument_type(argumentTuple[1]['type'], self.sourcefiletype),
                                      values=self.op.getParameterValuesForType(argumentTuple[0], self.sourcefiletype),
                                      value=self.argvalues[argumentTuple[0]] if argumentTuple[
                                                                                    0] in self.argvalues else None) \
                      for argumentTuple in self.arginfo]
        self.argBox = PropertyFrame(self.argBoxMaster, properties,
                                propertyFunction=EdgePropertyFunction(properties, self.scModel),
                                changeParameterCB=self.changeParameter,
                                extra_args={'end_im': self.end_im,
                                            'start_im':self.start_im,
                                            'model': self.scModel,
                                            'op': opname},
                                dir=self.dir)
        self.argBox.pack()

    def newcommand(self, event):
        self.op = self.scModel.getGroupOperationLoader().getOperationWithGroups(self.opname.get())
        self.arginfo = []
        if self.op is not None:
            for k, v in self.op.mandatoryparameters.iteritems():
                if 'source' in v and v['source'] != self.sourcefiletype:
                    continue
                if 'target' in v and v['target'] != self.targetfiletype:
                    continue
                self.arginfo.append((k, v))
            for k, v in self.op.optionalparameters.iteritems():
                if 'source' in v and v['source'] != self.sourcefiletype:
                    continue
                if 'target' in v and v['target'] != self.targetfiletype:
                    continue
                self.arginfo.append((k, v))
        self.buildArgBox(self.opname.get())
        if self.okButton is not None:
            self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)

    def organizeOperationsByCategory(self):
        return self.scModel.getGroupOperationLoader().getOperationsByCategoryWithGroups(self.sourcefiletype, self.targetfiletype)

    def newcategory(self, event):
        opByCat = self.organizeOperationsByCategory()
        if self.e1.get() in opByCat:
            self.oplist = opByCat[self.e1.get()]
            self.opname.set(self.oplist[0] if self.oplist else "")
            self.newcommand(event)
        else:
            self.oplist = []

    def body(self, master):
        top = Frame(master)
        bottom = Frame(master)
        self.argBoxMaster = bottom
        self.topBody(top)
        self.bottomBody(bottom)
        master.pack_propagate(True)
        top.pack_propagate(True)
        top.pack(padx=5, pady=5)
        bottom.pack(padx=5, pady=5)

    def bottomBody(self, master):
        return self.buildArgBox(self.opname.get())

    def topBody(self, master):
        self.okButton = None

        self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.end_im, (250, 250))).toPIL())
        self.c = Canvas(master, width=250, height=250)
        self.c.create_image(125, 125, image=self.photo, tag='imgd')
        self.c.grid(row=0, column=0, columnspan=2)
        Label(master, text="Category:").grid(row=1, sticky=W)
        Label(master, text="Operation:").grid(row=2, sticky=W)
        # self.attachImage = ImageTk.PhotoImage(file="icons/question.png")
        self.b = Button(master, bitmap='info', text="Help", command=self.help, borderwidth=0, relief=FLAT)
        self.b.grid(row=2, column=3)
        Label(master, text="Description:").grid(row=3, sticky=W)
        Label(master, text="Software Name:").grid(row=4, sticky=W)
        Label(master, text="Software Version:").grid(row=5, sticky=W)
        #Label(master, text='Semantic Groups:', anchor=W, justify=LEFT).grid(row=6, column=0)

        self.semanticFrame = SemanticFrame(master)
        self.semanticFrame.grid(row=6,column=0,columnspan=3,sticky=W)
        row = 8
        Label(master, text='Parameters:', anchor=W, justify=LEFT).grid(row=row, column=0, columnspan=2)
        row += 1


        self.opname = StringVar()
        self.opname.set(self.description.operationName)
        cats = self.organizeOperationsByCategory()
        catlist = list(cats.keys())
        catlist.sort()
        self.oplist = cats[catlist[0]] if len(cats) > 0 else []
        self.e1 = MyDropDown(master, catlist, command=self.newcategory)
        self.e2 = Button(master, textvar=self.opname, command=self.select_op)
        self.e4 = MyDropDown(master, sorted(self.softwareLoader.get_names(self.sourcefiletype), key=str.lower), command=self.newsoftware)
        self.e5 = AutocompleteEntryInText(master, values=[], takefocus=False, width=40)
        self.e1.bind("<Return>", self.newcategory)
        self.e1.bind("<<ComboboxSelected>>", self.newcategory)
        self.e2.bind("<Return>", self.select_op)
        self.e4.bind("<Return>", self.newsoftware)
        self.e4.bind("<<ComboboxSelected>>", self.newsoftware)
        self.e3 = Text(master, height=2, width=40, font=('Times', '14'), relief=RAISED, borderwidth=2)

        self.e1.grid(row=1, column=1, sticky=EW)
        self.e2.grid(row=2, column=1, sticky=EW)
        self.e3.grid(row=3, column=1, sticky=EW)
        self.e4.grid(row=4, column=1, sticky=EW)
        self.e5.grid(row=5, column=1)

        if self.description is not None:
            if self.description.semanticGroups is not None:
                pos = 1
                for grp in self.description.getSemanticGroups():
                    self.semanticFrame.insertListbox(pos,grp)
                    pos += 1
            if (self.description.inputMaskName is not None):
                self.inputMaskName = self.description.inputMaskName
            if self.description.operationName is not None and len(self.description.operationName) > 0:
                selectCat = getCategory(self.scModel.getGroupOperationLoader(),self.description)
                self.e1.set_completion_list(catlist, initialValue=selectCat)
                self.oplist = cats[selectCat] if selectCat in cats else []
                # self.e2.set_completion_list(oplist, initialValue=self.description.operationName)
            if (self.description.additionalInfo is not None):
                self.e3.delete(1.0, END)
                self.e3.insert(1.0, self.description.additionalInfo)
            self.newcommand(None)

        if self.description.software is not None:
            self.e4.set_completion_list(sorted(self.softwareLoader.get_names(self.sourcefiletype), key=str.lower),
                                        initialValue=self.description.software.name)
            self.e5.set_completion_list(sorted(self.softwareLoader.get_versions(self.description.software.name,
                                                                                software_type=self.sourcefiletype,
                                                                                version=self.description.software.version)),
                                        initialValue=self.description.software.version)
        else:
            self.e4.set_completion_list(sorted(self.softwareLoader.get_names(self.sourcefiletype), key=str.lower),
                                        initialValue=self.softwareLoader.get_preferred_name())
            self.e5.set_completion_list(
                sorted(self.softwareLoader.get_versions(self.softwareLoader.get_preferred_name(),
                                                        software_type=self.sourcefiletype)),
                initialValue=self.softwareLoader.get_preferred_version(self.softwareLoader.get_preferred_name()))

        return self.e1  # initial focus

    def set_op_name(self,name):
        self.opname.set(name)
        self.newcommand(None)

    def select_op(self):
        if len(self.oplist) > 0:
            SelectDialog(self,
                         "Set Operation",
                         "Select an operation",
                         self.oplist,
                         information="operation",
                         initial_value=self.opname.get(),
                         callback=self.set_op_name)
        else:
            tkMessageBox.showerror("No Operations", "There are no available operations under the current category.")

    def __getinfo(self,name):
        for k,v in self.arginfo:
            if k == name:
                return v
        return None

    def __checkParams(self):
        ok = True
        for k,v in self.argvalues.iteritems():
            info = self.__getinfo(k)
            if info is None:
                continue
            cv,error = checkValue(k,info['type'],v)
            if v is not None and len(str(v)) > 0 and cv is None:
                ok = False
        ok &= checkMandatory(self.scModel.getGroupOperationLoader(),self.opname.get(),self.sourcefiletype,self.targetfiletype,self.argvalues)
        return ok

    def buttonbox(self):
        box = Frame(self)
        self.okButton = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE,
                               state=ACTIVE if self.__checkParams() else DISABLED)
        self.okButton.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Escape>", self.cancel)
        box.pack(side=BOTTOM)

    def ok(self, event=None):

        self.withdraw()
        self.update_idletasks()
        try:
            self.apply()
        finally:
            self.cancel()

    def changeParameter(self, name, type, value):
        self.argvalues[name] = value
        if name == 'inputmaskname' and value is not None:
            self.inputMaskName = value
        if self.okButton is not None:
            self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)

    def help(self):
        op = self.scModel.getGroupOperationLoader().getOperationWithGroups(self.opname.get())
        if op is not None:
            tkMessageBox.showinfo(op.name, op.description if op.description is not None and len(
                op.description) > 0 else 'No description')

    def cancel(self):
        if self.cancelled:
            self.description = None
        # put focus back to the parent window
        if self.parent is not None:
            self.parent.focus_set()
        self.destroy()

    def apply(self):
        self.cancelled = False
        self.description.setFromOperation(self.scModel.getGroupOperationLoader().getOperationWithGroups(self.opname.get(),fake=True),
                                          filetype = self.sourcefiletype)
        self.description.setOperationName(self.opname.get())
        self.description.setAdditionalInfo(self.e3.get(1.0, END).strip())
        self.description.setInputMaskName(self.inputMaskName)
        self.description.semanticGroups =  list(self.semanticFrame.getListContents(0, END))
        self.description.setArguments(
            {k: v for (k, v) in self.argvalues.iteritems() if v is not None  and len(str(v)) > 0 and (k in [x[0] for x in self.arginfo])})
        self.description.setSoftware(Software(self.e4.get(), self.e5.get()))
        if (self.softwareLoader.add(self.description.software)):
            self.softwareLoader.save()


class ItemDescriptionCaptureDialog(Toplevel):
    """
    Edit properties of a graph item (node, edge, etc.)
    """

    def __init__(self, parent,  dictionary, properties, name, sourcefiletype=None):
        """

       :param parent: parent frame
       :param uiProfile:
       :param dictionary: items to inspect/edt
       :param properties: descriptionof items
       :param name: title of window
        """
        self.parent = parent
        self.cancelled = True
        self.argvalues = {}
        self.properties = properties
        self.sourcefiletype=sourcefiletype
        for prop_name in self.properties:
            if prop_name in dictionary:
                self.argvalues[prop_name] = dictionary[prop_name]

        Toplevel.__init__(self, parent)
        self.withdraw()  # remain invisible for now
        # If the master is not viewable, don't
        # make the child transient, or else it
        # would be opened withdrawn
        if parent.winfo_viewable():
            self.transient(parent)

        self.title(name)

        self.parent = parent

        self.result = None

        body = Frame(self)
        self.initial_focus = self.body(body)
        self.buttonbox()
        body.pack(padx=5, pady=5, fill=BOTH, expand=True)
        #body.pack_propagate(True)

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        if self.parent is not None:
            self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                      parent.winfo_rooty() + 50))

        self.deiconify()  # become visibile now

        self.initial_focus.focus_set()

        # wait for window to appear on screen before calling grab_set
        self.wait_visibility()
        self.grab_set()
        self.wait_window(self)

    def destroy(self):
        '''Destroy the window'''
        self.initial_focus = None
        Toplevel.destroy(self)

    def buildArgBox(self, master):

        disp_properties = [ProjectProperty(name=prop_name,
                                      description=prop_name,
                                      information=prop_def['description'],
                                      type=resolve_argument_type(prop_def['type'],self.sourcefiletype),
                                      values=prop_def['values'] if 'values' in prop_def else [],
                                      value=self.argvalues[prop_name] if prop_name in self.argvalues else None) \
                      for prop_name, prop_def in self.properties.iteritems()]
        argBox= PropertyFrame(master, disp_properties,
                                propertyFunction=NodePropertyFunction(self.argvalues),
                                changeParameterCB=self.changeParameter,
                                dir='.')
        argBox.pack(padx=5, pady=5, fill=BOTH, expand=True)


    def body(self, master):
        self.okButton = None
        Label(master, text='Parameters:', anchor=W, justify=LEFT).pack()
        self.buildArgBox(master)

    def buttonbox(self):
        box = Frame(self)
        self.okButton = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE,
                               state=ACTIVE)
        self.okButton.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Escape>", self.cancel)
        box.pack(side=BOTTOM)

    def ok(self, event=None):
        self.withdraw()
        self.update_idletasks()
        try:
            self.apply()
        finally:
            self.cancel()

    def changeParameter(self, name, type, value):
        self.argvalues[name] = value

    def cancel(self):
        if self.cancelled:
            self.argvalues = None
        # put focus back to the parent window
        if self.parent is not None:
            self.parent.focus_set()
        self.destroy()

    def apply(self):
        self.cancelled = False



class DescriptionViewDialog(tkSimpleDialog.Dialog):
    description = None
    metadiff = None
    metaBox = None


    def __init__(self, parent, scModel, name, description=None, metadiff=None):
        """

        :param parent:
        :param scModel:
        :param im:  end image
        :param name:
        :param description:
        :param metadiff:
        @type scModel: ImageProjectModel
        """
        self.dir = scModel.get_dir()
        self.parent = parent
        self.scModel = scModel
        self.description = description if description is not None else Modification('', '')
        self.metadiff = metadiff
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        vscrollbar = Scrollbar(master, orient=VERTICAL)
        Label(master, text="Operation:", anchor=W, justify=LEFT).grid(row=0, column=0, sticky=W)
        Label(master, text="Description:", anchor=W, justify=LEFT).grid(row=1, column=0, sticky=W)
        Label(master, text="Software:", anchor=W, justify=LEFT).grid(row=2, column=0, sticky=W)
        Label(master, text=getCategory(self.scModel.getGroupOperationLoader(),self.description), anchor=W, justify=LEFT).grid(row=0, column=1, sticky=W)
        Label(master, text=self.description.operationName, anchor=W, justify=LEFT).grid(row=0, column=2, sticky=W)
        Label(master, text=self.description.additionalInfo, anchor=W, justify=LEFT).grid(row=1, column=1, columnspan=3,
                                                                                         sticky=W)
        Label(master, text=self.description.getSoftwareName(), anchor=W, justify=LEFT).grid(row=2, column=1, sticky=W)
        Label(master, text=self.description.getSoftwareVersion(), anchor=W, justify=LEFT).grid(row=2, column=2,
                                                                                               sticky=W)
        Label(master, text='Automated: ' + self.description.automated, anchor=W, justify=LEFT).grid(row=3, column=0,
                                                                                                    sticky=W)
        Label(master, text='User: ' + self.description.username, anchor=W, justify=LEFT).grid(row=3, column=2,
                                                                                                    sticky=E)
        Message(master,
                text='Semantics: ' + ', '.join(self.description.getSemanticGroups()), anchor=W, justify=LEFT).grid(row=4,
                                                                                             column=0,
                                                                                              columnspan=4,
                                                                                              sticky=W)
        row = 5
        if len(self.description.arguments) > 0:
            Label(master, text='Parameters:', anchor=W, justify=LEFT).grid(row=row, column=0, columnspan=4, sticky=W)
            row += 1
            for argname, argvalue in self.description.arguments.iteritems():
                Label(master, text='      ' + argname + ': ' + str(argvalue), justify=LEFT).grid(row=row, column=0,
                                                                                                 columnspan=4, sticky=W)
                row += 1
        if self.description.inputMaskName is not None:
            self.inputmaskframe = ButtonFrame(master, self.description.inputMaskName, self.dir, \
                                              label='Mask (' + self.description.inputMaskName + '):', isMask=True,
                                              preserveSnapshot=True)
            self.inputmaskframe.grid(row=row, column=0, columnspan=4, sticky=E + W)
            row += 1
        if self.description.errors and len(self.description.errors) > 0:
            Label(master, text="Errors from mask processing :", anchor=W, justify=LEFT).grid(row=row, column=0,
                                                                                             columnspan=4, sticky=E + W)
            row += 1
            self.errorText = Text(master, height=10, width=40, font=('Times', '14'), relief=RAISED, borderwidth=2)
            self.errorText.grid(row=row, column=0, columnspan=4, sticky=E + W)
            row += 1
            for error in self.description.errors:
                self.errorText.insert(END, error)
            self.errorText.config(state=DISABLED)
        if self.metadiff is not None:
            sections = self.metadiff.getSections()
            Label(master, text=self.metadiff.getMetaType() + ' Changes:', anchor=W, justify=LEFT).grid(row=row,
                                                                                                       column=0,
                                                                                                       columnspan=2 if sections else 4,
                                                                                                       sticky=E + W)
            self.metaBox = MetaDiffTable(master, self.metadiff)
            if sections is not None:
                self.sectionBox = Spinbox(master, values=['Section ' + section for section in sections],
                                          command=self.changeSection)
                self.sectionBox.grid(row=row, column=1, columnspan=2, sticky=SE + NW)
            row += 1
            self.metaBox.grid(row=row, column=0, columnspan=4, sticky=E + W)
            row += 1
        if self.description.maskSet is not None:
            self.maskBox = MaskSetTable(master, self.description.maskSet, dir=self.dir)
            self.maskBox.grid(row=row, column=0, columnspan=4, sticky=SE + NW)
            row += 1

    def changeSection(self):
        self.metaBox.setSection(self.sectionBox.get()[8:])

    def cancel(self):
        tkSimpleDialog.Dialog.cancel(self)

    def buttonbox(self):
        box = Frame(self)
        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()


class ImageNodeCaptureDialog(tkSimpleDialog.Dialog):
    scModel = None
    selectedImage = None

    def __init__(self, parent, scModel):
        self.scModel = scModel
        tkSimpleDialog.Dialog.__init__(self, parent, "Select Node")

    def body(self, master):
        Label(master, text="Node Name:", anchor=W, justify=LEFT).grid(row=0, column=0, sticky=W)
        self.box = AutocompleteEntryInText(master, values=self.scModel.getNodeNames(), takefocus=True)
        self.box.grid(row=1, column=0,sticky=EW)
        self.name_var = StringVar('')
        self.node_name = Label(master, textvariable= self.name_var, anchor=W, justify=LEFT)
        self.node_name.grid(row=2, column=0, sticky=W)
        self.c = Canvas(master, width=500, height=500)
        self.photo = ImageTk.PhotoImage(ImageWrapper(np.zeros((500, 500,3))).toPIL())
        self.imc = self.c.create_image(250, 250, image=self.photo, tag='imgd')
        self.c.grid(row=3, column=0)
        self.box.bind("<Return>", self.newimage)
        self.box.bind("<<ComboboxSelected>>", self.newimage)

    def newimage(self, event):
        im = self.scModel.getImage(self.box.get())
        self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(im, (500, 500))).toPIL())
        self.c.itemconfig(self.imc, image=self.photo)
        self.name_var.set(self.scModel.getGraph().get_node(self.box.get())['file'])

    def cancel(self):
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.selectedImage = self.box.get()


class CompareDialog(tkSimpleDialog.Dialog):
    def __init__(self, parent, im, mask, name, analysis):
        self.im = im
        self.mask = mask
        self.analysis = analysis
        tkSimpleDialog.Dialog.__init__(self, parent, "Compare to " + name)

    def body(self, master):
        self.cim = Canvas(master, width=250, height=250)
        self.photoim = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(self.im, (250, 250), self.im.size)).toPIL())
        self.imc = self.cim.create_image(125, 125, image=self.photoim, tag='imgim')
        self.cim.grid(row=0, column=0)

        self.cmask = Canvas(master, width=250, height=250)
        self.photomask = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(self.mask, (250, 250), self.mask.size)).toPIL())
        self.maskc = self.cmask.create_image(125, 125, image=self.photomask, tag='imgmask')
        self.cmask.grid(row=0, column=1)

        iframe = Frame(master, bd=2, relief=SUNKEN)
        iframe.grid_rowconfigure(1, weight=1)
        Label(iframe, text='  '.join([key + ': ' + str(value) for key, value in self.analysis.items()]), anchor=W,
              justify=LEFT).grid(row=0, column=0, sticky=W)
        iframe.grid(row=1, column=0, columnspan=2, sticky=N + S + E + W)

    def buttonbox(self):
        box = Frame(self)
        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()


class VideoCompareDialog(tkSimpleDialog.Dialog):

    def __init__(self, parent, im, mask, name, analysis, dir):
        self.im = im
        self.dir = dir
        self.mask = mask
        self.analysis = analysis
        self.metaBox = None
        self.sectionBox = None
        tkSimpleDialog.Dialog.__init__(self, parent, "Compare to " + name)

    def body(self, master):
        row = 0
        meta_diff = self.analysis['metadatadiff']
        mask_set = self.analysis['videomasks']
        sections = meta_diff.getSections()
        Label(master, text=meta_diff.getMetaType() + ' Changes:', anchor=W, justify=LEFT).grid(row=row, column=0,
                                                                                              columnspan=2 if sections else 4,
                                                                                              sticky=E + W)
        self.metaBox = MetaDiffTable(master, meta_diff)
        if sections is not None:
            self.sectionBox = Spinbox(master, values=['Section ' + section for section in sections],
                                      command=self.changeSection)
            self.sectionBox.grid(row=row, column=1, columnspan=2, sticky=SE + NW)
        row += 1
        self.metaBox.grid(row=row, column=0, columnspan=4, sticky=E + W)
        row += 1
        if mask_set is not None:
            self.maskBox = MaskSetTable(master, mask_set, openColumn=3, dir=self.dir)
            self.maskBox.grid(row=row, column=0, columnspan=4, sticky=SE + NW)
        row += 1

    def changeSection(self):
        self.metaBox.setSection(self.sectionBox.get()[8:])

    def buttonbox(self):
        box = Frame(self)
        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()


class FilterCaptureDialog(tkSimpleDialog.Dialog):

    def __init__(self, parent, groupFilterLoader, scModel):
        im, filename = scModel.currentImage()
        self.gfl = groupFilterLoader
        self.pluginOps = self.gfl.getOperations(scModel.getStartType(),None)
        self.im = im
        self.c = None
        self.dir = scModel.get_dir()
        self.parent = parent
        self.scModel = scModel
        self.okButton = None
        self.photo= None
        self.argBox = None
        self.optocall = None
        self.cancelled = True
        self.arginfo = {}
        self.argvalues = {}
        self.softwareLoader = SoftwareLoader()
        self.sourcefiletype = scModel.getStartType()
        tkSimpleDialog.Dialog.__init__(self, parent, os.path.split(filename)[1])

    def body(self, master):
        top = Frame(master)
        bottom = Frame(master)
        self.argBoxMaster = bottom
        self.topBody(top)
        master.pack_propagate(True)
        top.pack_propagate(True)
        bottom.pack_propagate(True)
        top.pack(padx=5, pady=5)
        bottom.pack(padx=5, pady=5)

    def topBody(self,master):
        self.photo = ImageTk.PhotoImage(imageResize(self.im, (250, 250)).toPIL())
        self.c = Canvas(master, width=250, height=250)
        self.c.create_image(128, 128, image=self.photo, tag='imgd')
        self.c.grid(row=0, column=0, columnspan=2)
        self.e1 = AutocompleteEntryInText(master, values=sorted(self.pluginOps.keys(), key=lambda s: s.lower()), takefocus=True)
        self.e1.bind("<Return>", self.newop)
        self.e1.bind("<<ComboboxSelected>>", self.newop)
        row = 1
        labels = ['Plugin Name:', 'Category:', 'Operation:', 'Software Name:', 'Software Version:']
        for label in labels:
            Label(master, text=label, anchor=W, justify=LEFT).grid(row=row, column=0, sticky=W)
            row += 1
        self.catvar = StringVar()
        self.opvar = StringVar()
        self.e1.grid(row=1, column=1)
        row = 2
        variables = [self.catvar, self.opvar]
        for variable in variables:
            Label(master, textvariable=variable, anchor=W, justify=LEFT).grid(row=row, column=1, sticky=W)
            row += 1
        self.softwareselect = MyDropDown(master, sorted(self.softwareLoader.get_names(self.sourcefiletype), key=str.lower), command=self.newsoftware)
        self.versionselect = AutocompleteEntryInText(master, values=[], takefocus=False, width=40)
        self.softwareselect.bind("<Return>", self.newsoftware)
        self.softwareselect.bind("<<ComboboxSelected>>", self.newsoftware)
        self.softwareselect.grid(row=row, column=1, sticky=EW)
        self.softwareselect.set_completion_list(sorted(self.softwareLoader.get_names(self.sourcefiletype), key=str.lower),
                                    initialValue=self.softwareLoader.get_preferred_name())
        self.versionselect.set_completion_list(
            sorted(self.softwareLoader.get_versions(self.softwareLoader.get_preferred_name(),
                                                    software_type=self.sourcefiletype)),
            initialValue=self.softwareLoader.get_preferred_version(self.softwareLoader.get_preferred_name()))

        row += 1
        self.versionselect.grid(row=row, column=1)
        row +=1
        Label(master, text='Parameters:', anchor=W, justify=LEFT).grid(row=row, column=0, columnspan=2)

    def bottomBody(self, master):
        if len(self.pluginOps.keys()) > 0:
            self.newop(None)
        return

    def __getinfo(self,name):
        for k,v in self.arginfo.iteritems():
            if k == name:
                return v
        return None

    def __checkParams(self):
        ok = True
        if self.opvar.get() in [None,'']:
            return False
        for k, v in self.argvalues.iteritems():
            info = self.__getinfo(k)
            if info is None or 'type' not in info:
                continue
            cv, error = checkValue(k, info['type'], v)
            if v is not None and cv is None:
                ok = False
        ok &= checkMandatory(self.scModel.getGroupOperationLoader(),self.opvar.get(), self.sourcefiletype, self.sourcefiletype, self.argvalues)
        return ok

    def __buildTuple(self, argument, arginfo, operation):
        import copy
        argumentTuple = (argument, arginfo)
        argumentTuple = (argument, copy.copy(operation.mandatoryparameters[argument])) if operation is not None and \
                                                                               argument in operation.mandatoryparameters else argumentTuple
        argumentTuple = (argument, copy.copy(operation.optionalparameters[argument])) if operation is not None and \
                                                                              argument in operation.optionalparameters else argumentTuple
        if 'values' in arginfo:
            argumentTuple[1]['values'] = arginfo['values']
        if 'visible' in arginfo:
            argumentTuple[1]['visible'] = arginfo['visible']
        if 'description' not in argumentTuple[1]:
            argumentTuple[1]['description'] = 'Not Available'
        return argumentTuple

    def buildArgBox(self, operationName, arginfo):
        if self.argBox is not None:
            self.argBox.destroy()
        if arginfo is None:
            arginfo = {}
        operation = self.gfl.getOperation(operationName)
        argumentTuples = [self.__buildTuple(arg, arginfo[arg], operation) for arg in arginfo]
        for k, v in operation.mandatoryparameters.iteritems():
            if 'source' in v and v['source'] != self.sourcefiletype:
                continue
            if k in arginfo:
                continue
            argumentTuples.append((k, v))
        for k, v in operation.optionalparameters.iteritems():
            if 'source' in v and v['source'] != self.sourcefiletype:
                continue
            if k in arginfo:
                continue
            argumentTuples.append((k, v))
        for k,v in arginfo.iteritems():
            if 'defaultvalue' in v and v['defaultvalue'] is not None and \
                k not in self.argvalues:
                   self.argvalues[k] =  v['defaultvalue']

        properties = [ProjectProperty(name=argumentTuple[0],
                                      description=argumentTuple[0],
                                      information=argumentTuple[1]['description'],
                                      type=resolve_argument_type(argumentTuple[1]['type'],self.sourcefiletype),
                                      values=operation.getParameterValuesForType(argumentTuple[0], self.sourcefiletype),
                                      value=self.argvalues[argumentTuple[0]] if argumentTuple[
                                                                                    0] in self.argvalues else None) \
                      for argumentTuple in argumentTuples if 'visible' not in argumentTuple[1] or
                           argumentTuple[1]['visible']]
        self.argBox= PropertyFrame(self.argBoxMaster, properties,
                                propertyFunction=EdgePropertyFunction(properties,self.scModel),
                                changeParameterCB=self.changeParameter,
                                dir=self.dir)
        self.argBox.pack()
        self.arginfo = arginfo

    def buttonbox(self):
        box = Frame(self)
        self.okButton = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE,
                               state=ACTIVE if self.__checkParams() else DISABLED)
        self.okButton.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Escape>", self.cancel)
        box.pack(side=BOTTOM)

    def changeParameter(self, name, type, value):
        self.argvalues[name] = value
        if name == 'inputmaskname' and value is not None:
            self.inputMaskName = value
        if self.okButton is not None:
            self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)

    def newsoftware(self, event):
        sname = self.softwareselect.get()
        self.versionselect.set_completion_list(self.softwareLoader.get_versions(sname,software_type=self.sourcefiletype),
                                    initialValue=self.softwareLoader.get_preferred_version(name=sname))

    def newop(self, event):
        self.argvalues = {}
        if (self.pluginOps.has_key(self.e1.get())):
            self.optocall = self.e1.get()
            op = self.pluginOps[self.optocall]
            opinfo = op['operation']
            self.catvar.set(opinfo['category'])
            self.opvar.set(opinfo['name'])
            if 'software' in opinfo:
                self.softwareselect.set(opinfo['software'])
                self.softwareselect.configure(state='disabled')
            else:
                self.softwareselect.set(self.softwareLoader.get_preferred_name())
                self.softwareselect.configure(state='active')
            self.newsoftware(None)
            self.buildArgBox(opinfo['name'], opinfo['arguments'])
        else:
            self.catvar.set('')
            self.opvar.set('')
            self.softwareselect.set(self.softwareLoader.get_preferred_name())
            self.newsoftware(None)
            self.optocall = None
            self.buildArgBox(None, [])
        if self.okButton is not None:
            self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)

    def cancel(self):
        if self.cancelled:
            self.optocall = None
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.optocall = self.e1.get()
        self.softwaretouse = Software(self.softwareselect.get(), self.versionselect.get())
        if self.softwareLoader.add(self.softwaretouse ):
            self.softwareLoader.save()

class FilterGroupCaptureDialog(tkSimpleDialog.Dialog):
    gfl = None
    im = None
    grouptocall = None
    cancelled = True

    def __init__(self, parent, im, name):
        self.im = im
        self.parent = parent
        self.gfl = GroupFilterLoader()
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        self.photo = ImageTk.PhotoImage(imageResize(self.im, (250, 250)).toPIL())
        self.c = Canvas(master, width=250, height=250)
        self.c.create_image(128, 128, image=self.photo, tag='imgd')
        self.c.grid(row=0, column=0, columnspan=2)
        Label(master, text="Group Name:", anchor=W, justify=LEFT).grid(row=1, column=0, sticky=W)
        self.e1 = AutocompleteEntryInText(master, values=self.gfl.getGroupNames(), takefocus=True)
        self.e1.grid(row=1, column=1)

    def cancel(self):
        if self.cancelled:
            self.grouptocall = None
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.grouptocall = self.e1.get()

    def getGroup(self):
        return self.grouptocall

class URLCaptureDialog(tkSimpleDialog.Dialog):


    def __init__(self, parent, urls):
        self.urls = [x for x in urls if len(x) > 0]
        tkSimpleDialog.Dialog.__init__(self, parent, "Select URLs")

    def body(self, master):
        yscrollbar = Scrollbar(master, orient=VERTICAL)
        xscrollbar = Scrollbar(master, orient=HORIZONTAL)
        self.listbox = Listbox(master, width=80,
                               yscrollcommand=yscrollbar.set,
                               xscrollcommand=xscrollbar.set)
        self.listbox.bind("<Double-Button-1>", self.remove)
        self.listbox.grid(row=0, column=0, sticky=E + W + N + S,
                               columnspan=3)
        xscrollbar.config(command=self.listbox.xview)
        xscrollbar.grid(row=1, column=0, stick=E + W,columnspan=3)
        yscrollbar.config(command=self.listbox.yview)
        yscrollbar.grid(row=0, column=2, stick=N + S)
        for item in self.urls:
            self.listbox.insert(END, item)
        Label(master, text="Add Entry:", anchor=W, justify=LEFT).grid(row=2, column=0, sticky=W)
        self.url = Text(master, takefocus=True, width=60, height=1, relief=RAISED,
                      borderwidth=2)
        self.url.grid(row=2, column=1,sticky=EW)
        self.url_submit = Button(master, text="Add", command=lambda: self.add(None))
        self.url_submit.grid(row=2, column=2, sticky=W)
        #self.url.bind("<Return>", self.add)

    def buttonbox(self):
        '''add standard button box.

        override if you do not want the standard buttons
        '''

        box = Frame(self)

        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Escape>", self.cancel)
        self.bind("<Return>", self.add)
        box.pack()

    def cancel(self):
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        # if len(self.listbox.get(0, END)):

        self.urls = self.listbox.get(0, END)

    def remove(self,event):
        self.listbox.delete(self.listbox.curselection()[0],self.listbox.curselection()[0])

    def add(self,event):
        import urllib2
        contents = self.url.get(1.0, END).strip()
        if not contents.startswith('http'):
            contents = 'http://' + contents
        if len(contents) == 0:
            return
        try:
            f = urllib2.urlopen(contents,timeout=2)
            self.listbox.insert(END, contents)
            f.close()
        except Exception as e:
            pass
        self.url.delete(1.0,END)


class ActionableTableCanvas(TableCanvas):
    def __init__(self, parent=None, model=None, width=None, height=None, allowSave=False,openers=None, **kwargs):
        self.allowSave = True
        self.openers=openers
        TableCanvas.__init__(self, parent=parent, model=model, width=width, height=height, **kwargs)

    def handle_double_click(self, event):
        row = self.get_row_clicked(event)
        self.openFile(row)

    def openFile(self, row):
        #model = self.getModel()
        #TODO: Sorting?
        if self.openers is not None:
            self.openers[row]()

    def saveAll(self):
        self.model.saveAll()

    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        defaultactions = {"Set Fill Color": lambda: self.setcellColor(rows, cols, key='bg'),
                          "Set Text Color": lambda: self.setcellColor(rows, cols, key='fg'),
                          "Open": lambda: self.openFile(row),
                          "Copy": lambda: self.copyCell(rows, cols),
                          "Save": self.saveAll,
                          "View Record": lambda: self.getRecordInfo(row),
                          "Select All": self.select_All,
                          "Filter Records": self.showFilteringBar,
                          "Export csv": self.exportTable,
                          "Plot Selected": self.plotSelected,
                          "Plot Options": self.plotSetup,
                          "Export Table": self.exportTable,
                          "Preferences": self.showtablePrefs,
                          "Formulae->Value": lambda: self.convertFormulae(rows, cols)}

        if self.openers is not None:
            main = ["Open", "Set Fill Color", "Set Text Color", "Copy"]
        else:
            main = ["Set Fill Color", "Set Text Color", "Copy"]
        general = ["Select All", "Filter Records", "Preferences"]
        filecommands = ['Export csv','Save'] if self.allowSave else ['Export csv']
        plotcommands = ['Plot Selected', 'Plot Options']
        utilcommands = ["View Record", "Formulae->Value"]

        def createSubMenu(parent, label, commands):
            menu = Menu(parent, tearoff=0)
            popupmenu.add_cascade(label=label, menu=menu)
            for action in commands:
                menu.add_command(label=action, command=defaultactions[action])
            return menu

        def add_commands(fieldtype):
            """Add commands to popup menu for column type and specific cell"""
            functions = self.columnactions[fieldtype]
            for f in functions.keys():
                func = getattr(self, functions[f])
                popupmenu.add_command(label=f, command=lambda: func(row, col))
            return

        popupmenu = Menu(self, tearoff=0)

        def popupFocusOut(event):
            popupmenu.unpost()

        if outside == None:
            # if outside table, just show general items
            row = self.get_row_clicked(event)
            col = self.get_col_clicked(event)
            coltype = self.model.getColumnType(col)

            def add_defaultcommands():
                """now add general actions for all cells"""
                for action in main:
                    popupmenu.add_command(label=action, command=defaultactions[action])
                return

            #            if self.columnactions.has_key(coltype):
            #                add_commands(coltype)
            add_defaultcommands()

        for action in general:
            popupmenu.add_command(label=action, command=defaultactions[action])

        popupmenu.add_separator()
        createSubMenu(popupmenu, 'File', filecommands)
        createSubMenu(popupmenu, 'Plot', plotcommands)
        if outside == None:
            createSubMenu(popupmenu, 'Utils', utilcommands)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        return popupmenu


def toNumString(v):
    num = 0
    val = v
    if len(v) > 0 and '0123456789'.find(v[0]) > 0:
        pos = v.find(':')
        if pos < 0:
            pos = len(v)
        try:
            num = float(v[0:pos])
            if pos < len(v):
                val = v[pos+1:]
            else:
                val = ''
        except:
            num = 0
    return num,val

def compareNumString(numstringa,numstringb):
    diff = numstringa[0] - numstringb[0]
    if abs(diff) < 0.00000001:
        return -1 if numstringa[1] < numstringb[1] else (0 if numstringa[1] == numstringb[1] else 1)
    return int(np.sign(diff))

def sortMask(a,b):
    return compareNumString(toNumString(a),toNumString(b))

class ExtendedTableModel(TableModel):

    def __init__(self, datasource):
        TableModel.__init__(self)
        self.changes = {}
        self.datasource = datasource

    def setValueAt(self, value, rowIndex, columnIndex):
        TableModel.setValueAt(self,value,rowIndex,columnIndex)
        if rowIndex not in self.changes:
            self.changes[rowIndex] = {}
        self.changes[rowIndex][columnIndex] = value

    def saveAll(self):
        for row in self.changes:
            for col in self.changes[row]:
                self.datasource.update(row,col, self.changes[row][col])

class MaskSetTable(Frame):
    section = None

    def __init__(self, master, items, dir='.', **kwargs):
        self.items = items
        bh = kwargs.pop('boxheight') if 'boxheight' in kwargs else 125
        bw = kwargs.pop('boxwidth') if 'boxwidth' in kwargs else None
        Frame.__init__(self, master, **kwargs)
        self._drawMe(dir, bw,bh)

    def _drawMe(self, dir, boxWidth=140, boxHeight=125):
        from functools import partial
        openers= []
        model = ExtendedTableModel( self.items)
        for c in self.items.columnNames:
            model.addColumn(c)
        model.importDict(self.items.columnValues)
        model.reclist = sorted(model.reclist)

        def _get_segment(start,file):
            for segment in self.items.maskset:
                if get_start_time_from_segment(segment) == start and \
                    get_file_from_segment(segment) == file:
                    return segment
        def _open_mask(filename, preferences=None,start_frame=None,start_time=0, end_frame=None):
            vid = convertToVideo(filename,preferences=preferences,start_frame=start_frame,start_time=start_time)
            openFile(vid)
        def _log():
            logging.getLogger('maskgen').warn('Empty Segment')
        for recid in model.reclist:
            rec = model.data[recid]
            segment = _get_segment(rec['Start'],rec['File'])
            if segment is not None and get_file_from_segment(segment) is not None:
                opener = partial(_open_mask,
                                 os.path.join(dir,get_file_from_segment(segment)),
                                 preferences=MaskGenLoader(),
                                 start_frame=get_start_frame_from_segment(segment),
                                 start_time=get_start_time_from_segment(segment),
                                 end_frame=get_end_frame_from_segment(segment))
                openers.append(opener)
            else:
                openers.append(_log)

        self.table = ActionableTableCanvas(self, model=model, rowheaderwidth=140, showkeynamesinheader=True,
                                           height=boxHeight, width=boxWidth,
                                           allowSave=True, openers=openers)
        self.table.updateModel(model)
        self.table.createTableFrame()


class MetaDiffTable(Frame):
    section = None

    def __init__(self, master, items, section=None, **kwargs):
        self.items = items
        self.section = section
        Frame.__init__(self, master, **kwargs)
        self._drawMe()

    def setSection(self, section):
        if section == self.section:
            return
        self.section = section
        self.table.getModel().setupModel(self.items.toColumns(section))
        self.table.getModel().reclist = sorted(self.table.getModel().reclist,cmp=sortMask)
        self.table.redrawTable()

    def _drawMe(self):
        model = TableModel()
        for c in self.items.getColumnNames(self.section):
            model.addColumn(c)
        model.importDict(self.items.toColumns(self.section))
        model.reclist = sorted(model.reclist,cmp=sortMask)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.table = ActionableTableCanvas(self, model=model, rowheaderwidth=140, showkeynamesinheader=True, height=125, allowSave=True)
        self.table.updateModel(model)
        self.table.createTableFrame()


class CompositeCaptureDialog(tkSimpleDialog.Dialog):
    im = None
    cancelled = True
    modification = None
    start_type = None
    end_type = None
    selectMasks = None


    def __init__(self, parent,   scModel ):
        """
        :param parent:
        :param scModel:
        @type scModel : ImageProjectModel
        """
        self.dir = scModel.get_dir()
        self.start_type = scModel.getStartType()
        self.end_type = scModel.getEndType()
        self.parent = parent
        self.scModel = scModel
        name = scModel.start + ' to ' + scModel.end
        self.modification = scModel.getDescription()
        self.selectMasks = self.scModel.getSelectMasks()
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def load_overlay(self, event, initialize=False, master=None):
        import logging
        option = self.item.get()
        if option in self.selectMasks.keys():
            finalNode = option
        else:
            finalNode = self.selectMasks.keys()[0]
        value = os.path.split(self.selectMasks[finalNode][0])[1] if self.selectMasks[finalNode] is not None else ''
        self.filename.set(value)
        finalImage = self.scModel.getImageAndName(finalNode)[0]
        imTuple  = self.selectMasks[finalNode]
        color = [0,198,0]
        if imTuple is None:
            red = openImage(get_icon('RedX.png')).to_mask()
            color = [198,0,0]
            im = red.resize(finalImage.size,1)
        else:
            im = imTuple[1]
            im = im.to_mask().invert()
        imResized = imageResizeRelative(im, (250, 250), im.size)
        finalResized = imageResizeRelative(finalImage, (250, 250), finalImage.size)
        try:
            finalResized = finalResized.overlay(imResized,color=color)
        except Exception as ex:
            logging.getLogger('maskgen').error("Improper size mask" + ex.message)
        self.photo = ImageTk.PhotoImage(finalResized.toPIL())
        if initialize:
            self.c = Canvas(master, width=260, height=260)
            self.image_on_canvas = self.c.create_image(0, 0, image=self.photo, anchor=NW)
        else:
            self.c.itemconfig(self.image_on_canvas, image=self.photo)

    def body(self, master):
        self.item = StringVar()
        row = 0
        if len(self.selectMasks.keys()) > 0:
            self.item.set(self.selectMasks.keys()[0] if len(self.selectMasks.keys()) > 0 else '')
            self.filename = StringVar()
            self.load_overlay(None, initialize=True, master=master)
            self.c.grid(row=row, column=0, columnspan=2)
            row += 1
            self.label = Label(master, textvariable=self.filename, justify=LEFT)
            self.label.grid(row=row, column=0, columnspan=2,sticky='EW',padx=10)
            row += 1
            self.optionsBox = ttk.Combobox(master,
                                       values=list(self.selectMasks.keys()),
                                       textvariable=self.item)
            row += 1
            self.optionsBox.grid(row=row, column=0, columnspan=2, sticky='EW')
            self.optionsBox.bind("<<ComboboxSelected>>", self.load_overlay)
            row += 1
            self.bc = Button(master, text="Change Mask", command=self.changemask, relief=FLAT)
            self.bc.grid(row=row, column=0)
            self.bd = Button(master, text="Delete Mask", command=self.deletemask, relief=FLAT)
            self.bd.grid(row=row, column=1)
            row += 1
        self.includeInMaskVar = StringVar()
        op = getOperation(self.modification.operationName)
        self.includeInMaskVar.set(self.modification.recordMaskInComposite)
        if  self.modification.category not in ['Output','AntiForensic','Laundering']  or \
            op is not None and getValue(op.includeInMask, self.start_type, getValue(op.includeInMask,'default',False)):
            self.cbIncludeInComposite = Checkbutton(master, text="Included in Composite", variable=self.includeInMaskVar, \
                                                    onvalue="yes", offvalue="no")
            self.cbIncludeInComposite.grid(row=row, column=0, columnspan=2, sticky=W)
            return self.cbIncludeInComposite
        else:
            return None

    def deletemask(self):
        self.selectMasks[self.optionsBox.get()] = None
        self.load_overlay(None)

    def changemask(self):
        val = tkFileDialog.askopenfilename(initialdir=self.dir, title="Select Input Mask",
                                           filetypes=getMaskFileTypes())
        if (val != None and len(val) > 0):
            self.selectMasks[self.optionsBox.get()]  = (val,openImage(val, isMask=True, preserveSnapshot=os.path.split(os.path.abspath(val))[0] == dir))
            self.load_overlay(None)

    def cancel(self):
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.modification.setRecordMaskInComposite(self.includeInMaskVar.get())

class SubstituteMaskCaptureDialog(tkSimpleDialog.Dialog):
    cancelled = True

    def __init__(self, parent, scModel ):
        """
        :param parent:
        :param scModel:
        @type scModel : ImageProjectModel
        """
        self.parent = parent
        self.scModel = scModel
        name = scModel.start + ' to ' + scModel.end
        self.use_as_substitute = StringVar()
        self.use_as_substitute.set('yes' if self.scModel.hasSubstituteMasks() else 'no')
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        row=0
        self.ChkButton = Checkbutton(master, text="Use inputmask as substitute", variable=self.use_as_substitute, \
                                                onvalue="yes", offvalue="no")
        self.ChkButton.grid(row=row, column=0, columnspan=2, sticky=W)
        return self.ChkButton

    def cancel(self):
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False



class FileCaptureDialog(tkSimpleDialog.Dialog):

    def __init__(self, parent, name, dir, current_file=None):
        """
        :param parent:
        :param scModel:
        @type scModel : ImageProjectModel
        """
        self.dir = dir
        self.cancelled = True
        self.current_file = os.path.basename(current_file) if current_file is not None else None
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        self.item = StringVar()
        self.item.set(self.current_file if self.current_file is not None else '')
        label1 = Label(master, text='File', justify=LEFT)
        label1.grid(row=0, column=0, columnspan=1, sticky='EW', padx=10)
        label2 = Label(master, textvariable=self.item, justify=LEFT)
        label2.grid(row=0, column=1, columnspan=2, sticky='EW', padx=10)
        self.bc = Button(master, text="Change File", command=self.changefile, relief=RAISED)
        self.bc.grid(row=1, column=0,sticky='EW', padx=10)
        self.bd = Button(master, text="Forget File", command=self.forgetfile, relief=RAISED)
        self.bd.grid(row=1, column=1,sticky='EW', padx=10)

    def forgetfile(self):
        self.item.set('')
        self.current_file = None

    def changefile(self):
        val = tkFileDialog.askopenfilename(initialdir=self.dir, title="Select File",
                                           filetypes=getMaskFileTypes())
        #suffixes = [type_tuple[1][1:] for type_tuple in getMaskFileTypes()]
        if (val != None and len(val) > 0):
            #if os.path.splitext(val)[1] not in suffixes:
            #    return
            self.current_file = os.path.basename(val)
            self.item.set(self.current_file )

    def cancel(self):
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False

class PointsViewDialog(tkSimpleDialog.Dialog):
    """
    View mapping bounding boxes between to images.
    The second image's bounding box can be rotated to align with the first
    """
    cancelled= True
    angle = 0
    level = IntObject()
    colorMap = dict()
    ws = None

    def __init__(self, parent, start_box, end_box, angle, start_im, end_im,model,op=None,argument_name=None):
        """
        :param parent: MakeGenUI
        @type parent: MakeGenUI
        """
        self.parent = parent
        self.startIM = start_im
        self.nextIM = end_im
        self.left_box  = start_box
        self.right_box = end_box
        self.angle = angle
        self.scModel = model
        self.op = op
        self.extender = CompositeExtender(scModel=self.scModel)
        self.argument_name = argument_name
        tkSimpleDialog.Dialog.__init__(self, parent)

    def notify(self,event):
        if self.nb.tab(event.widget.select(), "text") == 'Composite':
            self.composite_view.update(self._newComposite())

    def getStringConfiguration(self):
        return str(self.left_box) + ':' + str(self.right_box) + ':' + str(self.angle)

    def _newComposite(self):
        override_args={
            'op' : self.op,
            'shape change': str((int(self.nextIM.size[1]-self.startIM.size[1]),
                             int(self.nextIM.size[0]-self.startIM.size[0]))).replace('L','')
        }
        if self.argument_name is not None and self.ws is not None:
            self.updateBox()
            override_args['arguments'] = {self.argument_name : self.getStringConfiguration()}

        return self.extender.get_image(override_args,target_size=self.nextIM.size)

    def instructionsFrame(self,master):
        f = Frame(master)
        w1 = Label(f, text="The left image is the image prior to recapture. " + \
                           "The right image is the recaptured image. " + \
                           "The idea is to draw rectangles around the corresponding areas in each. " + \
                           "If a portion of the left image is recaptured, cropping parts of the image, " + \
                           "then draw a rectangle around the portion of the left image that is " + \
                           "captured in the right image. If the recapture image is framed " + \
                           "containing 100% of the left image with additional framing (background), " + \
                           "draw a rectange around the portion of the right image that represents 100% of the " + \
                           "left image.  The rectangle can be adjusted by clicking and dragging the corners."
                   , font=("Helvetica", 14), wraplength=400, justify=LEFT)
        w1.grid(row=0)
        w2 = Label(f, text="Once the rectangles are complete, rotate the right rectangle to indicate the amount of rotation applied to " + \
                           "the image, if any.  In most cases, the amount of rotation is -90,0,90 or 180.",
                   font=("Helvetica", 14), wraplength=400, justify=LEFT)
        w2.grid(row=1)
        w3 = Label(f, text=
        "The composite image tab is for review only.  The refresh button reapplies the changes to the composite, as does " + \
        "switching between the composite tab and the other tabs. The scale is only for aiding the edit process; it is " + \
        "not applied to the final images.",
                   font=("Helvetica", 14), wraplength=400, justify=LEFT)
        w3.grid(row=2)
        return f

    def body(self,master):
        self.nb = ttk.Notebook(master)
        self.left = PictureEditor(master,self.startIM.toPIL(), self.left_box)
        f = self.instructionsFrame(self.nb)

        self.right = PictureEditor(self.nb, self.nextIM.toPIL(),self.right_box,angle=self.angle)
        self.composite_view = ScrollCompositeViewer(self.nb, self.nextIM, self._newComposite())
        self.nb.add(self.right, text='Image')
        self.nb.add(self.composite_view, text='Composite')
        self.nb.add(f, text='Instructions')
        self.nb.select(self.right)
        self.nb.bind('<<NotebookTabChanged>>', self.notify)

        self.left.grid(row=0, column=0, columnspan=2)
        self.nb.grid(row=0, column=2,columnspan=2)

        label1 = Label(master,text='Scale:', justify=RIGHT,anchor=S)
        label1.grid(row=1, column=0,sticky=E)
        self.ls = Scale(master, from_=15, to=100, orient=HORIZONTAL, command=self.rescale)
        self.ls.grid(row=1, column=1,sticky=W)
        self.ls.set(100)
        label2 = Label(master, text='Rotation:', justify=RIGHT,anchor=S)
        label2.grid(row=1, column=2,sticky=E)
        self.ws = Scale(master, from_=-180, to=180,length=360,resolution=1,orient=HORIZONTAL,command=self.rotate)
        self.ws.grid(row=1,column=3,sticky=W)
        self.ws.set(self.angle)

    def rescale(self,event):
        self.right.set_scale(float(self.ls.get())/100.0)
        self.left.set_scale(float(self.ls.get()) / 100.0)
        self.composite_view.set_scale(float(self.ls.get()) / 100.0)

    def rotate(self,event):
        self.right.rotate(self.ws.get())

    def cancel(self):
        tkSimpleDialog.Dialog.cancel(self)

    def refresh_composite(self):
        self.composite_view.update(self._newComposite())

    def updateBox(self):
        if self.ws is not None:
            self.angle = self.ws.get()
            self.left_box = (min(self.left.box[0], self.left.box[2]),
                             min(self.left.box[1], self.left.box[3]),
                             max(self.left.box[0], self.left.box[2]),
                             max(self.left.box[1], self.left.box[3]))
            self.right_box = (min(self.right.box[0], self.right.box[2]),
                              min(self.right.box[1], self.right.box[3]),
                              max(self.right.box[0], self.right.box[2]),
                              max(self.right.box[1], self.right.box[3]))

    def apply(self):
        self.cancelled = False
        self.updateBox()

    def buttonbox(self):
        box = Frame(self)

        w = Button(box, text="OK", width=10, command=self.ok)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=15, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Refresh Composite", width=15, command=self.refresh_composite)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()


class CommentViewer(tkSimpleDialog.Dialog):
    def __init__(self, master):
        self.master=master
        tkSimpleDialog.Dialog.__init__(self, master)

    def body(self, master):
        try:
            comment = self.master.scModel.getProjectData('qacomment')
            if comment == '':
                raise ValueError('comments missing')
        except ValueError:
            comment = 'There are no comments!'

        self.commentLabel = Label(self, text=comment, wraplength=400, justify=LEFT)
        self.commentLabel.pack(side=TOP)

    def buttonbox(self):
        box = Frame(self)

        w = Button(box, text="Clear Comment", width=15, command=self.clearComment, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="OK", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def clearComment(self):
        self.master.scModel.setProjectData('qacomment', '',excludeUpdate=True)
        self.commentLabel.config(text='There are no comments!')


class ButtonFrame(Frame):
    def __init__(self, master, fileName, dir, label=None, isMask=False, preserveSnapshot=False, **kwargs):
        Frame.__init__(self, master, **kwargs)
        self.fileName = fileName
        self.dir = dir
        Label(self, text=label if label else fileName, anchor=W, justify=LEFT).grid(row=0, column=0, sticky=W)
        img = openImage(os.path.join(dir, fileName), isMask=isMask, preserveSnapshot=preserveSnapshot)
        self.img = ImageTk.PhotoImage(fixTransparency(imageResizeRelative(img, (125, 125), img.size)).toPIL())
        w = Button(self, text=fileName, width=10, command=self.openMask, default=ACTIVE, image=self.img)
        w.grid(row=1, sticky=E + W)

    def openMask(self):
        openFile(os.path.join(self.dir, self.fileName))



def createCompareDialog(master, im2, mask, nodeId, analysis, dir, linktype):
    if linktype == 'image.image':
        return CompareDialog(master, im2, mask, nodeId, analysis)
    elif linktype == 'video.video':
        return VideoCompareDialog(master, im2, mask, nodeId, analysis, dir)


class RotateDialog(tkSimpleDialog.Dialog):
    parent = None
    cancelled = True
    rotate = 'no'

    def __init__(self, parent, donor_im, rotated_im, orientation):
        self.parent = parent
        self.donor_im = donor_im
        self.rotated_im = rotated_im
        self.orientation = orientation
        tkSimpleDialog.Dialog.__init__(self, parent, "Image Orientation: " + self.orientation)

    def body(self, master):
        row = 0
        Label(master, text="Base").grid(row=row, column=0, sticky=W + S + N)
        Label(master, text="Final w/rotation").grid(row=row, column=1, sticky=E + S + N)
        row = 1
        self.donor_photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.donor_im, (250, 250))).toPIL())
        self.donor_canvas = Canvas(master, width=125, height=125)
        self.donor_canvas.create_image(125, 125, image=self.donor_photo, tag='imgd')
        self.donor_canvas.grid(row=row, column=0, sticky=W + N)
        self.rotated_photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.rotated_im, (250, 250))).toPIL())
        self.rotated_canvas = Canvas(master, width=125, height=125)
        self.rotated_canvas.create_image(125, 125, image=self.rotated_photo, tag='imgr')
        self.rotated_canvas.grid(row=row, column=1, sticky=E + N)
        row = 2
        Label(master, text="Do you wish to counter rotate image").grid(row=row, column=0, sticky=E + W, columnspan=2)
        row = 3
        Label(master, text="to align with the orientation?").grid(row=row, column=0, sticky=E + W, columnspan=2)
        self.buttonboxgrid(master, row + 1)

    def buttonbox(self):
        return

    def buttonboxgrid(self, box, row):
        #        box = Frame(self)
        okButton = Button(box, text="Yes", width=10, command=self.ok, default=ACTIVE)
        okButton.grid(row=row, column=0)
        noButton = Button(box, text="No", width=10, command=self.cancel)
        noButton.grid(row=row, column=1)
        self.bind("<Escape>", self.cancel)
        # box.pack()

    def cancel(self):
        if self.cancelled:
            self.rotate = 'no'
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.rotate = 'yes'


class VerticalScrolledFrame(Frame):
    """
    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    """

    def __init__(self, parent, horizontal=False, **kw):
        Frame.__init__(self,parent, **kw)
        self.parent = parent
        # create a canvas object and a vertical scrollbar for scrolling it
        self.canvas = canvas = Canvas(self, bd=0, highlightthickness=0)
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        if horizontal:
            hscrollbar = Scrollbar(self, orient=HORIZONTAL)
            hscrollbar.pack(fill=X, side=BOTTOM, expand=FALSE)
            canvas = Canvas(self, bd=0, highlightthickness=0,
                            yscrollcommand=vscrollbar.set,
                            xscrollcommand=hscrollbar.set)
            hscrollbar.config(command=canvas.xview)
        else:
            canvas = Canvas(self, bd=0, highlightthickness=0,
                            yscrollcommand=vscrollbar.set)
        #canvas.configure(yscrollcommand=vscrollbar.set)
        vscrollbar.config(command=canvas.yview)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)
        self._canvas = canvas

        #create a frame inside the canvas which will be scrolled with it
        self.interior = Frame(canvas)
        self.interior_id = canvas.create_window(0, 0, window=self.interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (self.interior.winfo_reqwidth(), self.interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if self.interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=self.interior.winfo_reqwidth())
            screen_h = self.winfo_screenheight()
            if ((self.parent.winfo_rooty() + self.parent.winfo_height() - self.canvas.winfo_height() + self.interior.winfo_reqheight()) < screen_h):
                self.canvas.configure(height=self.interior.winfo_reqheight())

        self.interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(self.interior_id, width=canvas.winfo_width())
            elif self.interior.winfo_reqwidth() != self.canvas.winfo_width():
                self.canvas.config(width=self.interior.winfo_reqwidth())
            if (self.interior.winfo_reqheight() != self.canvas.winfo_height()) or (
                self.interior.winfo_height() != self.canvas.winfo_height()):
                self.canvas.itemconfigure(self.interior_id, height=self.canvas.winfo_height())

        if not horizontal:
            canvas.bind('<Configure>', _configure_canvas)

        return

    def resize_canvas(self, height = 400, width = 400):
        """
        Function for the user to resize the internal Canvas widget if desired
        :param height: new height in pixels
        :param width: new width in pixels
        :return:
        """
        self._canvas.configure(width=width, height=height)


def notifyCB(obj,name, type, row, cb,a1,a2,a3):
    if cb is not None:
        cb(name, type, obj.values[row].get())

class PropertyFrame(VerticalScrolledFrame):

   parent = None
   cancelled = True
   dir = '.'
   buttons = {}
   propertyFunction = PropertyFunction()
   extra_args = {}
   """
   @type scModel: ImageProjectModel
   """

   def __init__(self, parent, properties, propertyFunction=PropertyFunction(),
                dir='.',
                changeParameterCB=None,
                extra_args ={},
                **kwargs):
     self.parent = parent
     self.properties = [prop for prop in properties if not prop.node and not prop.semanticgroup]
     self.values =   [None for prop in properties]
     self.widgets =[None for prop in properties]
     self.changeParameterCB = changeParameterCB
     self.dir = dir
     self.propertyFunction = propertyFunction
     self.extra_args = extra_args
     VerticalScrolledFrame.__init__(self, parent, **kwargs)
     self.body()

   def body(self):
       master = self.interior
       row = 0
       for prop in self.properties:
           self.values[row] = StringVar()
           partialCB = partial(notifyCB,self, prop.name, prop.type, row,self.changeParameterCB)
           self.values[row].trace("w", partialCB)
           p = partial(viewInfo, (prop.description, prop.information))
           Button(master, text=prop.description, takefocus=False, command=p).grid(row=row, sticky=E)
           v = self.propertyFunction.getValue(prop.name)
           if v is not None:
               self.values[row].set(v)
           if prop.type == 'list':
               if prop.readonly:
                  if v is not None and type(v) != list:
                     v = [v]
                  widget = Message(master, text=', '.join(v if v is not None else ''))#,width=80)
                  widget.grid(row=row, column=1, columnspan=2, sticky=E + W)
               else:
                  widget =  ttk.Combobox(master, values=prop.values, takefocus=(row == 0),textvariable=self.values[row], state='readonly')
                  widget.grid(row=row, column=1, columnspan=2, sticky=E + W)
           elif prop.type == 'text':
               widget = Text(master, takefocus=(row == 0), width=60, height=3, relief=RAISED,
                                       borderwidth=2)
               partialf = partial(fillTextVariable, self, row)
               widget.bind("<KeyRelease>", partialf)
               widget.bind("<KeyPress>", partialf)
               if v:
                   widget.insert(1.0, v)
               widget.grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type == 'urls':
               partialf = partial(promptForURLAndFillButtonText, self, prop.name, row)
               v_temp = v if v is not None else '               '
               items  = [re.sub('^http[s]*://','',item) for item in v_temp.split('\n')]
               self.buttons[prop.name] = widget = Button(master, text= ' '.join(items),
                                                         takefocus=False,
                                                        # width=max([len(i) for i in items]),
                                                         height =(1 if v is None else v.count('\n')+1),
                                                         anchor=W, justify=LEFT, padx=2,
                                                         command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type == 'yesno':
               widget = [None,None]
               widget[0]  =Radiobutton(master, text='Yes', takefocus=(row == 0), variable=self.values[row],
                               value='yes')
               widget[0].grid(row=row, column=1, sticky=W)
               #widget[0].deselect()
               widget[1] =  Radiobutton(master, text='No', takefocus=(row == 0), variable=self.values[row], value='no')
               widget[1].grid(row=row, column=2, sticky=E)
               #widget[1].select()
           elif prop.type == 'file:image':
               partialf = partial(promptForFileAndFillButtonText, self, self.dir, prop.name, row, getImageFileTypes())
               self.buttons[prop.name] = widget = Button(master, text=v if v is not None else '              ', takefocus=False,
                                                command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type == 'file:video':
               partialf = partial(promptForFileAndFillButtonText, self, self.dir, prop.name, row, videofiletypes)
               self.buttons[prop.name] = widget = Button(master, text=v if v is not None else '              ',
                                                         takefocus=False,
                                                         command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type.startswith('file:'):
               typematch = '*.' + prop.type[prop.type.find(':')+1:]
               typename =  prop.type[prop.type.find(':') + 1:].upper()
               partialf = partial(promptForFileAndFillButtonText, self, self.dir, prop.name, row, [(typename, typematch)])
               self.buttons[prop.name] = widget = Button(master, text=v if v is not None else '               ', takefocus=False,
                                                command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type.startswith('fileset:'):
               initialdir_parts = tuple(prop.type[8:].split('/'))
               initialdir = os.path.join(*tuple(initialdir_parts))
               partialf = partial(promptForFileAndFillButtonText, self, initialdir, prop.name, row, [('Text', '*.txt'), ('All Files', '*')])
               self.buttons[prop.name] = widget = Button(master, text=v if v is not None else '               ', takefocus=False,
                                                command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type.startswith('folder:'):
               initialdir_parts = tuple(prop.type[7:].split('/'))
               initialdir = os.path.join(*tuple(initialdir_parts))
               partialf = partial(promptForFolderAndFillButtonText, self, initialdir, prop.name, row)
               self.buttons[prop.name] = widget = Button(master, text=v if v is not None else '               ',
                                                         takefocus=False,
                                                         command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type.startswith('donor'):
               partialf = partial(promptForDonorandFillButtonText, self, prop.name, row)
               self.buttons[prop.name] =  widget = Button(master, text=v if v is not None else '', takefocus=False,
                                                command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type.startswith('float'):
               widget = Entry(master, takefocus=(row == 0), width=80,textvariable=self.values[row])
               widget.grid(row=row, column=1, columnspan=12, sticky=E + W)
               v = prop.type
           elif prop.type.startswith('int'):
               widget = Entry(master, takefocus=(row == 0), width=80, textvariable=self.values[row])
               widget.grid(row=row, column=1, columnspan=12, sticky=E + W)
               v = prop.type
           elif prop.type.startswith('boxpair'):
               partialf = partial(promptForBoxPairAndFillButtonText, self, prop.name, row)
               self.buttons[prop.name] = widget = Button(master,
                                                         text=v if v is not None else '',
                                                         takefocus=False,
                                                         command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type.startswith('listfromfile:'):
               filename = getFileName(prop.type[13:])
               if filename:
                   with open(filename) as f:
                       values = sorted(f.read().splitlines())
                   widget = ttk.Combobox(master, values=values, textvariable=self.values[row])
               else:
                   logging.getLogger("maskgen").warning(prop.type[13:] + " NOT found.")
                   widget = Entry(master, takefocus=(row == 0), width=80, textvariable=self.values[row])
               widget.grid(row=row, column=1, columnspan=12, sticky=E + W)
           elif prop.type == 'label':
               widget = Label(master, takefocus=(row==0), width=80, text=prop.information)
               widget.grid(row=row, column=0, columnspan=12, sticky=E + W)
           elif prop.type == 'time':
                widget = TimeWidget(master, textvariable=self.values[row])
                widget.grid(row=row, column=1, columnspan=12, sticky=E + W)
           else:
               widget = Entry(master, takefocus=(row == 0), width=80, textvariable=self.values[row])
               widget.grid(row=row, column=1, columnspan=12, sticky=E + W)
           self.widgets[row] = widget
           if prop.readonly:
               if prop.type == 'yesno':
                   widget[0].config(state=DISABLED)
                   widget[1].config(state=DISABLED)
               elif prop.type != 'list':
                   widget.config(state=DISABLED)
           row += 1

   def findWidgetValue(self, widget, prop):
       return widget.get().strip()

   def apply(self):
       i = 0
       for prop in self.properties:
           v = self.findWidgetValue(self.values[i], prop)
           v, error = checkValue(prop.name, prop.type, v)
           if v and len(v) > 0 and error is None:
               self.propertyFunction.setValue(prop.name, v)
           elif error is not None:
               tkMessageBox.showwarning('Error', prop.name, error)
           i += 1



class ProperyChangeAction:

    """
    Customized actions to take for specific properties by PropertyFunction
    @see PropertyFunction
    """

    def __init__(self):
        pass

    def setvalue(self, oldvalue, newvalue):
        pass

class SystemPropertyFunction(PropertyFunction):

    prefLoader = None
    """
    @type prefLoader: MaskGenLoader
    @type property_change_actions: dict {str:ProperyChangeAction)
    """
    def __init__(self,prefLoader,property_change_actions):
        """

        :param prefLoader:
        @type prefLoader: MaskGenLoader
        """
        self.prefLoader = prefLoader
        self.property_change_actions = property_change_actions


    def getValue(self, name):
        return self.prefLoader.get_key(name,'')

    def setValue(self, name,value):
        if name in self.property_change_actions:
            self.property_change_actions[name].setvalue(self.prefLoader.get_key(name,''), value)
        return self.prefLoader.save(name,value)

class ProjectPropertyFunction(PropertyFunction):

    def __init__(self,scModel):
        """
        :param scModel:
        @type scModel: ImageProjectModel
        """
        self.scModel = scModel

    def getValue(self, name):
        return self.scModel.getProjectData(name)

    def setValue(self, name,value):
        return self.scModel.setProjectData(name,value)

class SystemPropertyDialog(tkSimpleDialog.Dialog):

   cancelled = False
   def __init__(self, parent, properties, prefLoader=None,title="System Properties",
                dir='.',
                property_change_actions=dict()):
        self.properties =properties
        self.prefLoader = prefLoader
        self.dir=dir
        self.property_change_actions = property_change_actions
        tkSimpleDialog.Dialog.__init__(self, parent, title)

   def body(self, master):
        self.vs = PropertyFrame(master,
                            self.properties,
                            propertyFunction=SystemPropertyFunction(self.prefLoader,
                                                                    self.property_change_actions),
                            dir=self.dir)
        self.wm_resizable(width=False,height=True)
        self.master.pack_propagate(True)
        self.master.grid_propagate(True)
        self.vs.pack(side="top", fill="both", expand=True)

   def buttonbox(self):
        '''add standard button box.

        override if you do not want the standard buttons
        '''

        box = Frame(self)

        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack(expand=False)

   def cancel(self, event=None):
    self.cancelled = True
    tkSimpleDialog.Dialog.cancel(self,event=event)

   def apply(self):
       if not self.cancelled:
            self.vs.apply()
       tkSimpleDialog.Dialog.apply(self)

class PropertyDialog(tkSimpleDialog.Dialog):

   cancelled = False
   def __init__(self, parent, properties, scModel=None,title="Project Properties", dir='.'):
        self.properties =properties
        self.scModel = scModel
        self.dir=dir
        tkSimpleDialog.Dialog.__init__(self, parent, title)

   def body(self, master):
        self.vs = PropertyFrame(master, self.properties,
                           propertyFunction=ProjectPropertyFunction(self.scModel),
                            dir=self.dir)
        self.vs.grid(row=0)

   def cancel(self, event=None):
    self.cancelled = True
    tkSimpleDialog.Dialog.cancel(self,event=event)

   def apply(self):
       if not self.cancelled:
            self.vs.apply()
       tkSimpleDialog.Dialog.apply(self)

class EdgePropertyFunction(PropertyFunction):

    lookup_values = {}

    scModel = None
    def __init__(self,  properties, scModel):
        """
        :param properties:
        :param scModel:
        @type properties: dict
        @type scModel: ImageProjectModel
        """
        self.scModel = scModel
        for prop in properties:
            self.lookup_values[prop.name] = prop.value

    def getValue(self, name):
        return self.lookup_values[name]

    def setValue(self, name,value):
        self.lookup_values[name] = value

class NodePropertyFunction(PropertyFunction):

    def __init__(self,  properties):
        """
        """
        self.lookup_values = properties

    def getValue(self, name):
        return  self.lookup_values[name] if name in self.lookup_values else None

    def setValue(self, name,value):
        self.lookup_values[name] = value


class ValidationFrame(VerticalScrolledFrame):

    def __init__(self, master, parent,items,**kwargs):
        """

        :param master:
        :param parent:
        :param items:
        :param kwargs:
        @type items: list of ValidationMessage
        """
        VerticalScrolledFrame.__init__(self, master,horizontal=True,**kwargs)
        self.parent = parent
        self.body(self.interior, items)
        self.fixes = []
        self.items = items

    def errorMessagesIncomplete(self):
        """
              Unrepaired error messages still in the list?
              :return: bool
              @rtype: bool
              """
        for row in range(len(self.items)):
            item = self.items[row]
            if item.Severity in [Severity.CRITICAL,Severity.ERROR] and row not in self.fixes:
                return True
        return False

    def autofixesComplete(self):
        """
        Are some repairable errors not repaired?
        :return: bool
        @rtype: bool
        """
        for row in range(len(self.items)):
            item = self.items[row]
            if item.Fix is not None and row not in self.fixes:
                return False
        return True


    def fix(self, row, item):
        """
        :param row:
        :param item:
        :return:
        @type item: ValidationMessage
        """
        try:
            item.applyFix(self.parent.scModel.getGraph())
            self.widgets[row - 1].grid_forget()
            self.buttons[row - 1].grid_forget()#config(state=DISABLED)
            self.fixes.append(row - 1)
        except Exception as ex:
            tkMessageBox.showwarning('Error' ,str(ex))

    def body(self,master, items):
        """
        :param parent:
        :param items:
        :return:
        @type items: list of ValidationMessage
        """
        row = 1
        self.buttons = []
        self.widgets = []
        for item in items:
            if item.Start != item.End:
                item_text='{}: {}->{} {}'.format(item.Severity.name,
                                                                self.parent.scModel.getFileName(item.Start),
                                                                self.parent.scModel.getFileName(item.End),
                                                                item.Message)
            elif len(item[1]) > 0:
                item_text=  '{}: {} {}'.format(item.Severity.name,
                                                            self.parent.scModel.getFileName(item.Start),
                                                            item.Message)
            else:
                item_text= '{}: {}'.format(item.Severity.name,
                                                         item.Message)

            cb = partial(self.parent.selectLink,item.Start,item.End)
            cbfix = partial(self.fix,row,item)
            widget = Button(master, text=item_text, command=cb)
            widget.config(relief=SUNKEN)
            button = Button(master, text='Fix', takefocus=False, command=cbfix)
            button.config(state=DISABLED if item.Fix is None else ACTIVE)
            self.buttons.append(button)
            self.widgets.append(widget)
            button.grid(row=row, column=2,sticky=E)
            widget.grid(row=row, column=1,sticky=W)
            row+=1


class ValidationListDialog(Toplevel):
    items = None

    def __init__(self, parent, items, name):
        """
        :param items:
        :return:
        @type items: list of ValidationMessage
        """
        self.items = items
        self.parent = parent
        Toplevel.__init__(self, parent)
        self.resizable(width=True, height=True)
        self.title(name)
        self.parent = parent
        body = Frame(self)
        body.pack(padx=5, pady=5, fill=BOTH, expand=True)
        self.itemsframe = ValidationFrame(body, parent,items)
        self.itemsframe.grid(row=0, column=0, sticky=N + E + S + W)
        self.grid_propagate(True)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        w = self.buttons(body)
        w.grid(row=2, column=0)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

    def buttons(self, frame):
        return Button(frame, text="OK", width=10, command=self.cancel, default=ACTIVE)

    def cancel(self):
        # self.parent.doneWithWindow(self)
        self.parent.focus_set()
        self.destroy()


class DecisionValidationListDialog(ValidationListDialog):
    isok = False

    def __init__(self, parent, items, name):
        ValidationListDialog.__init__(self, parent, items, name)

    def autofixesComplete(self):
        return self.itemsframe.autofixesComplete()

    def errorMessagesIncomplete(self):
        return self.itemsframe.errorMessagesIncomplete()

    def setok(self):
        self.isok = True
        self.cancel()

    def wait(self, root):
        root.wait_window(self)

    def buttons(self, frame):
        box = Frame(frame)
        w1 = Button(box, text="Cancel", width=10, command=self.cancel, default=ACTIVE)
        w2 = Button(box, text="Continue", width=10, command=self.setok, default=ACTIVE)
        w1.pack(side=LEFT, padx=5, pady=5)
        w2.pack(side=RIGHT, padx=5, pady=5)
        return box
