import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg
from matplotlib.figure import Figure
from Tkinter import *
import ttk
import tkMessageBox
from group_filter import GroupFilterLoader
import tkFileDialog, tkSimpleDialog
from PIL import ImageTk
from autocomplete_it import AutocompleteEntryInText
from tool_set import imageResize, imageResizeRelative, openImage, fixTransparency, openImage, openFile, \
    validateTimeString, \
    validateCoordinates, getMaskFileTypes, getImageFileTypes, get_username, coordsFromString, IntObject, get_icon
from scenario_model import Modification, ImageProjectModel
from software_loader import Software, SoftwareLoader
import os
import thread
import numpy as np
from tkintertable import TableCanvas, TableModel
from image_wrap import ImageWrapper
from functools import partial
from group_filter import GroupOperationsLoader
from software_loader import ProjectProperty, getSemanticGroups
import sys
from collapsing_frame import Chord, Accordion
from PictureEditor import PictureEditor
from CompositeViewer import ScrollCompositeViewer


class QAViewDialog(Toplevel):
    lookup = {}

    def __init__(self, parent):
        """

        :param parent: MakeGenUI
        @type parent: MakeGenUI
        """
        self.parent = parent
        self.probes = self.parent.scModel.getProbeSetWithoutComposites(saveTargets=False)
        Toplevel.__init__(self, parent)
        # self.complete = True if self.parent.scModel.getProjectData('validation') == 'yes' else False
        self.createWidgets()
        self.resizable(width=False, height=False)

    def getFileNameForNode(self, nodeid):
        fn = self.parent.scModel.getFileName(nodeid)
        self.lookup[fn] = nodeid
        return fn

    def createWidgets(self):
        row = 0
        col = 0
        self.validateButton = Button(self, text='Check Validation', command=self.parent.validate, width=50)
        self.validateButton.grid(row=row, column=col, padx=10, columnspan=5, sticky='EW')
        row = 1
        col = 1
        self.optionsLabel = Label(self,
                                  text='Select terminal node to view composite, or PasteSplice node to view donor mask: ')
        self.optionsLabel.grid(row=row, columnspan=5)
        row += 1
        self.crit_links = ['->'.join([self.getFileNameForNode(p.edgeId[1]), self.getFileNameForNode(p.finalNodeId)]) for
                           p in self.probes] if self.probes else []
        donors = ['<-'.join([self.getFileNameForNode(p.edgeId[1]), self.getFileNameForNode(p.donorBaseNodeId)]) for p in
                  self.probes if p.donorMaskImage is not None] if self.probes else []
        donors = set(sorted(donors))
        self.crit_links.extend([x for x in donors])
        self.optionsBox = ttk.Combobox(self, values=self.crit_links)
        if self.crit_links:
            self.optionsBox.set(self.crit_links[0])
        self.optionsBox.grid(row=row, columnspan=6, sticky='EW', padx=10)
        self.optionsBox.bind("<<ComboboxSelected>>", self.load_overlay)
        row += 1
        self.operationVar = StringVar()
        self.operationLabel = Label(self, textvariable=self.operationVar, justify=LEFT)
        self.operationLabel.grid(row=row, column=0, columnspan=1, sticky='EW', padx=10)
        row += 1
        self.optionsLabel.grid(row=row, columnspan=5)
        self.cImgFrame = Frame(self)
        self.cImgFrame.grid(row=row, rowspan=8)
        self.descriptionLabel = Label(self)

        # only load the overlay if there are blue links
        if self.crit_links:
            self.load_overlay(initialize=True)

        col = 1

        self.infolabel = Label(self, justify=LEFT, text='QA Checklist:').grid(row=row, column=col)
        row += 1

        qa_list = [
            'Input masks are provided where possible, especially for any operation where pixels were directly taken from one region to another (e.g. PasteSampled)',
            'PasteSplice operations should include resizing, rotating, positioning, and cropping of the pasted object in their arguments as one operation. \n -For example, there should not be a PasteSplice followed by a TransformRotate of the pasted object.',
            'Base and terminal node images should be the same format.\n -If the base was a JPEG, the Create JPEG/TIFF option should be used as the last step.',
            'Verify that all relevant local changes are accurately represented in the composite and donor mask image(s), which can be easily viewed to the left.',
            'All relevant semantic groups are identified.',
            'End nodes are renamed to their MD5 value (Process->Rename Final Images).']
        checkboxes = []
        self.checkboxvars = []
        for q in qa_list:
            var = BooleanVar()
            ck = Checkbutton(self, variable=var, command=self.check_ok)
            ck.select() if self.parent.scModel.getProjectData('validation') == 'yes' else ck.deselect()
            ck.grid(row=row, column=col)
            checkboxes.append(ck)
            self.checkboxvars.append(var)
            Label(self, text=q, wraplength=300, justify=LEFT).grid(row=row, column=col + 1,
                                                                   sticky='EW')  # , columnspan=4)
            row += 1

        Label(self, text='QA Signoff: ').grid(row=row, column=col, sticky='W')
        col += 1

        self.reporterStr = StringVar()
        self.reporterStr.set(get_username())
        self.reporterEntry = Entry(self, textvar=self.reporterStr)
        self.reporterEntry.grid(row=row, column=col, columnspan=3, sticky='W')

        row += 1
        col -= 1

        self.acceptButton = Button(self, text='Accept', command=lambda: self.qa_done('yes'), width=15, state=DISABLED)
        self.acceptButton.grid(row=row, column=col, columnspan=2, sticky='W')

        self.rejectButton = Button(self, text='Reject', command=lambda: self.qa_done('no'), width=15)
        self.rejectButton.grid(row=row, column=col + 2, columnspan=2, sticky='W')

        row += 1
        self.descriptionLabel.grid(row=row, column=col - 1)

        row += 1
        self.commentsLabel = Label(self, text='Comments: ')
        self.commentsLabel.grid(row=row, column=col - 1, columnspan=5)
        row += 1
        textscroll = Scrollbar(self)
        textscroll.grid(row=row, column=col + 5, sticky=NS)
        self.commentsBox = Text(self, height=5, width=100, yscrollcommand=textscroll.set)
        self.commentsBox.grid(row=row, column=col - 1, padx=5, pady=5, columnspan=6, sticky=NSEW)
        textscroll.config(command=self.commentsBox.yview)
        currentComment = self.parent.scModel.getProjectData('qacomment')
        self.commentsBox.insert(END, currentComment) if currentComment is not None else ''

        self.check_ok()

    def _compose_label(self, edge):
        op = edge['op']
        if 'semanticGroups' in edge and edge['semanticGroups'] is not None:
            groups = edge['semanticGroups']
            op += ' [' + ', '.join(groups) + ']'
        return op

    def load_overlay(self, initialize=False):
        edgeTuple = tuple(self.optionsBox.get().split('->'))
        if len(edgeTuple) > 1:
            probe = [probe for probe in self.probes if
                     probe.edgeId[1] == self.lookup[edgeTuple[0]] and probe.finalNodeId == self.lookup[edgeTuple[1]]][0]
            n = self.parent.scModel.G.get_node(probe.finalNodeId)
            finalFile = os.path.join(self.parent.scModel.G.dir,
                                     self.parent.scModel.G.get_node(probe.finalNodeId)['file'])
            final = openImage(finalFile)
            finalResized = imageResizeRelative(final, (500, 500), final.size)
            imResized = imageResizeRelative(probe.targetMaskImage, (500, 500),
                                            probe.targetMaskImage.size if probe.targetMaskImage is not None else finalResized.size)
        else:
            edgeTuple = tuple(self.optionsBox.get().split('<-'))
            probe = \
                [probe for probe in self.probes if
                 probe.edgeId[1] == self.lookup[edgeTuple[0]] and probe.donorBaseNodeId == self.lookup[edgeTuple[1]]][0]
            n = self.parent.scModel.G.get_node(probe.donorBaseNodeId)
            finalFile = os.path.join(self.parent.scModel.G.dir,
                                     self.parent.scModel.G.get_node(probe.donorBaseNodeId)['file'])
            final = openImage(finalFile)
            finalResized = imageResizeRelative(final, (500, 500), final.size)
            imResized = imageResizeRelative(probe.donorMaskImage, (500, 500),
                                            probe.donorMaskImage.size if probe.donorMaskImage is not None else finalResized.size)
        edge = self.parent.scModel.getGraph().get_edge(probe.edgeId[0], probe.edgeId[1])
        self.operationVar.set(self._compose_label(edge))
        finalResized = finalResized.overlay(imResized)
        self.photo = ImageTk.PhotoImage(finalResized.toPIL())
        if initialize is True:
            self.c = Canvas(self.cImgFrame, width=510, height=510)
            self.c.pack()
        self.image_on_canvas = self.c.create_image(0, 0, image=self.photo, anchor=NW, tag='imgc')

    def qa_done(self, qaState):
        self.parent.scModel.set_validation_properties(qaState, self.reporterStr.get(), self.commentsBox.get(1.0, END))
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

