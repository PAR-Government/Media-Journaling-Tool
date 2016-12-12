from Tkinter import *
import ttk
import time
import tkMessageBox
from group_filter import GroupFilter, GroupFilterLoader
import Tkconstants, tkFileDialog, tkSimpleDialog
from PIL import ImageTk
from autocomplete_it import AutocompleteEntryInText
from tool_set import imageResize, imageResizeRelative, fixTransparency, openImage, openFile, validateTimeString, \
    validateCoordinates, getMaskFileTypes, getFileTypes, get_username
from scenario_model import Modification,ImageProjectModel
from software_loader import Software, SoftwareLoader
import os
import numpy as np
from tkintertable import TableCanvas, TableModel
from image_wrap import ImageWrapper
from functools import partial
from group_filter import getOperationWithGroups,getOperationsByCategoryWithGroups,getCategoryForOperation
from software_loader import ProjectProperty


def checkValue(name, type, value):
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
    if value and len(value) > 0:
        if type.startswith('float'):
            vals = [float(x) for x in type[type.rfind('[') + 1:-1].split(':')]
            try:
                value = float(value)
                if value < vals[0] or value > vals[1]:
                    raise ValueError(value)
            except:
                return None, 'Invalid value for ' + name + '; not in range ' + str(vals[0]) + ' to ' + str(
                    vals[1])
        elif type.startswith('int'):
            vals = [int(x) for x in type[type.rfind('[') + 1:-1].split(':')]
            try:
                value = int(value)
                if value < vals[0] or value > vals[1]:
                    raise ValueError(value)
            except:
                return None, 'Invalid value for ' + name + '; not in range ' + str(vals[0]) + ' to ' + str(
                    vals[1])
        elif type == 'time':
            if not validateTimeString(value):
                return None, 'Invalid time value for ' + name + '; not in format 00:00:00.000 or 00:00:00:00'
        elif type == 'coordinates':
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
    val = tkFileDialog.askopenfilename(initialdir=dir, title="Select " + id,
                                       filetypes=filetypes)
    var = obj.values[row]
    var.set(val if (val is not None and len(val) > 0) else None)
    obj.buttons[id].configure(text=os.path.split(val)[1] if (val is not None and len(val) > 0) else ' ' * 30)


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
    d = ImageNodeCaptureDialog(obj, obj.scModel)
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
    if argumentTuple[1]['type'] == 'imagefile':
        val = tkFileDialog.askopenfilename(initialdir=dir, title="Select " + argumentTuple[0], filetypes=filetypes)
        if (val != None and len(val) > 0):
            res = val
    elif argumentTuple[1]['type'] == 'xmpfile':
        val = tkFileDialog.askopenfilename(initialdir=dir, title="Select " + argumentTuple[0],
                                           filetypes=[('XMP', '*.xmp')])
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
    else:
        d = EntryDialog(parent, "Set Parameter " + argumentTuple[0], argumentTuple[1]['description'], None,
                        initialvalue=initialvalue)
        res = d.choice
    return res


def getCategory(mod):
    if mod.category is not None and len(mod.category) > 0:
        return mod.category
    return getCategoryForOperation(mod.operationName)

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
            self.children['menu'].add_command(label=val, command=lambda v=self.var, l=val: self.doit(l))

    def set_completion_list(self, values, initialValue=None):
        if initialValue is None:
            initialValue = values[0] if len(values) > 0 else ''
        if initialValue not in values:
            initialValue = ''
        self.children['menu'].delete(0, END)
        for val in values:
            self.children['menu'].add_command(label=val, command=lambda v=self.var, l=val: self.doit(l))
        self.var.set(initialValue)

    def get(self):
        return self.var.get()

    def doit(self,v):
        self.var.set(v)
        if self.command is not None:
            self.command(self.var.get())

    def bind(self, name, command):
        self.command = command

class PropertyFunction:

    def getValue(self, name):
        return None

    def setValue(self, name,value):
        return None



