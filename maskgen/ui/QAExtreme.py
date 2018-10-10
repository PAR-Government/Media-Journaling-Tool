import matplotlib
from maskgen.maskgen_loader import MaskGenLoader
from maskgen.ui.semantic_frame import SemanticFrame
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

matplotlib.use("TkAgg")
import logging
from matplotlib.figure import Figure
from Tkinter import *
import matplotlib.patches as mpatches
import ttk
import tkMessageBox
from PIL import ImageTk
from maskgen.support import getValue
from maskgen.tool_set import imageResizeRelative, openImage,get_username
import os
import numpy as np
import maskgen.qa_logic
from maskgen.video_tools import getMaskSetForEntireVideo, get_end_time_from_segment
import maskgen.tool_set
import random
import maskgen.scenario_model
import maskgen.validation
from maskgen.ui.description_dialog import MaskSetTable
import webbrowser
from maskgen.mask_rules import compositeMaskSetFromVideoSegment
from maskgen.graph_meta_tools import MetaDataExtractor

class QAProjectDialog(Toplevel):

    lookup = {}
    def __init__(self, parent):
        self.valid = False
        self.colors = [[155,0,0],[0,155,0],[0,0,155],[153,76,0],[96,96,96],[204,204,0],[160,160,160]]
        self.parent = parent
        self.scModel = parent.scModel
        self.meta_extractor = MetaDataExtractor(parent.scModel.getGraph())
        self.probes = None
        Toplevel.__init__(self, parent)
        self.type = self.parent.scModel.getEndType()
        self.checkboxvars = {}
        self.backs = {}
        self.subplots ={}
        self.pltdata = {}
        self.backsProbes={}
        self.photos = {}
        self.commentsBoxes = {}
        self.edges = {}
        self.qaList = []
        self.pathboxes = {}
        self.qaData = maskgen.qa_logic.ValidationData(self.scModel)
        self.resizable(width=False, height=False)

        self.progressBars = []
        self.narnia = {}
        self.pageDisplays = {}

        self.createWidgets()


    def getProbes(self):
        try:
            self.probes = self.parent.scModel.getProbeSetWithoutComposites(saveTargets=False,keepFailures=True)
        except Exception as e:
            logging.getLogger('maskgen').error(str(e))
            self.probes = None

    def getFileNameForNode(self, nodeid):
        try:
            fn = self.scModel.getFileName(nodeid)
            if fn not in self.lookup:
                self.lookup[fn] = []
            if nodeid not in  self.lookup[fn]:
                self.lookup[fn].append(nodeid)
        except TypeError:
            fn = None
            logging.getLogger('maskgen').warn("Unable to locate File for node with Id {}".format(nodeid))
        return fn

    def pre(self):
        self.move(-1,False)

    def nex(self):
        self.move(1, False)

    def exitProgram(self):
        self.destroy()

    def help(self,event):
        URL = MaskGenLoader.get_key("apiurl")[:-3] + "journal"
        webbrowser.open_new(URL)

    def createWidgets(self):
        page1 = Frame(self)
        page1.grid()
        self.cur = page1
        statusLabelText = StringVar()
        statusLabelText.set('Probes Generating')
        Label(page1, text="Welcome to the QA Wizard. Press Next to begin the QA Process or Quit to stop. This is "
                                "Manny; He is here to help you analyze the journal. The tool is currently generating the probes. "
                                "This could take a while. When the next button is enabled you may begin.", wraplength=400).grid(column=0,row=0,\
                                                                                                rowspan=2,columnspan=2)
        filename = maskgen.tool_set.get_icon('Manny_icon_color.jpg')
        filenamecol = maskgen.tool_set.get_icon('Manny_icon_mask.jpg')
        manFrame = Frame(page1)
        manFrame.grid(column=0,row=2,columnspan=2)
        c = Canvas(manFrame, width=510, height=510)
        c.pack()
        img = openImage(filename)
        imgm = openImage(filenamecol).to_mask()
        imgm = imageResizeRelative(imgm, (500,500), imgm.size)
        self.manny = ImageTk.PhotoImage(imageResizeRelative(img, (500,500), img.size).overlay(imgm, self.colors[random.randint(0, len(self.colors) - 1)]).toPIL())
        self.image_on_canvas = c.create_image(510/2,510/2, image=self.manny, anchor=CENTER, tag='things')
        Label(page1,textvariable=statusLabelText).grid(column=0,row=3,columnspan=2,sticky=E+W)
        c.bind("<Double-Button-1>", self.help)
        wquit = Button(page1, text='Quit', command=self.exitProgram, width=20).grid(column=0,row=4,sticky=W, padx=5, pady=5)
        wnext = Button(page1, text = 'Next', command=self.nex,state=DISABLED,width=20)
        wnext.grid(column = 1,row=4,sticky = E,padx=5,pady=5)
        self.parent.update()
        self.getProbes()
        if self.probes is None:
            statusLabelText.set('Probe Generation failed.  Please consult logs for more details.')
            self.parent.update()
        else:
            self.errors = [p for p in self.probes if p.failure]
            if len(self.errors) > 0:
                statusLabelText.set('Probes Complete with errors. Generating Preview Pages.')
            else:
                statusLabelText.set('Probes Complete. Generating Preview Pages.')
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
                for n in self.lookup[end]:
                    if n in self.scModel.finalNodes():
                        break
                self.backs[end] = []
                next = self.getPredNode(n)
                while next != None:
                    n = next.start
                    self.backs[end].append(next)
                    next = self.getPredNode(n)
                self.backs[end].reverse()

            donors = ['<-'.join([self.getFileNameForNode(p.edgeId[1]), self.getFileNameForNode(p.donorBaseNodeId)]) for p in
                      self.probes if p.donorMaskImage is not None or p.donorVideoSegments is not None] if self.probes else []
            donors = set(sorted(donors))
            self.crit_links.extend([x for x in donors])
            count = 0.0
            for k in self.qaData.keys():
                count += 1 if self.qaData.get_qalink_status(k) == 'yes' else 0
            self.progress = count / len(self.crit_links) if len(self.crit_links) != 0 else 0.99999
            count= 1
            for link in self.crit_links:
                page = Frame(self)
                self.cur = page
                self.createImagePage(link,page)
                self.pages.append(page)
                count += 1


            row = 0
            col = 0
            lastpage = Frame(self)
            self.cur = lastpage
            self.infolabel = Label(lastpage, justify=LEFT, text='QA Checklist:').grid(row=row, column=col)
            row += 1
            qa_list = [
                'Base and terminal node images should be the same format. -If the base was a JPEG, the Create JPEG/TIFF option should be used as the last step.',
                'All relevant semantic groups are identified.']
            checkboxes = []

            self.checkboxvars[self.cur] = []
            for q in qa_list:
                var = BooleanVar()
                ck = Checkbutton(lastpage, variable=var, command=self.check_ok)
                ck.select() if self.parent.scModel.getProjectData('validation') == 'yes' else ck.deselect()
                ck.grid(row=row, column=col)
                checkboxes.append(ck)
                self.checkboxvars[self.cur].append(var)
                Label(lastpage, text=q, wraplength=600, justify=LEFT).grid(row=row, column=col + 1,
                                                                       sticky='W')
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
            self.rejectButton = Button(lastpage, text='Reject', command=lambda: self.qa_done('no'), width=15)
            self.rejectButton.grid(row=row, column=col+1, columnspan=1, sticky='E')
            self.previButton = Button(lastpage, text='Previous', command=self.pre, width=15)
            self.previButton.grid(row=row, column=col, columnspan=2, sticky='W')

            row += 1
            self.commentsLabel = Label(lastpage, text='Comments: ')
            self.commentsLabel.grid(row=row, column=col, columnspan=3)
            row += 1
            textscroll = Scrollbar(lastpage)
            textscroll.grid(row=row, column=col + 4, sticky=NS)
            self.commentsBox = Text(lastpage, height=5, width=100, yscrollcommand=textscroll.set,relief=SUNKEN)
            self.commentsBox.grid(row=row, column=col, padx=5, pady=5, columnspan=3, sticky=NSEW)
            textscroll.config(command=self.commentsBox.yview)
            currentComment = self.parent.scModel.getProjectData('qacomment')
            self.commentsBox.insert(END, currentComment) if currentComment is not None else ''
            row+=1
            pb = ttk.Progressbar(lastpage, orient='horizontal', mode='determinate', maximum=100.001)
            pb.grid(row=row, column=0, sticky=EW, columnspan=8)
            pb.step(self.progress*100)
            self.progressBars.append(pb)
            self.check_ok()
            self.pages.append(lastpage)
            self.cur=page1
            statusLabelText.set('Preview Pages Complete. Press Next to Continue.')
            wnext.config(state=NORMAL)


    def validategoodtimes(self):
        v = self.scModel.validate()
        if maskgen.validation.core.hasErrorMessages(v, lambda x: True):
            self.valid = False
            tkMessageBox.showerror("Validation Errors!","It seems this journal has unresolved validation errors. "
                                    "Please address these and try again. Your QA progress will be saved.")
        else:
            self.valid = True
        self.check_ok()

    def createVideoPage(self, t, p):
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
        self.setUpPlot(t)
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
        else:
            return str

    def setUpFrames(self,t):
        self.pageDisplays[self.cur] = [0,[]]
        self.setUpPlot(t)
        self.setUpMask(t)
        self.frameMove(0)
        nextButton = Button(self.cImgFrame, text='Next', command=self.frameNext, width=15)
        nextButton.grid(row=1, column=2, columnspan=2, sticky='E')
        prevButton = Button(self.cImgFrame, text='Previous', command=self.framePrev, width=15)
        prevButton.grid(row=1, column=0, columnspan=2, sticky='W')

    def frameNext(self):
        self.frameMove(1)

    def framePrev(self):
        self.frameMove(-1)

    def setUpMask(self,t):
        self.displayFrame = Frame(self.cImgFrame, height=500,width=50)

        if (len(t.split('->'))>1):
            probe = [probe for probe in self.probes if
                 probe.edgeId[1] in self.lookup[self.edgeTuple[0]] and probe.finalNodeId in self.lookup[self.edgeTuple[1]]][0]
        else:
            probe = \
            [probe for probe in self.probes if
             probe.edgeId[1] in self.lookup[self.edgeTuple[0]] and probe.donorBaseNodeId in
             self.lookup[
                 self.edgeTuple[1]]][0]
        if probe.targetVideoSegments is not None:
            self.maskBox = MaskSetTable(self.displayFrame,
                                        maskgen.scenario_model.VideoMaskSetInfo(compositeMaskSetFromVideoSegment(probe.targetVideoSegments)),
                                        openColumn=3,
                                        dir=self.scModel.get_dir(), boxheight=389, boxwidth=452)
            self.maskBox.grid()
            self.pageDisplays[self.cur][1].append(self.displayFrame)

    def setUpPlot(self,t):
        ps = [mpatches.Patch(color="red", label="Target Video"),mpatches.Patch(color="blue",label="Current Manipulations"),mpatches.Patch(color="green",label="Other Manipulations")]
        data = []
        f = Figure(figsize=(6,4), dpi=100)
        subplot = f.add_subplot(111)
        subplot.legend(handles=ps,loc=8)
        prolist = []
        maxtsec =0
        for p in self.probes:
            maxtsec = max(maxtsec, p.max_time())
            if (self.finalNodeName == None):
                if p.donorBaseNodeId is not None and self.getFileNameForNode(p.donorBaseNodeId) == self.edgeTuple[1]:
                    prolist.append(p)
            else:
                if (self.getFileNameForNode(p.finalNodeId) == self.edgeTuple[1]):
                    prolist.append(p)
        try:
            tsec = get_end_time_from_segment(getMaskSetForEntireVideo(
                self.meta_extractor.getMetaDataLocator(self.lookup[self.edgeTuple[1]][0]),
                 media_types=p.media_types())[0]) / 1000.0
        except Exception as ex:
            logging.getLogger("maskgen").error(ex.message)
            logging.getLogger("maskgen").error("{} Duration could not be found the length displayed in the graph is incorrect".format(self.edgeTuple[1]))
            tsec = maxtsec
        ytics = []
        ytic_lbl = []
        count = 0
        high = 0
        low = tsec*1000+20000
        for p in prolist:
            count += 1
            col = 2
            cur = False
            if (p.edgeId[1] in self.lookup[self.edgeTuple[0]]):
                col = 1
                cur = True
            if self.finalNodeName == None:
                for mvs in p.donorVideoSegments if p.donorVideoSegments is not None else []:
                    data.append([count,col,mvs.starttime,mvs.endtime])
                    if cur:
                        high = max(high,mvs.endtime)
                        low = min(low,mvs.starttime)
                        subplot.text(mvs.starttime - 100, count-0.5, "F:" + str(int(mvs.startframe)),{'size':10})
                        subplot.text(mvs.endtime + 100, count-0.5, "F:" + str(int(mvs.endframe)),{'size':10})
                        subplot.text(mvs.starttime - 100, count - 0.20, "T:" + str(int(mvs.starttime)), {'size': 10})
                        subplot.text(mvs.endtime + 100, count - 0.20, "T:" + str(int(mvs.endtime)), {'size': 10})
            else:
                for mvs in p.targetVideoSegments if p.targetVideoSegments is not None else []:
                    data.append([count,col,mvs.starttime,mvs.endtime])
                    if cur:
                        high = max(high,mvs.endtime)
                        low = min(low,mvs.starttime)
                        subplot.text(mvs.starttime, count-0.5, "F:" + str(int(mvs.startframe)),{'size':10})
                        subplot.text(mvs.endtime,count-0.5, "F:" + str(int(mvs.endframe)),{'size':10})
                        subplot.text(mvs.starttime, count - 0.20, "T:" + str(int(mvs.starttime)), {'size': 10})
                        subplot.text(mvs.endtime, count - 0.20, "T:" + str(int(mvs.endtime)), {'size': 10})
            ytics.append(count)
            ytic_lbl.append(str(self.abreive(p.edgeId[0])))

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
        self.displayFrame = Frame(self.cImgFrame)
        self.pageDisplays[self.cur][1].append(self.displayFrame)
        canvas = Canvas(self.displayFrame,height=50,width=50)
        imscroll = Scrollbar(self.displayFrame, orient=HORIZONTAL)
        imscroll.grid(row =1,column=0,sticky=EW)
        imscroll.config(command=self.scrollplt)
        fcanvas = FigureCanvasTkAgg(f, master=canvas)
        fcanvas.show()
        fcanvas.get_tk_widget().grid(row=0,column=0)
        fcanvas._tkcanvas.grid(row=0, column=0)
        canvas.grid(row=0, column=0)
        canvas.config(height=50,width=50)
        self.subplots[self.cur] = f

    def frameMove(self, i):
        displays = self.pageDisplays[self.cur]
        cur = displays[0]
        frames = displays[1]
        if 0 <= cur+i < len(frames):
            frames[cur].grid_forget()
            frames[cur+i].grid(row=0,column=0,columnspan=3)
            displays[0] += i

    def scrollplt(self, *args):
        if (args[0] == 'moveto'):
            na = self.pltdata[self.cur]
            end = na[-1]
            total = end[3]-end[2] + 20000
            curframe = self.subplots[self.cur].get_children()[1].xaxis.get_view_interval()
            space = curframe[1]-curframe[0]
            total *= float(args[1])
            self.subplots[self.cur].get_children()[1].xaxis.set_view_interval(total, total+space,ignore=True)
            self.subplots[self.cur].canvas.draw()
        elif (args[0] == 'scroll'):
            self.subplots[self.cur].get_children()[1].xaxis.pan(int(args[1]))
            self.subplots[self.cur].canvas.draw()


    def createImagePage(self, t, p):

        self.edgeTuple = tuple(t.split("<-"))
        if len(self.edgeTuple) < 2:
            self.finalNodeName = t.split("->")[1]
            self.edgeTuple = tuple(t.split("->"))
        else:
            self.finalNodeName = None
        if (len(t.split('->'))>1):
            probe = [probe for probe in self.probes if
                 probe.edgeId[1] in self.lookup[self.edgeTuple[0]] and probe.finalNodeId in self.lookup[self.edgeTuple[1]]][0]
        else:
            probe = \
            [probe for probe in self.probes if
             probe.edgeId[1] in self.lookup[self.edgeTuple[0]] and probe.donorBaseNodeId in
             self.lookup[
                 self.edgeTuple[1]]][0]
        success = maskgen.tool_set.get_icon('RedX.png') if probe.failure else maskgen.tool_set.get_icon('check.png')
        iFrame = Frame(p)


        c = Canvas(iFrame, width=35, height=35)

        c.pack()
        img = openImage(success)
        self.narnia[t] = ImageTk.PhotoImage(imageResizeRelative(img, (30, 30), img.size).toPIL())
        self.image_on_canvas = c.create_image(15, 15, image=self.narnia[t], anchor=CENTER, tag='things')
        row = 0
        col = 0

        self.optionsLabel = Label(p, text=t, font=(None,10))
        self.optionsLabel.grid(row=row, columnspan=3, sticky='EW', padx=(40,0),pady=10)
        iFrame.grid(column=0, row=0, columnspan=1, sticky=W)
        row += 1
        self.operationVar = StringVar()
        self.operationVar.set("Operation [ Semantic Groups ]: ")
        self.operationLabel = Label(p, textvariable=self.operationVar, justify=LEFT)
        self.semanticFrame = SemanticFrame(p)
        self.semanticFrame.grid(row=row+1, column=0, columnspan=2, sticky=N+W, rowspan=1, pady=10)
        row += 2
        self.cImgFrame = Frame(p)
        self.cImgFrame.grid(row=row, rowspan=8)
        self.descriptionVar = StringVar()
        self.descriptionLabel = Label(p, textvariable=self.operationVar, justify=LEFT)
        row += 8
        self.operationLabel.grid(row=row, columnspan=3, sticky='W', padx=10)
        row += 1
        textscroll = Scrollbar(p)
        textscroll.grid(row=row, column=col + 1, sticky=NS)
        self.commentBox = Text(p, height=5, width=80, yscrollcommand=textscroll.set, relief=SUNKEN)
        self.commentsBoxes[t] = self.commentBox
        self.commentBox.grid(row=row, column=col, padx=5, pady=5, columnspan=1, rowspan = 2, sticky=NSEW)

        textscroll.config(command=self.commentBox.yview)
        col = 3
        row = 0
        scroll = Scrollbar(p)
        scroll.grid(row=row, column=col + 2, rowspan=5, columnspan=1,sticky=NS)

        self.pathList = Listbox(p, width=30, yscrollcommand=scroll.set,selectmode=EXTENDED,exportselection=0)
        self.pathList.grid(row=row, column=col-1, rowspan=5, columnspan=3, padx=(30,10), pady=(20,20))
        self.pathboxes[p] = self.semanticFrame.getListbox()
        scroll.config(command=self.pathList.yview)
        self.transitionVar = StringVar()


        edge = self.scModel.getGraph().get_edge(probe.edgeId[0], probe.edgeId[1])
        self.operationVar.set(self.operationVar.get() + self._compose_label(edge))
        self.edges[p] = [edge, self.semanticFrame.getListbox()]
        for sg in edge['semanticGroups'] if 'semanticGroups' in edge else []:
            self.semanticFrame.insertListbox(ANCHOR, sg)
        operation = self.scModel.getGroupOperationLoader().getOperationWithGroups(edge['op'])

        if ('<-' in t and probe.donorVideoSegments is None) or probe.targetVideoSegments is None:
            self.loadt(t)
        else:
            self.transitionString(None)
            self.setUpFrames(t)
        if operation.qaList is not None:
            args = getValue(edge, 'arguments', {})
            self.curOpList = [x for x in operation.qaList]
            for item_pos in range(len(self.curOpList)):
                item = self.curOpList[item_pos]
                try:
                    self.curOpList[item_pos] = item.format(**args )
                except:
                    pass
        else:
            self.curOpList = []
        row += 5
        checkboxes = []
        self.checkboxvars[self.cur] = []
        if self.curOpList is None:
            self.qaData.set_qalink_status(t,'yes')

        for q in self.curOpList:
            var = BooleanVar()
            ck = Checkbutton(p, variable=var, command=self.check_ok)
            ck.select() if (self.qaData.get_qalink_status(t) == 'yes') else ck.deselect()
            ck.grid(row=row, column=col-1)
            checkboxes.append(ck)
            self.checkboxvars[self.cur].append(var)
            Label(p, text=q, wraplength=250, justify=LEFT).grid(row=row, column=col, columnspan=4,
                                                                   sticky='W')
            row += 1

        currentComment = self.qaData.get_qalink_caption(t)
        self.commentBox.delete(1.0,END)
        self.commentBox.insert(END, currentComment if currentComment is not None else '')
        self.acceptButton = Button(p, text='Next', command=self.nex, width=15)
        self.acceptButton.grid(row=12, column=col+2, columnspan=2, sticky='E',padx=(20,20))
        self.prevButton = Button(p, text='Previous', command=self.pre, width=15)
        self.prevButton.grid(row=12, column=col-1, columnspan=2, sticky='W',padx=(20,20))

        self.acceptnButton = Button(p, text='Next Unchecked', command=self.nexCheck, width=15)
        self.acceptnButton.grid(row=13, column=col + 2, columnspan=2, sticky='E',padx=(20,20))
        self.prevnButton = Button(p, text='Previous Unchecked', command=self.preCheck, width=15)
        self.prevnButton.grid(row=13, column=col-1, columnspan=2, sticky='W',padx=(20,20))
        row = 14
        pb = ttk.Progressbar(p,orient='horizontal', mode='determinate',maximum=100.0001)
        pb.grid(row = row, column = 0, sticky=EW,columnspan=8)
        pb.step(self.progress*100)

        self.progressBars.append(pb)

    def moveto(self, i):
        pass

    def transitionString(self, probeList):
        tab = "     "
        current = 0
        c = 0
        if self.finalNodeName == None:
            self._add_to_listBox(self.pathList, self.edgeTuple[1])
            self.pathList.insert(END, 2*tab + "|")
            self.pathList.insert(END, tab + "Donor")
            self.pathList.insert(END, 2*tab + "|")
            self.pathList.insert(END, 2*tab + "V")
            self._add_to_listBox(self.pathList, self.edgeTuple[0])
            self.pathList.select_set(6)
            return self.edgeTuple[0] + "\n|Donor|\nV\n" + self.edgeTuple[1]
        self._add_to_listBox(self.pathList,self.backs[self.finalNodeName][0].start)
        for p in self.backs[self.finalNodeName]:
            edge = self.scModel.getGraph().get_edge(p.start, p.end)
            self.pathList.insert(END, 2 * tab + "|")
            c += self._add_to_listBox(self.pathList, edge['op'])
            self.pathList.insert(END, 2 * tab + "|")
            self.pathList.insert(END, 2 * tab + "V")
            c += 3
            c += self._add_to_listBox(self.pathList, self.getFileNameForNode(p.end))
            if self.getFileNameForNode(p.end) == self.edgeTuple[0]:
                current = c

        self.pathList.selection_set(current)
        self.pathList.see(max(0,current-5))
        return ""


    def _add_to_listBox(self, box, string):
        if len(string) < 20:
            box.insert(END, string)
            return 1
        box.insert(END, string[0:15]+"...")
        box.insert(END, "    " + string[max(15-int(len(string)),-10):])
        return 2

    def _compose_label(self,edge):
        op  = edge['op']
        if 'semanticGroups' in edge and edge['semanticGroups'] is not None:
            groups = edge['semanticGroups']
            op += ' [' + ', '.join(groups) + ']'
        self.descriptionVar = edge['description']
        return op

    def loadt(self,t):
        self.load_overlay(True, t)

    def load_overlay(self, initialize,t):
        edgeTuple = self.edgeTuple
        message = 'final image'
        if (len(t.split('->')) > 1):
            probe = [probe for probe in self.probes if
                     probe.edgeId[1] in self.lookup[self.edgeTuple[0]] and probe.finalNodeId in self.lookup[
                         self.edgeTuple[1]]][0]
            n = self.parent.scModel.G.get_node(probe.finalNodeId)
            finalFile = os.path.join(self.parent.scModel.G.dir,
                                     self.parent.scModel.G.get_node(probe.finalNodeId)['file'])
            final = openImage(finalFile)
            finalResized = imageResizeRelative(final, (500, 500), final.size)
            imResized = imageResizeRelative(probe.targetMaskImage, (500, 500),
                                            probe.targetMaskImage.size if probe.targetMaskImage is not None else finalResized.size)


        else:
            message = 'donor'
            probe = \
        [probe for probe in self.probes if probe.edgeId[1] in self.lookup[edgeTuple[0]] and probe.donorBaseNodeId in self.lookup[edgeTuple[1]]][0]
            final, final_file = self.scModel.G.get_image(probe.donorBaseNodeId)
            finalResized = imageResizeRelative(final, (500, 500), final.size)
            imResized = imageResizeRelative(probe.donorMaskImage, (500, 500),
                                        probe.donorMaskImage.size if probe.donorMaskImage is not None else finalResized.size)

        edge = self.scModel.getGraph().get_edge(probe.edgeId[0],probe.edgeId[1])

        if initialize is True:
            self.c = Canvas(self.cImgFrame, width=510, height=510)
            self.c.pack()
        self.transitionString(None)
        try:
            finalResized = finalResized.overlay(imResized)
        except IndexError:
            tex = self.c.create_text(250,250,width=400,font=("Courier", 20))
            self.c.itemconfig(tex, text="The mask of link {} did not match the size of the {}.".format(t, message))
            return

        self.photos[t] = ImageTk.PhotoImage(finalResized.toPIL())

        self.image_on_canvas = self.c.create_image(255, 255, image=self.photos[t], anchor=CENTER, tag='imgc')

    def nexCheck(self):
        self.move(1,True)

    def preCheck(self):
        self.move(-1,True)

    def move(self, dir, checked):

        if self.cur in self.edges.keys():
            self.edges[self.cur][0]['semanticGroups'] = self.edges[self.cur][1].get(0, END)
        finish = True
        if self.cur in self.checkboxvars.keys():
            for i in self.checkboxvars[self.cur]:
                if i.get() is False:
                    finish = False
                    break
        ind = self.pages.index(self.cur)
        step = 0
        if 0<=ind-1<len(self.crit_links):
            if finish and self.crit_links[ind-1] in self.qaData.keys():
                if self.qaData.get_qalink_status(self.crit_links[ind-1]) == 'no':
                    step += 1.0/len(self.crit_links)*100
                self.qaData.set_qalink_status(self.crit_links[ind-1],'yes')
                self.qaData.set_qalink_caption(self.crit_links[ind-1],self.commentsBoxes[self.crit_links[ind-1]].get(1.0, END).strip())

            if not finish:
                if self.qaData.get_qalink_status(self.crit_links[ind-1]) == 'yes':
                    step += -1.0/len(self.crit_links)*100
                self.qaData.set_qalink_status(self.crit_links[ind - 1], 'no')
                self.qaData.set_qalink_caption(self.crit_links[ind - 1], self.commentsBoxes[self.crit_links[ind - 1]].get(1.0, END).strip())
        for p in self.progressBars:
            p.step(step)
        i = self.pages.index(self.cur) + dir

        if not 0<=i<len(self.pages):
            return
        nex = self.cur
        while checked:
            nex = self.pages[i]
            finish = True
            if nex in self.checkboxvars.keys():
                for t in self.checkboxvars[nex]:
                    if t.get() is False:
                        finish = False
                        break
            if i == len(self.pages)-1 or i == 0:
                break
            if not finish:
                break
            i += dir
        self.cur.grid_forget()
        self.cur = self.pages[i]
        self.cur.grid()

    def qa_done(self, qaState):
        self.qaData.update_All(qaState, self.reporterStr.get(), self.commentsBox.get(1.0, END), None)
        self.parent.scModel.save()
        self.destroy()

    def getPredNode(self, node):
        for pred in self.scModel.G.predecessors(node):
            edge = self.scModel.G.get_edge(pred, node)
            if edge['op'] != 'Donor':
                return self.scModel.getModificationForEdge(pred, node)
        return None

    def check_ok(self, event=None):
        turn_on_ok = len(self.crit_links) > 0 and len(self.errors) == 0
        if not turn_on_ok:
            for l in self.checkboxvars:
                if l is not None:
                    for b in self.checkboxvars[l]:
                        if b.get() is False or turn_on_ok is False:
                            turn_on_ok = False
        if turn_on_ok is True and self.valid is True:
            self.acceptButton.config(state=NORMAL)
        else:
            self.acceptButton.config(state=DISABLED)