class QAProjectDialog(Toplevel):

    lookup = {}
    def __init__(self, parent):
        self.parent = parent
        self.scModel = parent.scModel
        self.type = self.parent.scModel.getEndType()
        print('Stalled?')
        self.probes = self.parent.scModel.getProbeSetWithoutComposites(saveTargets=False)
        print("Done")
        Toplevel.__init__(self, parent)
        self.type = self.parent.scModel.getEndType()
        self.checkboxvars = []
        self.backs = {}
        self.subplots ={}
        self.pltdata = {}
        self.backsProbes={}
        self.photos = {}
        self.createWidgets()
        self.resizable(width=False, height=False)


    def getFileNameForNode(self, nodeid):
        fn = self.parent.scModel.getFileName(nodeid)
        self.lookup[fn] = nodeid
        return fn

    def pre(self):
        self.move(-1)

    def nex(self):
        self.move(+1)

    def exitProgram(self):
        self.destroy()

    def createWidgets(self):
        page1 = Frame(self)
        page1.grid()
        self.cur = page1
        lbl = Label(page1, text="Welcome to the QA Wizard Press Next to begin the QA Process or Quit to stop",wraplength=200).grid(column=0,row=0,rowspan=2,columnspan=2)
        wquit = Button(page1, text='Quit', command=self.exitProgram).grid(column=0,row=2,sticky=W)
        wnext = Button(page1, text = 'Next', command=self.nex).grid(column = 1,row=2,sticky = E)
        self.pages = []
        self.pages.append(page1)
        self.crit_links = ['->'.join([self.getFileNameForNode(p.edgeId[1]), self.getFileNameForNode(p.finalNodeId)]) for
                           p in self.probes] if self.probes else []
        self.crit_links = list(set(self.crit_links))

        self.finNodes = []
        for x in range(0,len(self.crit_links)):
            for y in range(x,len(self.crit_links)):
                link1 = self.crit_links[x]
                link2 = self.crit_links[y]
                fin1 = link1.split("->")[1]
                fin2 = link2.split("->")[1]
                self.finNodes.append(fin2)
                if (fin1>fin2):
                    self.crit_links[x] = self.crit_links[y]
                    self.crit_links[y] = link1
        self.finNodes = list(set(self.finNodes))

        for end in self.finNodes:
            n = self.lookup[end]
            self.backs[end] = []
            next = self.getPredNode(n)
            while next != None:
                n = next.start
                self.backs[end].append(next)
                next = self.getPredNode(n)
            #print(len(self.backs[end]))
            self.backs[end].reverse()

        if (self.type =='image'):
            donors = ['<-'.join([self.getFileNameForNode(p.edgeId[1]), self.getFileNameForNode(p.donorBaseNodeId)]) for p in
                  self.probes if p.donorMaskImage is not None] if self.probes else []
        else:
            donors = ['<-'.join([self.getFileNameForNode(p.edgeId[1]), self.getFileNameForNode(p.donorBaseNodeId)]) for p in
                      self.probes if p.donorVideoSegments is not None] if self.probes else []
        donors = set(sorted(donors))
        self.crit_links.extend([x for x in donors])
        for link in self.crit_links:
            page = Frame(self)
            self.cur = page

            self.createImagePage(link,page)
            self.pages.append(page)


        row = 0
        col = 0
        lastpage = Frame(self)
        self.validateButton = Button(lastpage, text='Check Validation', command=self.parent.validate, width=50)
        self.validateButton.grid(row=row, column=col, padx=10, columnspan=3, sticky='EW')
        row += 1
        self.infolabel = Label(lastpage, justify=LEFT, text='QA Checklist:').grid(row=row, column=col)
        row += 1

        qa_list = [
            'Base and terminal node images should be the same format. -If the base was a JPEG, the Create JPEG/TIFF option should be used as the last step.',
            'All relevant semantic groups are identified.',
            'End nodes are renamed to their MD5 value (Process->Rename Final Images).']
        checkboxes = []
        #self.checkboxvars = []
        for q in qa_list:
            var = BooleanVar()
            ck = Checkbutton(lastpage, variable=var, command=self.check_ok)
            ck.select() if self.parent.scModel.getProjectData('validation') == 'yes' else ck.deselect()
            ck.grid(row=row, column=col)
            checkboxes.append(ck)
            self.checkboxvars.append(var)
            Label(lastpage, text=q, wraplength=600, justify=LEFT).grid(row=row, column=col + 1,
                                                                   sticky='W')  # , columnspan=4)
            row += 1

        Label(lastpage, text='QA Signoff: ').grid(row=row, column=col)
        col += 1
        self.reporterStr = StringVar()
        self.reporterStr.set(get_username())
        self.reporterEntry = Entry(lastpage, textvar=self.reporterStr)
        self.reporterEntry.grid(row=row, column=col, columnspan=3, sticky='W')
        row += 2
        col -= 1
        self.acceptButton = Button(lastpage, text='Accept', command=lambda: self.qa_done('yes'), width=15, state=DISABLED)
        self.acceptButton.grid(row=row, column=col+2, columnspan=2, sticky='W')

        self.rejectButton = Button(lastpage, text='Previous', command=self.pre, width=15)
        self.rejectButton.grid(row=row, column=col, columnspan=2, sticky='W')

        row += 1
        # self.descriptionLabel.grid(row=row, column=col - 1)

        row += 1
        self.commentsLabel = Label(lastpage, text='Comments: ')
        self.commentsLabel.grid(row=row, column=col, columnspan=3)
        row += 1
        textscroll = Scrollbar(lastpage)
        textscroll.grid(row=row, column=col + 4, sticky=NS)
        self.commentsBox = Text(lastpage, height=5, width=100, yscrollcommand=textscroll.set)
        self.commentsBox.grid(row=row, column=col, padx=5, pady=5, columnspan=3, sticky=NSEW)
        textscroll.config(command=self.commentsBox.yview)
        currentComment = self.parent.scModel.getProjectData('qacomment')
        self.commentsBox.insert(END, currentComment) if currentComment is not None else ''

        self.check_ok()
        self.pages.append(lastpage)
        self.cur=page1
        #print(len(self.pages))
        #print(len(self.photos))
        #print(len(self.crit_links))


    def createVideoPage(self, t, p):
        self.t = t
        self.edgeTuple = tuple(t.split("<-"))
        if (len(self.edgeTuple))< 2:
            self.edgeTuple = tuple(t.split("->"))
            self.finalNodeName = self.edgeTuple[0]
        else:
            self.finalNodeName=None
        row = 0
        col = 0
        self.optionsLabel = Label(p, text=t)
        self.optionsLabel.grid(row=row, columnspan=3, sticky='EW', padx=10)
        row += 1
        self.operationVar = StringVar()
        self.operationLabel = Label(p, textvariable=self.operationVar, justify=LEFT)
        self.pltFrame = Frame(p)
        self.setUpPlot(self.t)
        row +=1
        self.pltFrame.grid(row = row, column = 0)
        row += 1
        self.acceptButton = Button(p, text='Next', command=self.nex, width=15)
        self.acceptButton.grid(row=11, column=col + 2, columnspan=2, sticky='E')
        self.prevButton = Button(p, text='Previous', command=self.pre, width=15)
        self.prevButton.grid(row=11, column=col, columnspan=2, sticky='W')


    def abreive(self,str):
        if (len(str)>10):
            return(str[:5]+ "...\n" + str[-6:])

    def setUpPlot(self,t):
        data = []
        f = Figure(figsize=(6,4), dpi=100)
        subplot = f.add_subplot(111)
        self.subplots[self.cur] = f
        prolist = []
        for p in self.probes:
            if (self.finalNodeName == None):
                if self.getFileNameForNode(p.donorBaseNodeId) == self.edgeTuple[1]:
                    prolist.append(p)
            else:
                if (self.getFileNameForNode(p.finalNodeId) == self.edgeTuple[1]):
                    prolist.append(p)
        ts = (self.scModel.G.get_node(self.lookup[self.edgeTuple[1]])['duration'])
        ftr = [3600, 60, 1]

        tsec = sum([a * b for a, b in zip(ftr, map(float, ts.split(':')))])
        ytics = []
        ytic_lbl = []
        count = 0
        high = 0
        low = tsec*1000+20000
        for p in prolist:
            count += 1
            col = 2
            cur = False
            if (self.lookup[self.edgeTuple[0]] == p.edgeId[1]):
                col = 1
                cur = True
            if self.finalNodeName == None:
                for mvs in p.donorVideoSegments:
                    data.append([count,col,mvs.starttime,mvs.endtime])
                    if cur:
                        high = max(high,mvs.endtime)
                        low = min(low,mvs.starttime)
            else:
                for mvs in p.targetVideoSegments:
                    data.append([count,col,mvs.starttime,mvs.endtime])
                    if cur:
                        high = max(high,mvs.endtime)
                        low = min(low,mvs.starttime)
            ytics.append(count)
            ytic_lbl.append(self.abreive(p.edgeId[0]))

        color_mapper = np.vectorize(lambda x: {0: 'red', 1: 'blue', 2: 'green'}.get(x))
        data.append([count+1,0,0.0,tsec*1000.0])
        ytics.append(count+1)
        ytic_lbl.append(self.abreive(self.edgeTuple[1]))
        na = np.array(data)
        subplot.hlines(na[:,0],na[:,2],na[:,3],color_mapper(na[:,1]),linewidth=10)
        subplot.set_yticks(ytics)
        subplot.set_yticklabels(ytic_lbl)
        subplot.set_xlabel('Time in Milliseconds')
        subplot.grid()
        i = subplot.yaxis.get_view_interval()
        if (i[1]-i[0]<10):
            i[0]= i[1]-8
            subplot.yaxis.set_view_interval(i[0],i[1])
        i = subplot.xaxis.get_view_interval()
        if (i[1]-i[0]>2000):
            i[0] = low - 1000
            i[1] = high + 1000
            subplot.xaxis.set_view_interval(i[0],i[1])
        self.pltdata[self.cur] = na
        canvas = Canvas(self.cImgFrame,height=50,width=50)
        canvas.grid(row = 0,column=0)
        imscroll = Scrollbar(self.cImgFrame, orient=HORIZONTAL)
        imscroll.grid(row =1,column=0,sticky=EW)
        imscroll.config(command=self.scrollplt)
        fcanvas = FigureCanvasTkAgg(f, master=canvas)
        #toolbar = NavigationToolbar2TkAgg(fcanvas, self)
        fcanvas.show()
        fcanvas.get_tk_widget().grid(row=0,column=0)
        fcanvas._tkcanvas.grid(row=0, column=0)
        canvas.config(height=50,width=50)



    def scrollplt(self, *args):
        if (args[0] == 'moveto'):
            #i = self.subplots[self.cur].xaxis.get_view_interval()
            ib = self.subplots[self.cur].subplots().get_xbound()
            ih = ib[1]*float(args[1])
            il = ih - 2000
            self.subplots[self.cur].subplots().xaxis.set_view_interval(il,ih)
            self.subplots[self.cur].canvas.hide()
        elif (args[0] == 'scroll'):
            na = self.pltdata[self.cur]
            self.subplots[self.cur].subplots().xaxis.pan(int(args[1])*100)
            i = self.subplots[self.cur].subplots().xaxis.get_view_interval()
            self.subplots[self.cur].subplots().hlines(na[:,0],na[:,2],na[:,3],np.vectorize(lambda x: {0: 'red', 1: 'blue', 2: 'green'}.get(x))(na[:,1]),linewidth=10)
            self.subplots[self.cur].subplots().xaxis.set_view_interval(i[0],i[1])
            self.subplots[self.cur].canvas.draw()
            self.subplots[self.cur].canvas.flush_events()


        print('done')

    def createImagePage(self, t, p):
        self.t = t
        self.edgeTuple = tuple(t.split("<-"))
        if len(self.edgeTuple) < 2:
            self.finalNodeName = t.split("->")[1]
            self.edgeTuple = tuple(t.split("->"))
        else:
            self.finalNodeName = None
        row = 0
        col = 0
        self.optionsLabel = Label(p, text=t)
        self.optionsLabel.grid(row=row, columnspan=3, sticky='EW', padx=10)
        row += 1
        self.operationVar = StringVar()
        self.operationLabel = Label(p, textvariable=self.operationVar, justify=LEFT)
        row += 1
        self.operationLabel.grid(row=row, columnspan=3, sticky='EW', padx=10)
        row += 1
        self.cImgFrame = Frame(p)
        # self.load_overlay(initialize= True)
        self.cImgFrame.grid(row=row, rowspan=8)
        self.descriptionVar = StringVar()
        self.descriptionLabel = Label(p, textvariable=self.operationVar, justify=LEFT)
        row += 8
        textscroll = Scrollbar(p)
        textscroll.grid(row=row, column=col + 1, sticky=NS)
        self.commentBox = Text(p, height=5, width=80, yscrollcommand=textscroll.set)
        self.commentBox.grid(row=row, column=col, padx=5, pady=5, columnspan=1, sticky=NSEW)
        textscroll.config(command=self.commentBox.yview)
        col = 3
        row = 0
        scroll = Scrollbar(p)
        scroll.grid(row=row, column=col + 2, rowspan=5, columnspan=1,sticky=NS)
        # self.scrollh = Scrollbar(self, orient=HORIZONTAL)
        # self.scrollh.grid(row=row + 5, column=col,sticky= EW)
        self.pathList = Listbox(p, width=30, yscrollcommand=scroll.set)
        self.pathList.grid(row=row, column=col-1, rowspan=5, columnspan=3)
        scroll.config(command=self.pathList.yview)
        self.transitionVar = StringVar()
        # self.pathText = Text(self, width=100, height=100,yscrollcommand=self.scroll.set)
        # self.pathText.setvar(self, self.transitionVar)
        # self.pathText.grid(row = row, column = col, rowspan = 5)
        #self.checkVars = []
        if (len(t.split('->'))>1):
            probe = [probe for probe in self.probes if
                 probe.edgeId[1] == self.lookup[self.edgeTuple[0]] and probe.finalNodeId == self.lookup[self.edgeTuple[1]]][0]
        else:
            probe = \
            [probe for probe in self.probes if
             probe.edgeId[1] == self.lookup[self.edgeTuple[0]] and probe.donorBaseNodeId ==
             self.lookup[
                 self.edgeTuple[1]]][0]
        edge = self.scModel.getGraph().get_edge(probe.edgeId[0], probe.edgeId[1])
        print (edge['op'])
        operation = self.scModel.getGroupOperationLoader().getOperationWithGroups(edge['op'])
        if self.type == 'image':
            self.loadt()
        else:
            self.setUpPlot(t)
            self.transitionString(None)
        #thread.start_new_thread(self.loadt, ())
        try:
            self.curOpList = operation.qalist
        except AttributeError:
            print("No QAList Found")
            self.curOpList = []
        if (self.curOpList == None):
            self.curOpList = []
        row += 5
        checkboxes = []
        #self.checkboxvars = []
        for q in self.curOpList:
            var = BooleanVar()
            ck = Checkbutton(p, variable=var, command=self.check_ok)
            ck.select() if self.scModel.getProjectData('validation') == 'yes' else ck.deselect()
            ck.grid(row=row, column=col-1)
            checkboxes.append(ck)
            self.checkboxvars.append(var)
            Label(p, text=q, wraplength=250, justify=LEFT).grid(row=row, column=col, columnspan=4,
                                                                   sticky='W')  # , columnspan=4)
            row += 1
        self.acceptButton = Button(p, text='Next', command=self.nex, width=15)
        self.acceptButton.grid(row=11, column=col+2, columnspan=2, sticky='E')
        self.prevButton = Button(p, text='Previous', command=self.pre, width=15)
        self.prevButton.grid(row=11, column=col, columnspan=2, sticky='W')




    def transitionString(self, probeList):
        tab = "     "

        if self.finalNodeName == None:
            self.pathList.insert(END, self.edgeTuple[1]  )
            self.pathList.insert(END, 2*tab + "|")
            self.pathList.insert(END, tab + "Donor")
            self.pathList.insert(END, 2*tab + "|")
            self.pathList.insert(END, 2*tab + "V")
            self.pathList.insert(END, self.edgeTuple[0])
            return self.edgeTuple[0] + "\n|\nPasteSplice\n|\nV\n" + self.edgeTuple[1]
        self.pathList.insert(END,self.getFileNameForNode( self.backs[self.finalNodeName][0].start)[0:15]+"...")
        self.pathList.insert(END, tab + self.getFileNameForNode(self.backs[self.finalNodeName][0].start)[-10:])
        for p in self.backs[self.finalNodeName]:
            edge = self.scModel.getGraph().get_edge(p.start, p.end)
            self.pathList.insert(END, 2 * tab + "|")
            self.pathList.insert(END, tab + edge['op'])
            self.pathList.insert(END, 2 * tab + "|")
            self.pathList.insert(END, 2 * tab + "V")
            self.pathList.insert(END, self.getFileNameForNode(p.end)[0:15]+ "...")
            self.pathList.insert(END, tab + self.getFileNameForNode(p.end)[-10:])
            str = ""
        return str


    def _compose_label(self,edge):
        op  = edge['op']
        if 'semanticGroups' in edge and edge['semanticGroups'] is not None:
            groups = edge['semanticGroups']
            op += ' [' + ', '.join(groups) + ']'
        self.descriptionVar = edge['description']
        return op

    def loadt(self):
        self.load_overlay(True)

    def load_overlay(self, initialize):

        edgeTuple = self.edgeTuple
        if (len(self.t.split('->')) > 1):
            probe = [probe for probe in self.probes if
                     probe.edgeId[1] == self.lookup[self.edgeTuple[0]] and probe.finalNodeId == self.lookup[
                         self.edgeTuple[1]]][0]
            n = self.parent.scModel.G.get_node(probe.finalNodeId)
            finalFile = os.path.join(self.parent.scModel.G.dir,
                                     self.parent.scModel.G.get_node(probe.finalNodeId)['file'])
            final = openImage(finalFile)
            finalResized = imageResizeRelative(final, (500, 500), final.size)
            imResized = imageResizeRelative(probe.targetMaskImage, (500, 500),
                                            probe.targetMaskImage.size if probe.targetMaskImage is not None else finalResized.size)
        else:
            probe = \
        [probe for probe in self.probes if probe.edgeId[1] == self.lookup[edgeTuple[0]] and probe.donorBaseNodeId == self.lookup[edgeTuple[1]]][0]
            n = self.scModel.G.get_node(probe.donorBaseNodeId)
            finalFile = os.path.join(self.scModel.G.dir,
                                 self.scModel.G.get_node(probe.donorBaseNodeId)['file'])
            final = openImage(finalFile)
            finalResized = imageResizeRelative(final, (500, 500), final.size)
            imResized = imageResizeRelative(probe.donorMaskImage, (500, 500),
                                        probe.donorMaskImage.size if probe.donorMaskImage is not None else finalResized.size)
        edge = self.scModel.getGraph().get_edge(probe.edgeId[0],probe.edgeId[1])
        self.operationVar.set(self._compose_label(edge))
        self.transitionString(None)
        finalResized = finalResized.overlay(imResized)
        self.photos[self.t] = ImageTk.PhotoImage(finalResized.toPIL())
        if initialize is True:
            self.c = Canvas(self.cImgFrame, width=510, height=510)
            self.c.pack()
        self.image_on_canvas = self.c.create_image(0, 0, image=self.photos[self.t], anchor=NW, tag='imgc')


    def move(self, dir):
        #print(len(self.pages))
        #print(self.cur)
        i = self.pages.index(self.cur) + dir
        if not 0<=i<len(self.pages):
            return
        self.cur.grid_forget()
        self.cur = self.pages[i]
        self.cur.grid()

    def qa_done(self, qaState):
        self.parent.scModel.set_validation_properties(qaState, self.reporterStr.get(), self.commentsBox.get(1.0, END))
        self.parent.scModel.save()
        self.destroy()

    def getPredNode(self,node):
        for pred in self.scModel.G.predecessors(node):
            for pred in self.scModel.G.predecessors(node):
                edge = self.scModel.G.get_edge(pred, node)
                if edge['op'] != 'Donor':
                    return self.scModel.getModificationForEdge(pred, node, edge)
        return None

    def check_ok(self, event=None):
        turn_on_ok = True
        for b in self.checkboxvars:
            if b.get() is False or turn_on_ok is False:
                turn_on_ok = False

        if turn_on_ok is True:
            self.acceptButton.config(state=NORMAL)
        else:
            self.acceptButton.config(state=DISABLED)




class VideoQADialog(Toplevel):
    pass