class DescriptionCaptureDialog(tkSimpleDialog.Dialog):
    description = None
    im = None
    inputMaskName = None
    dir = '.'
    photo = None
    c = None
    moc = None
    cancelled = True
    sourcefiletype = 'image'
    targetfiletype = 'image'
    argvalues = {}
    arginfo = []
    mandatoryinfo = []
    argBox = None

    def __init__(self, parent, uiProfile, scModel, targetfiletype, im, name, description=None):
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
        self.dir = scModel.get_dir()
        self.uiProfile = uiProfile
        self.im = im
        self.parent = parent
        self.scModel = scModel
        self.sourcefiletype = scModel.getStartType()
        self.targetfiletype = targetfiletype
        self.argvalues = description.arguments if description is not None else {}
        self.description = description if description is not None else Modification('', '')
        self.softwareLoader = SoftwareLoader()
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def newsoftware(self, event):
        sname = self.e4.get()
        self.e5.set_completion_list(self.softwareLoader.get_versions(sname,software_type=self.sourcefiletype),
                                    initialValue=self.softwareLoader.get_preferred_version(name=sname))



    def __addToBox(self, arg, mandatory):
        sep = '*: ' if mandatory else ': '
        if arg == 'inputmaskname':
            self.argBox.insert(END, arg + sep + (self.inputMaskName if self.inputMaskName is not None else ''))
        else:
            self.argBox.insert(END, arg + sep + (
            str(self.description.arguments[arg]) if arg in self.description.arguments else ''))

    def buildArgBox(self):
        if self.argBox is not None:
            self.argBox.destroy()
        properties = [ProjectProperty(name=argumentTuple[0],
                                      description=argumentTuple[0],
                                      information=argumentTuple[1]['description'],
                                      type=argumentTuple[1]['type'],
                                      values=argumentTuple[1]['values'] if 'values' in argumentTuple[1] else [],
                                      value=self.argvalues[argumentTuple[0]] if argumentTuple[
                                                                                    0] in self.argvalues else None) \
                      for argumentTuple in self.arginfo]
        self.argBox= PropertyFrame(self.argBoxMaster, properties,
                                scModel=self.scModel,
                                propertyFunction=EdgePropertyFunction(properties),
                                changeParameterCB=self.changeParameter,
                                dir=self.dir)
        self.argBox.grid(row=self.argBoxRow, column=0, columnspan=2, sticky=E + W)

    def newcommand(self, event):
        op = getOperationWithGroups(self.e2.get())
        self.arginfo = []
        self.mandatoryinfo = []
        if op is not None:
            for k, v in op.mandatoryparameters.iteritems():
                if 'source' in v and v['source'] != self.sourcefiletype:
                    continue
                if 'target' in v and v['target'] != self.targetfiletype:
                    continue
                self.arginfo.append((k, v))
                self.mandatoryinfo.append(k)
            for k, v in op.optionalparameters.iteritems():
                if 'source' in v and v['source'] != self.sourcefiletype:
                    continue
                if 'target' in v and v['target'] != self.targetfiletype:
                    continue
                self.arginfo.append((k, v))
        self.buildArgBox()
        if self.okButton is not None:
            self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)

    def organizeOperationsByCategory(self):
        return getOperationsByCategoryWithGroups(self.sourcefiletype, self.targetfiletype)

    def newcategory(self, event):
        opByCat = self.organizeOperationsByCategory()
        if self.e1.get() in opByCat:
            oplist = opByCat[self.e1.get()]
            self.e2.set_completion_list(oplist)
            self.newcommand(event)
        else:
            self.e2.set_completion_list([])

    def body(self, master):
        self.okButton = None

        self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im, (250, 250))).toPIL())
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
        row = 6
        Label(master, text='Parameters:', anchor=W, justify=LEFT).grid(row=row, column=0, columnspan=2)
        row += 1
        self.argBoxRow = row
        self.argBoxMaster = master
        self.argBox = self.buildArgBox()
        row += 1

        cats = self.organizeOperationsByCategory()
        catlist = list(cats.keys())
        catlist.sort()
        oplist = cats[catlist[0]] if len(cats) > 0 else []
        self.e1 = MyDropDown(master, catlist, command=self.newcategory)
        self.e2 = MyDropDown(master, oplist, command=self.newcommand)
        self.e4 = MyDropDown(master, sorted(self.softwareLoader.get_names(self.sourcefiletype), key=str.lower), command=self.newsoftware)
        self.e5 = AutocompleteEntryInText(master, values=[], takefocus=False, width=40)
        self.e1.bind("<Return>", self.newcategory)
        self.e1.bind("<<ComboboxSelected>>", self.newcategory)
        self.e2.bind("<Return>", self.newcommand)
        self.e2.bind("<<ComboboxSelected>>", self.newcommand)
        self.e4.bind("<Return>", self.newsoftware)
        self.e4.bind("<<ComboboxSelected>>", self.newsoftware)
        self.e3 = Text(master, height=2, width=40, font=('Times', '14'), relief=RAISED, borderwidth=2)

        self.e1.grid(row=1, column=1, sticky=EW)
        self.e2.grid(row=2, column=1, sticky=EW)
        self.e3.grid(row=3, column=1, sticky=EW)
        self.e4.grid(row=4, column=1, sticky=EW)
        self.e5.grid(row=5, column=1)

        if self.description is not None:
            if (self.description.inputMaskName is not None):
                self.inputMaskName = self.description.inputMaskName
            if self.description.operationName is not None and len(self.description.operationName) > 0:
                selectCat = getCategory(self.description)
                self.e1.set_completion_list(catlist, initialValue=selectCat)
                oplist = cats[selectCat] if selectCat in cats else []
                self.e2.set_completion_list(oplist, initialValue=self.description.operationName)
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

    def __getinfo(self,name):
        for k,v in self.arginfo:
            if k == name:
                return v
        return None

    def __checkParams(self):
        ok = True
        for k,v in self.argvalues.iteritems():
            info = self.__getinfo(k)
            cv,error = checkValue(k,info['type'],v)
            if v is not None and cv is None:
                ok = False
        for arg in self.mandatoryinfo:
            ok &= (arg in self.argvalues and self.argvalues[arg] is not None and len(str(self.argvalues[arg])) > 0)
        return ok

    def buttonbox(self):
        box = Frame(self)
        self.okButton = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE,
                               state=ACTIVE if self.__checkParams() else DISABLED)
        self.okButton.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def changeParameter(self, name, type, value):
        self.argvalues[name] = value
        if name == 'inputmaskname' and value is not None:
            self.inputMaskName = value
        if self.okButton is not None:
            self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)

    def help(self):
        op = getOperationWithGroups(self.e2.get())
        if op is not None:
            tkMessageBox.showinfo(op.name, op.description if op.description is not None and len(
                op.description) > 0 else 'No description')

    def cancel(self):
        if self.cancelled:
            self.description = None
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.description.setOperationName(self.e2.get())
        self.description.setAdditionalInfo(self.e3.get(1.0, END).strip())
        self.description.setInputMaskName(self.inputMaskName)
        self.description.setArguments(
            {k: v for (k, v) in self.argvalues.iteritems() if k in [x[0] for x in self.arginfo]})
        self.description.setSoftware(Software(self.e4.get(), self.e5.get()))
        if (self.softwareLoader.add(self.description.software)):
            self.softwareLoader.save()


class DescriptionViewDialog(tkSimpleDialog.Dialog):
    description = None
    im = None
    photo = None
    c = None
    metadiff = None
    metaBox = None

    def __init__(self, parent, dir, im, name, description=None, metadiff=None):
        self.im = im
        self.dir = dir
        self.parent = parent
        self.description = description if description is not None else Modification('', '')
        self.metadiff = metadiff
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        vscrollbar = Scrollbar(master, orient=VERTICAL)
        Label(master, text="Operation:", anchor=W, justify=LEFT).grid(row=0, column=0, sticky=W)
        Label(master, text="Description:", anchor=W, justify=LEFT).grid(row=1, column=0, sticky=W)
        Label(master, text="Software:", anchor=W, justify=LEFT).grid(row=2, column=0, sticky=W)
        Label(master, text=getCategory(self.description), anchor=W, justify=LEFT).grid(row=0, column=1, sticky=W)
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
        row = 4
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
            self.maskBox = MaskSetTable(master, self.description.maskSet, openColumn=3, dir=self.dir)
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
        self.box.grid(row=0, column=1)
        self.c = Canvas(master, width=250, height=250)
        self.photo = ImageTk.PhotoImage(ImageWrapper(np.zeros((250, 250,3))).toPIL())
        self.imc = self.c.create_image(125, 125, image=self.photo, tag='imgd')
        self.c.grid(row=1, column=0, columnspan=2)
        self.box.bind("<Return>", self.newimage)
        self.box.bind("<<ComboboxSelected>>", self.newimage)

    def newimage(self, event):
        im = self.scModel.getImage(self.box.get())
        self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(im, (250, 250))).toPIL())
        self.c.itemconfig(self.imc, image=self.photo)

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
    im = None
    photo = None
    c = None
    optocall = None
    argvalues = {}
    cancelled = True
    mandatoryinfo = []

    def __init__(self, parent, dir, im, pluginOps, name, scModel):
        self.pluginOps = pluginOps
        self.im = im
        self.dir = dir
        self.parent = parent
        self.scModel = scModel
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        self.photo = ImageTk.PhotoImage(imageResize(self.im, (250, 250)).toPIL())
        self.c = Canvas(master, width=250, height=250)
        self.c.create_image(128, 128, image=self.photo, tag='imgd')
        self.c.grid(row=0, column=0, columnspan=2)
        self.e1 = AutocompleteEntryInText(master, values=self.pluginOps.keys(), takefocus=True)
        self.e1.bind("<Return>", self.newop)
        self.e1.bind("<<ComboboxSelected>>", self.newop)
        row = 1
        labels = ['Plugin Name:', 'Category:', 'Operation:', 'Software Name:', 'Software Version:']
        for label in labels:
            Label(master, text=label, anchor=W, justify=LEFT).grid(row=row, column=0, sticky=W)
            row += 1
        self.catvar = StringVar()
        self.opvar = StringVar()
        self.softwarevar = StringVar()
        self.versionvar = StringVar()
        self.e1.grid(row=1, column=1)
        row = 2
        variables = [self.catvar, self.opvar, self.softwarevar, self.versionvar]
        for variable in variables:
            Label(master, textvariable=variable, anchor=W, justify=LEFT).grid(row=row, column=1, sticky=W)
            row += 1
        Label(master, text='Parameters:', anchor=W, justify=LEFT).grid(row=row, column=0, columnspan=2)
        row += 1
        self.argBoxRow = row
        self.argBoxMaster = master
        self.argBox = Listbox(master)
        self.argBox.bind("<Double-Button-1>", self.changeParameter)
        self.argBox.grid(row=row, column=0, columnspan=2, sticky=E + W)
        if len(self.pluginOps.keys()) > 0:
            self.newop(None)

    def __checkParams(self):
        ok = True
        for arg in self.mandatoryinfo:
            ok &= (arg in self.argvalues and self.argvalues[arg] is not None and len(str(self.argvalues[arg])) > 0)
        return ok

    def __buildTuple(self, argument, operation):
        argumentTuple = (argument[0], operation.mandatoryparameters[argument[0]]) if operation is not None and argument[
                                                                                                         0] in operation.mandatoryparameters else None
        argumentTuple = (argument[0], operation.optionalparameters[argument[0]]) if operation is not None and argument[
                                                                                                        0] in operation.optionalparameters else argumentTuple
        argumentTuple = ('donor', {'type': 'donor', 'description': 'Donor'}) if argument[
                                                                                    0] == 'donor' else argumentTuple
        argumentTuple = ('inputmaskname', {'type': 'imagefile', 'description': 'Input Mask File'}) if argument[
                                                                                                          0] == 'inputmaskname' else argumentTuple
        argumentTuple = (argument[0], {'type': 'string', 'description': argument[2] if len(
            argument) > 2 else 'Not Available'}) if argumentTuple is None else argumentTuple
        return argumentTuple

    def buildArgBox(self, operationName, arginfo):
        if self.argBox is not None:
            self.argBox.destroy()
        if arginfo is None:
            arginfo = []
        operation = getOperationWithGroups(operationName)
        argumentTuples = [self.__buildTuple(arg, operation) for arg in arginfo]
        properties = [ProjectProperty(name=argumentTuple[0],
                                      description=argumentTuple[0],
                                      information=argumentTuple[1]['description'],
                                      type=argumentTuple[1]['type'],
                                      values=argumentTuple[1]['values'] if 'values' in argumentTuple[1] else [],
                                      value=self.argvalues[argumentTuple[0]] if argumentTuple[
                                                                                    0] in self.argvalues else None) \
                      for argumentTuple in argumentTuples]
        self.argBox= PropertyFrame(self.argBoxMaster, properties,
                                scModel=self.scModel,
                                propertyFunction=EdgePropertyFunction(properties),
                                changeParameterCB=self.changeParameter,
                                dir=self.dir)
        self.argBox.grid(row=self.argBoxRow, column=0, columnspan=2, sticky=E + W)

    def buttonbox(self):
        box = Frame(self)
        self.okButton = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE,
                               state=ACTIVE if self.__checkParams() else DISABLED)
        self.okButton.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def changeParameter(self, name, type, value):
        v, error = checkValue(name,type, value)
        self.argvalues[name] = v
        if name == 'inputmaskname' and value is not None:
            self.inputMaskName = value
        if self.okButton is not None:
            self.okButton.config(state=ACTIVE if self.__checkParams() else DISABLED)

    def newop(self, event):
        self.argvalues = {}
        if (self.pluginOps.has_key(self.e1.get())):
            self.optocall = self.e1.get()
            op = self.pluginOps[self.optocall]
            opinfo = op['operation']
            self.catvar.set(opinfo[1])
            self.opvar.set(opinfo[0])
            self.softwarevar.set(opinfo[3])
            self.versionvar.set(opinfo[4])
            self.buildArgBox(opinfo[0], op['arguments'])
        else:
            self.catvar.set('')
            self.opvar.set('')
            self.softwarevar.set('')
            self.versionvar.set('')
            self.optocall = None
            self.buildArgBox(None, [])

    def cancel(self):
        if self.cancelled:
            self.optocall = None
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.optocall = self.e1.get()


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


class ActionableTableCanvas(TableCanvas):
    def __init__(self, parent=None, model=None, width=None, height=None, openColumn=None, dir='.', **kwargs):
        self.openColumn = openColumn
        self.dir = dir
        TableCanvas.__init__(self, parent=parent, model=model, width=width, height=height, **kwargs)

    def handle_double_click(self, event):
        row = self.get_row_clicked(event)
        self.openFile(row)

    def openFile(self, row):
        model = self.getModel()
        f = model.getValueAt(row, self.openColumn)
        if f is not None and len(str(f)) > 0:
          openFile(os.path.join(self.dir, f))

    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        defaultactions = {"Set Fill Color": lambda: self.setcellColor(rows, cols, key='bg'),
                          "Set Text Color": lambda: self.setcellColor(rows, cols, key='fg'),
                          "Open": lambda: self.openFile(row),
                          "Copy": lambda: self.copyCell(rows, cols),
                          "View Record": lambda: self.getRecordInfo(row),
                          "Select All": self.select_All,
                          "Filter Records": self.showFilteringBar,
                          "Export csv": self.exportTable,
                          "Plot Selected": self.plotSelected,
                          "Plot Options": self.plotSetup,
                          "Export Table": self.exportTable,
                          "Preferences": self.showtablePrefs,
                          "Formulae->Value": lambda: self.convertFormulae(rows, cols)}

        if self.openColumn:
            main = ["Open", "Set Fill Color", "Set Text Color", "Copy"]
        else:
            main = ["Set Fill Color", "Set Text Color", "Copy"]
        general = ["Select All", "Filter Records", "Preferences"]
        filecommands = ['Export csv']
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
    print diff
    if abs(diff) < 0.00000001:
        return -1 if numstringa[1] < numstringb[1] else (0 if numstringa[1] == numstringb[1] else 1)
    return int(np.sign(diff))

def sortMask(a,b):
    return compareNumString(toNumString(a),toNumString(b))

class MaskSetTable(Frame):
    section = None

    def __init__(self, master, items, openColumn=3, dir='.', **kwargs):
        self.items = items
        Frame.__init__(self, master, **kwargs)
        self._drawMe(dir, openColumn)

    def _drawMe(self, dir, openColumn):
        model = TableModel()
        for c in self.items.columnNames:
            model.addColumn(c)
        model.importDict(self.items.columnValues)
        model.reclist = sorted(model.reclist)

        self.table = ActionableTableCanvas(self, model=model, rowheaderwidth=140, showkeynamesinheader=True, height=125,
                                           openColumn=openColumn, dir=dir)
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

        self.table = ActionableTableCanvas(self, model=model, rowheaderwidth=140, showkeynamesinheader=True, height=125)
        self.table.updateModel(model)
        self.table.createTableFrame()


class ListDialog(Toplevel):
    items = None

    def __init__(self, parent, items, name):
        self.items = items
        self.parent = parent
        Toplevel.__init__(self, parent)
        self.resizable(width=True, height=True)
        self.title(name)
        self.parent = parent
        body = Frame(self)
        self.body(body)
        body.grid(row=0, column=0, sticky=N + E + S + W)
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

    def setItems(self, items):
        self.items = items
        self.itemBox.delete(0, END)
        for item in self.items:
            self.itemBox.insert(END, item[2])

    def body(self, master):
        self.yscrollbar = Scrollbar(master, orient=VERTICAL)
        self.xscrollbar = Scrollbar(master, orient=HORIZONTAL)
        self.itemBox = Listbox(master, width=80, yscrollcommand=self.yscrollbar.set, xscrollcommand=self.xscrollbar.set)
        self.itemBox.bind("<Double-Button-1>", self.change)
        self.itemBox.grid(row=0, column=0, sticky=E + W + N + S)
        self.xscrollbar.config(command=self.itemBox.xview)
        self.xscrollbar.grid(row=1, column=0, stick=E + W)
        self.yscrollbar.config(command=self.itemBox.yview)
        self.yscrollbar.grid(row=0, column=1, stick=N + S)
        for item in self.items:
            self.itemBox.insert(END, item[2])

    def cancel(self):
        self.parent.doneWithWindow(self)
        self.parent.focus_set()
        self.destroy()

    def change(self, event):
        if len(self.itemBox.curselection()) == 0:
            return
        index = int(self.itemBox.curselection()[0])
        self.parent.selectLink(self.items[index][0], self.items[index][1])


class DecisionListDialog(ListDialog):
    isok = False

    def __init__(self, parent, items, name):
        ListDialog.__init__(self, parent, items, name)

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

class CompositeCaptureDialog(tkSimpleDialog.Dialog):
    im = None
    selectMaskName = None
    cancelled = True
    modification = None
    start_type = None
    end_type = None

    def __init__(self, parent, start_type, end_type,  dir, im, name, modification):
        self.dir = dir
        self.im = im
        self.start_type = start_type
        self.end_type = end_type
        self.parent = parent
        self.name = name
        self.modification = modification
        self.selectMaskName = self.modification.selectMaskName
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im, (250, 250))).toPIL())
        self.c = Canvas(master, width=250, height=250)
        self.image_on_canvas = self.c.create_image(125, 125, image=self.photo, tag='imgd')
        self.c.grid(row=0, column=0, columnspan=2)
        self.includeInMaskVar = StringVar()
        self.includeInMaskVar.set(self.modification.recordMaskInComposite)
        self.cbIncludeInComposite = Checkbutton(master, text="Included in Composite", variable=self.includeInMaskVar, \
                                                onvalue="yes", offvalue="no")
        self.useInputMaskVar = StringVar()
        self.useInputMaskVar.set('yes' if self.modification.usesInputMaskForSelectMask() else 'no')
        row = 1
        self.cbIncludeInComposite.grid(row=row, column=0, columnspan=2, sticky=W)
        row += 1
        if self.modification.inputMaskName is not None:
            self.cbUseInputMask = Checkbutton(master, text="Use Input Mask", variable=self.useInputMaskVar,
                                              onvalue="yes", offvalue="no", command=self.useinputmask)
            self.cbUseInputMask.grid(row=row, column=0, columnspan=2, sticky=W)
            row += 1
        self.b = Button(master, text="Change Mask", command=self.changemask, borderwidth=0, relief=FLAT)
        self.b.grid(row=row, column=0)
        return self.cbIncludeInComposite

    def useinputmask(self):
        if self.useInputMaskVar.get() == 'yes':
            self.im = openImage(os.path.join(self.dir, self.modification.inputMaskName), isMask=True,
                                preserveSnapshot=True)
            self.selectMaskName = self.modification.inputMaskName
        elif self.modification.changeMaskName is not None:
            self.im = openImage(os.path.join(self.dir, self.modification.changeMaskName), isMask=True,
                                preserveSnapshot=True)
            self.selectMaskName = self.modification.changeMaskName
        else:
            self.im = ImageWrapper(np.zeros((250, 250, 3)))
        self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im, (250, 250))).toPIL())
        self.c.itemconfig(self.image_on_canvas, image=self.photo)

    def changemask(self):
        val = tkFileDialog.askopenfilename(initialdir=self.dir, title="Select Input Mask",
                                           filetypes=getMaskFileTypes())
        if (val != None and len(val) > 0):
            self.selectMaskName = val
            self.im = openImage(val, isMask=True, preserveSnapshot=os.path.split(os.path.abspath(val))[0] == dir)
            self.photo = ImageTk.PhotoImage(fixTransparency(imageResize(self.im, (250, 250))).toPIL())
            self.c.itemconfig(self.image_on_canvas, image=self.photo)

    def cancel(self):
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.modification.setSelectMaskName(self.selectMaskName)
        self.modification.setRecordMaskInComposite(self.includeInMaskVar.get())


class CompositeViewDialog(tkSimpleDialog.Dialog):
    im = None
    composite = None
    """
    @type im: ImageWrapper
    @type composite: ImageWrapper
    """

    def __init__(self, parent, name, composite, im):
        self.composite = composite
        self.im= im
        self.parent = parent
        self.name = name
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        compositeResized = imageResizeRelative(self.composite, (500, 500),self.composite.size)
        if self.im is not None:
            imResized = imageResizeRelative(self.im, (500, 500),self.im.size)
            imResized = imResized.overlay(compositeResized)
        else:
            imResized = compositeResized
        self.photo = ImageTk.PhotoImage(imResized.toPIL())
        self.c = Canvas(master, width=compositeResized.size[0]+10, height=compositeResized.size[1]+10)
        self.image_on_canvas = self.c.create_image(0,0, image=self.photo,anchor=NW, tag='imgd')
        self.c.grid(row=0, column=0, columnspan=2)

    def buttonbox(self):
        box = Frame(self)
        w1 = Button(box, text="Close", width=10, command=self.ok, default=ACTIVE)
        w2 = Button(box, text="Export", width=10, command=self.saveThenOk, default=ACTIVE)
        w1.pack(side=LEFT, padx=5, pady=5)
        w2.pack(side=RIGHT, padx=5, pady=5)
        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def saveThenOk(self):
        val = tkFileDialog.asksaveasfilename(initialdir='.', initialfile=self.name + '_composite.png',
                                             filetypes=[("png files", "*.png")], defaultextension='.png')
        if (val is not None and len(val) > 0):
            # to cover a bug in some platforms
            if not val.endswith('.png'):
                val = val + '.png'
            self.im.save(val)
            self.ok()

class QAViewDialog(Toplevel):
    def __init__(self, parent, terminalNodes, donorNodes):
        self.terminals = terminalNodes
        self.donors = donorNodes
        self.parent = parent
        Toplevel.__init__(self, parent)
        #self.complete = True if self.parent.scModel.getProjectData('validation') == 'yes' else False
        self.createWidgets()
        self.resizable(width=False, height=False)

    def createWidgets(self):
        row=0
        col=0
        self.optionsLabel = Label(self, text='Select terminal node to view composite, or PasteSplice node to view donor mask: ')
        self.optionsLabel.grid(row=row)
        row+=1
        self.optionsBox = ttk.Combobox(self, values=self.terminals + self.donors)
        self.optionsBox.set(self.terminals[0])
        self.optionsBox.grid(row=row, sticky='EW')
        self.optionsBox.bind("<<ComboboxSelected>>", self.composite_or_donor)
        row+=1
        self.cImgFrame = Frame(self)
        self.cImgFrame.grid(row=row, rowspan=8)
        self.master.scModel.selectImage(self.terminals[0])
        self.descriptionLabel = Label(self)
        self.composite_or_donor(initialize=True)

        row=1
        col=1

        self.validateButton = Button(self, text='Check Validation', command=self.parent.validate, width=50)
        self.validateButton.grid(row=row, column=col, padx=10, columnspan=6, sticky='EW')
        row+=1

        self.infolabel = Label(self, justify=LEFT, text='QA Checklist:').grid(row=row, column=col)
        row+=1

        qa_list = ['Input masks are provided where possible, especially for any operation where pixels were directly taken from one region to another (e.g. PasteSampled)',
                   'PasteSplice operations should include resizing, rotating, positioning, and cropping of the pasted object in their arguments as one operation. \n -For example, there should not be a PasteSplice followed by a TransformRotate of the pasted object.',
                   'Base and terminal node images should be the same format.\n -If the base was a JPEG, the Create JPEG/TIFF option should be used as the last step.',
                   'Verify that all relevant local changes are accurately represented in the composite and donor mask image(s), which can be easily viewed to the left.']
        checkboxes = []
        self.checkboxvars = []
        for q in qa_list:
            var = BooleanVar()
            ck = Checkbutton(self, variable=var, command=self.check_ok)
            ck.select() if self.parent.scModel.getProjectData('validation') == 'yes' else ck.deselect()
            ck.grid(row=row, column=col)
            checkboxes.append(ck)
            self.checkboxvars.append(var)
            Label(self, text=q, wraplength=300, justify=LEFT).grid(row=row, column=col+1, sticky='W', columnspan=4)
            row+=1

        Label(self, text='QA Signoff: ').grid(row=row, column=col, sticky='W')
        col+=1

        self.reporterStr = StringVar()
        self.reporterStr.set(get_username())
        self.reporterEntry = Entry(self, textvar=self.reporterStr)
        self.reporterEntry.grid(row=row, column=col, columnspan=3, sticky='W')

        row+=1
        col-=1

        self.acceptButton = Button(self, text='Accept', command=lambda:self.qa_done('yes'), width=15, state=DISABLED)
        self.acceptButton.grid(row=row, column=col, columnspan=2, sticky='W')

        self.rejectButton = Button(self, text='Reject', command=lambda:self.qa_done('no'), width=15)
        self.rejectButton.grid(row=row, column=col+2, columnspan=2, sticky='W')

        row += 1
        self.descriptionLabel.grid(row=row, column=col-1)

        row +=1
        self.commentsLabel = Label(self, text='Comments: ')
        self.commentsLabel.grid(row=row, column=col-1, columnspan=5)
        row+=1
        textscroll = Scrollbar(self)
        textscroll.grid(row=row, column=col+5, sticky=NS)
        self.commentsBox = Text(self, height=5, width=100, yscrollcommand=textscroll.set)
        self.commentsBox.grid(row=row, column=col-1, padx=5, pady=5, columnspan=6, sticky=NSEW)
        textscroll.config(command=self.commentsBox.yview)
        currentComment = self.parent.scModel.getProjectData('qacomment')
        self.commentsBox.insert(END, currentComment) if currentComment is not None else ''

        self.check_ok()

    def composite_or_donor(self, initialize=False, event=None):
        self.name = self.parent.scModel.start
        self.master.scModel.selectImage(self.optionsBox.get())
        if self.optionsBox.get() in self.terminals:
            self.im = self.parent.scModel.startImage()
            self.composite = self.master.scModel.getComposite()
            self.descriptionLabel.config(text='Composite generated for node ' + self.optionsBox.get())
        elif self.optionsBox.get() in self.donors:
            self.composite, self.im = self.parent.scModel.getDonorAndBaseImages()
            self.descriptionLabel.config(text='Donor mask generated for node ' + self.optionsBox.get())
        else:
            return

        self.load_composite(initialize)

    def load_composite(self, initialize=False):
        compositeResized = imageResizeRelative(self.composite, (500, 500),self.composite.size)
        if self.im is not None:
            imResized = imageResizeRelative(self.im, (500, 500),self.im.size)
            imResized = imResized.overlay(compositeResized)
        else:
            imResized = compositeResized
        self.photo = ImageTk.PhotoImage(imResized.toPIL())
        if initialize is True:
            self.c = Canvas(self.cImgFrame, width=compositeResized.size[0]+10, height=compositeResized.size[1]+10)
            self.c.pack()
        self.image_on_canvas = self.c.create_image(0, 0, image=self.photo, anchor=NW, tag='imgc')


    def qa_done(self, qaState):
        self.parent.scModel.setProjectData('validation', qaState)
        self.parent.scModel.setProjectData('validatedby', self.reporterStr.get())
        self.parent.scModel.setProjectData('validationdate', time.strftime("%m/%d/%Y"))
        self.parent.scModel.setProjectData('qacomment', self.commentsBox.get(1.0, END))
        self.parent.scModel.save()

        self.destroy()

    def check_ok(self, event=None):
        turn_on_ok = True
        for b in self.checkboxvars:
            if b.get() is False or turn_on_ok is False:
                turn_on_ok = False

        if turn_on_ok is True:
            self.acceptButton.config(state=NORMAL)
        else:
            self.acceptButton.config(state=DISABLED)


class CommentViewer(tkSimpleDialog.Dialog):
    def __init__(self, master):
        self.master=master
        tkSimpleDialog.Dialog.__init__(self, master)

    def body(self, master):
        try:
            comment = self.master.scModel.getProjectData('qacomment')
            if comment == '':
                raise
        except:
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
        self.master.scModel.setProjectData('qacomment', '')
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


class SelectDialog(tkSimpleDialog.Dialog):
    cancelled = True

    def __init__(self, parent, name, description, values):
        self.description = description
        self.values = values
        self.parent = parent
        self.name = name
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        desc_lines = '\n'.join(self.description.split('.'))
        Label(master, text=desc_lines, wraplength=400).grid(row=0, sticky=W)
        self.var1 = StringVar()
        self.var1.set(self.values[0])
        self.e1 = OptionMenu(master, self.var1, *self.values)
        #self.e1 = AutocompleteEntryInText(master, values=self.values, takefocus=True)
        self.e1.grid(row=1, column=0,sticky=EW)
        self.lift()

    def cancel(self):
        if self.cancelled:
            self.choice = None
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.choice = self.var1.get()


class EntryDialog(tkSimpleDialog.Dialog):
    cancelled = True

    def __init__(self, parent, name, description, validateFunc, initialvalue=None):
        self.description = description
        self.validateFunc = validateFunc
        self.parent = parent
        self.name = name
        self.initialvalue = initialvalue
        tkSimpleDialog.Dialog.__init__(self, parent, name)

    def body(self, master):
        Label(master, text=self.description).grid(row=0, sticky=W)
        self.e1 = Entry(master, takefocus=True)
        if self.initialvalue:
            self.e1.insert(0, self.initialvalue)
        self.e1.grid(row=1, column=0)
        self.lift()

    def cancel(self):
        if self.cancelled:
            self.choice = None
        tkSimpleDialog.Dialog.cancel(self)

    def apply(self):
        self.cancelled = False
        self.choice = self.e1.get()

    def validate(self):
        v = self.e1.get()
        if self.validateFunc and not self.validateFunc(v):
            tkMessageBox.showwarning(
                "Bad input",
                "Illegal values, please try again"
            )
            return 0
        return 1


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
        Label(master, text="Final without rotation").grid(row=row, column=1, sticky=E + S + N)
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
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling

    """

    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())

        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())

        canvas.bind('<Configure>', _configure_canvas)

        return

def notifyCB(obj,name, type, row, cb,a1,a2,a3):
    if cb is not None:
        cb(name, type, obj.values[row].get())

class PropertyFrame(VerticalScrolledFrame):

   parent = None
   cancelled = True
   dir = '.'
   buttons = {}
   scModel = None
   propertyFunction = PropertyFunction()
   """
   @type scModel: ImageProjectModel
   """

   def __init__(self, parent, properties, propertyFunction=PropertyFunction(),scModel=None, dir='.',changeParameterCB=None, **kwargs):
     self.parent = parent
     self.properties = [prop for prop in properties if not prop.node]
     self.values =   [None for prop in properties]
     self.widgets =[None for prop in properties]
     self.changeParameterCB = changeParameterCB
     self.dir = dir
     self.propertyFunction = propertyFunction
     self.scModel = scModel
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
           if v:
               self.values[row].set(v)
           if prop.type == 'list':
               widget =  ttk.Combobox(master, values=prop.values, takefocus=(row == 0),textvariable=self.values[row])
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
           elif prop.type == 'yesno':
               widget = [None,None]
               widget[0]  =Radiobutton(master, text='Yes', takefocus=(row == 0), variable=self.values[row],
                               value='yes')
               widget[0].grid(row=row, column=1, sticky=W)
               #widget[0].deselect()
               widget[1] =  Radiobutton(master, text='No', takefocus=(row == 0), variable=self.values[row], value='no')
               widget[1].grid(row=row, column=2, sticky=E)
               #widget[1].select()
           elif prop.type == 'imagefile':
               partialf = partial(promptForFileAndFillButtonText, self, self.dir, prop.name, row, getFileTypes())
               self.buttons[prop.name] = widget = Button(master, text=v if v is not None else '              ', takefocus=False,
                                                command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type == 'xmpfile':
               partialf = partial(promptForFileAndFillButtonText, self, self.dir, prop.name, row, [('XMP', '*.xmp')])
               self.buttons[prop.name] = widget = Button(master, text=v if v is not None else '               ', takefocus=False,
                                                command=partialf)
               self.buttons[prop.name].grid(row=row, column=1, columnspan=8, sticky=E + W)
           elif prop.type.startswith('fileset:'):
               initialdir_parts = tuple(prop.type[8:].split('/'))
               initialdir = os.path.join(*tuple(initialdir_parts))
               partialf = partial(promptForFileAndFillButtonText, self, initialdir, prop.name, row, [('Text', '*.txt')])
               self.buttons[prop.name] = widget = Button(master, text=v if v is not None else '               ', takefocus=False,
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
           else:
               widget = Entry(master, takefocus=(row == 0), width=80,textvariable=self.values[row])
               widget.grid(row=row, column=1, columnspan=12, sticky=E + W)
           self.widgets[row] = widget
           if prop.readonly:
               if prop.type == 'yesno':
                   widget[0].config(state=DISABLED)
                   widget[1].config(state=DISABLED)
               else:
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

class PropertyDialog(tkSimpleDialog.Dialog):

   cancelled = False
   def __init__(self, parent, properties, scModel=None,title="Project Properties", dir='.'):
        self.properties =properties
        self.scModel = scModel
        self.dir=dir
        tkSimpleDialog.Dialog.__init__(self, parent, title)

   def body(self, master):
        self.vs = PropertyFrame(master, self.properties,
                           scModel=self.scModel,
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
    def __init__(self,properties):
        """
        :param scModel:
        @type scModel: ImageProjectModel
        """
        for prop in properties:
            self.lookup_values[prop.name] = prop.value

    def getValue(self, name):
        return self.lookup_values[name]

    def setValue(self, name,value):
        self.lookup_values[name] = value