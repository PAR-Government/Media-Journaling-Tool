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
from maskgen.tool_set import imageResizeRelative, openImage,get_username, GrayBlockOverlayGenerator, compose_overlay_name
import os
import numpy as np
import maskgen.qa_logic
from maskgen.video_tools import getMaskSetForEntireVideo, get_end_time_from_segment
import maskgen.tool_set
import random
import maskgen.scenario_model
from maskgen.services.probes import ProbeGenerator, DetermineTaskDesignation, fetch_qaData_designation, cleanup_temporary_files
import maskgen.validation
from maskgen.tool_set import openFile
import webbrowser
from maskgen.graph_meta_tools import MetaDataExtractor


class Chkbox:

    def __init__(self, parent, dialog, label=None, command=None, value=False):
        self.value = BooleanVar(value=value)
        self.box = Checkbutton(parent, variable=self.value, command=dialog.check_ok if command is None else command)
        self.label = label

    def __nonzero__(self):
       return self.value.get()

    def set_value(self, value):
        self.value.set(value=value)

    def grid_info(self):
        return self.box.grid_info()

    def grid(self):
        self.label.grid()
        self.box.grid()

    def grid_remove(self):
        self.box.grid_remove()
        self.label.grid_remove()


class CheckboxGroup:
    """
    boxes: list of wrapped Checkboxes
    condition: either 'all'- all checkboxes in the group must be true or 'any'- any true value will return true.
    """

    def __init__(self, boxes = [], condition = 'all'):
        self.boxes = boxes
        self.condition = condition

    def __nonzero__(self):
        if len(self.boxes) == 0:
            return True
        if self.condition == 'any':
            return any(bool(value) for value in self.boxes)
        else:
            return all(bool(value) for value in self.boxes)

    def hide_group(self):
        for ck in self.boxes:
            ck.grid_remove()

    def show_group(self):
        for ck in self.boxes:
            ck.grid()

    def grid_info(self, index = -1):
        """
        Get the grid_info of the checkbox at the index. default is last index
        :return:
        """
        return self.boxes[index].grid_info() if len(self.boxes) > 0 else {}

class MannyPage(Frame):

    """
    Displays mascot with instructions and status information on probe and QA page generation.
    """
    checkboxes = CheckboxGroup()
    manny_colors = [[155, 0, 0], [0, 155, 0], [0, 0, 155], [153, 76, 0], [96, 96, 96], [204, 204, 0], [160, 160, 160]]

    def __init__(self, master):
        Frame.__init__(self, master)
        self.statusLabelText = StringVar()
        self.statusLabelText.set('Probes Generating')
        self.heading = Label(self, text="Welcome to the QA Wizard. Press Next to begin the QA Process or Quit to stop. This is "
                          "Manny; He is here to help you analyze the journal. The tool is currently generating the probes. "
                          "This could take a while. When the next button is enabled you may begin.",
              wraplength=400)
        self.heading.grid(column=0, row=0, rowspan=2, columnspan=2)
        manny_color = maskgen.tool_set.get_icon('Manny_icon_color.jpg')
        manny_mask = maskgen.tool_set.get_icon('Manny_icon_mask.jpg')
        self.mannyFrame = Frame(self)
        self.mannyFrame.grid(column=0, row=2, columnspan=2)
        self.canvas = Canvas(self.mannyFrame, width=510, height=510)
        self.canvas.pack()
        manny_img = openImage(manny_color)
        manny_img_mask = openImage(manny_mask).to_mask()
        manny_img_mask = imageResizeRelative(manny_img_mask, (500, 500), manny_img_mask.size)
        self.manny = ImageTk.PhotoImage(
            imageResizeRelative(manny_img, (500, 500), manny_img.size).overlay(manny_img_mask,self.manny_colors[
            random.randint(0, len(self.manny_colors) - 1)]).toPIL())
        self.image_on_canvas = self.canvas.create_image(510 / 2, 510 / 2, image=self.manny, anchor=CENTER, tag='things')
        self.statusLabelObject = Label(self, textvariable=self.statusLabelText)
        self.statusLabelObject.grid(column=0, row=3, columnspan=2, sticky=E + W)
        self.canvas.bind("<Double-Button-1>", master.help)
        self.wquit = Button(self, text='Quit', command=master.exitProgram, width=20)
        self.wquit.grid(column=0, row=4, sticky=W, padx=5, pady=5)
        self.wnext = Button(self, text='Next', command=master.nex, state=DISABLED, width=20)
        self.wnext.grid(column=1, row=4, sticky=E, padx=5, pady=5)

class FinalPage(Frame):
    """
    Final QA page, handles comments, final approval.
    """
    def __init__(self, master):
        Frame.__init__(self, master)
        row = 0
        col = 0
        self.infolabel = Label(self, justify=LEFT, text='QA Checklist:').grid(row=row, column=col)
        row += 1
        qa_list = [
            'Base and terminal node images should be the same format. -If the base was a JPEG, the Create JPEG/TIFF option should be used as the last step.',
            'All relevant semantic groups are identified.']
        self.checkboxes = CheckboxGroup(boxes=[])
        for q in qa_list:
            box_label = Label(self, text=q, wraplength=600, justify=LEFT)
            ck = Chkbox(parent=self, dialog=master, label=box_label, value=master.qaData.get_state())
            ck.box.grid(row=row, column=col)
            ck.label.grid(row=row, column=col + 1, sticky='W')
            self.checkboxes.boxes.append(ck)
            row += 1
        master.checkboxes[master.current_qa_page] = self.checkboxes
        Label(self, text='QA Signoff: ').grid(row=row, column=col)
        col += 1
        self.reporterStr = StringVar()
        self.reporterStr.set(get_username())
        self.reporterEntry = Entry(self, textvar=self.reporterStr)
        self.reporterEntry.grid(row=row, column=col, columnspan=3, sticky='W')
        row += 2
        col -= 1
        self.acceptButton = Button(self, text='Accept', command=lambda: master.qa_done('yes'), width=15,
                                   state=DISABLED)
        self.acceptButton.grid(row=row, column=col + 2, columnspan=2, sticky='W')
        self.rejectButton = Button(self, text='Reject', command=lambda: master.qa_done('no'), width=15)
        self.rejectButton.grid(row=row, column=col + 1, columnspan=1, sticky='E')
        self.previButton = Button(self, text='Previous', command=master.pre, width=15)
        self.previButton.grid(row=row, column=col, columnspan=2, sticky='W')

        row += 1
        self.commentsLabel = Label(self, text='Comments: ')
        self.commentsLabel.grid(row=row, column=col, columnspan=3)
        row += 1
        textscroll = Scrollbar(self)
        textscroll.grid(row=row, column=col + 4, sticky=NS)
        self.commentsBox = Text(self, height=5, width=100, yscrollcommand=textscroll.set, relief=SUNKEN)
        self.commentsBox.grid(row=row, column=col, padx=5, pady=5, columnspan=3, sticky=NSEW)
        textscroll.config(command=self.commentsBox.yview)
        currentComment = master.parent.scModel.getProjectData('qacomment')
        self.commentsBox.insert(END, currentComment) if currentComment is not None else ''

class QAPage(Frame):
    """
    A standard QA Page, allows review and user validation of probe spatial, temporal aspects
    """

    #TODO: Refactor to put page data with the page.
    """
    subplots = []
    pltdata = []
    successIcon = None
    displays = []
    pathboxes = []
    """

    def __init__(self, master, link):
        Frame.__init__(self, master=master)
        self.master = master
        self.link = link
        self.checkboxes = CheckboxGroup(boxes=[])
        #Find this probe- could probably do this elsewhere and pass it in.
        self.edgeTuple = tuple(link.split("<-"))
        if len(self.edgeTuple) < 2:
            self.finalNodeName = link.split("->")[1]
            self.edgeTuple = tuple(link.split("->"))
        else:
            self.finalNodeName = None
        if (len(link.split('->'))>1):
            probe = [probe for probe in master.probes if
                 probe.edgeId[1] in master.lookup[self.edgeTuple[0]] and probe.finalNodeId in master.lookup[self.edgeTuple[1]]][0]
        else:
            probe = \
            [probe for probe in master.probes if
             probe.edgeId[1] in master.lookup[self.edgeTuple[0]] and probe.donorBaseNodeId in
             master.lookup[
                 self.edgeTuple[1]]][0]
        self.probe = probe
        iFrame = Frame(self)
        c = Canvas(iFrame, width=35, height=35)
        c.pack()

        #Success Icon
        img = openImage(maskgen.tool_set.get_icon('RedX.png') if probe.failure else maskgen.tool_set.get_icon('check.png'))
        self.successIcon = ImageTk.PhotoImage(imageResizeRelative(img, (30, 30), img.size).toPIL())
        c.create_image(15, 15, image=self.successIcon, anchor=CENTER, tag='things')

        #Layout
        row = 0
        col = 0
        self.optionsLabel = Label(self, text=self.link, font=(None, 10))
        self.optionsLabel.grid(row=row, columnspan=3, sticky='EW', padx=(40, 0), pady=10)
        iFrame.grid(column=0, row=0, columnspan=1, sticky=W)
        row += 1
        self.operationVar = StringVar(value="Operation [ Semantic Groups ]:")
        self.operationLabel = Label(self, textvariable=self.operationVar, justify=LEFT)
        self.semanticFrame = SemanticFrame(self)
        self.semanticFrame.grid(row=row + 1, column=0, columnspan=2, sticky=N + W, rowspan=1, pady=10)
        row += 2
        #cImageFrame is used for plot, image and overlay
        self.cImgFrame = ttk.Notebook(self)
        self.cImgFrame.bind('<<NotebookTabChanged>>', lambda a: self.frameMove())
        self.cImgFrame.grid(row=row, rowspan=8)
        self.descriptionVar = StringVar()
        self.descriptionLabel = Label(self, textvariable=self.operationVar, justify=LEFT)
        row += 8
        self.operationLabel.grid(row=row, columnspan=3, sticky='W', padx=10)
        row += 1
        textscroll = Scrollbar(self)
        textscroll.grid(row=row, column=col + 1, sticky=NS)
        self.commentBox = Text(self, height=5, width=80, yscrollcommand=textscroll.set, relief=SUNKEN)
        self.master.commentsBoxes[self.link] = self.commentBox
        self.commentBox.grid(row=row, column=col, padx=5, pady=5, columnspan=1, rowspan=2, sticky=NSEW)
        textscroll.config(command=self.commentBox.yview)
        col = 3
        row = 0
        scroll = Scrollbar(self)
        scroll.grid(row=row, column=col + 2, rowspan=5, columnspan=1, sticky=NS)

        self.pathList = Listbox(self, width=30, yscrollcommand=scroll.set, selectmode=EXTENDED, exportselection=0)
        self.pathList.grid(row=row, column=col - 1, rowspan=5, columnspan=3, padx=(30, 10), pady=(20, 20))
        self.master.pathboxes[self] = self.semanticFrame.getListbox()
        scroll.config(command=self.pathList.yview)
        self.transitionVar = StringVar()

        edge = master.scModel.getGraph().get_edge(probe.edgeId[0], probe.edgeId[1])
        self.operationVar.set(self.operationVar.get() + master._compose_label(edge))
        master.edges[self] = [edge, self.semanticFrame.getListbox()]
        for sg in edge['semanticGroups'] if 'semanticGroups' in edge else []:
            self.semanticFrame.insertListbox(ANCHOR, sg)
        operation = master.scModel.getGroupOperationLoader().getOperationWithGroups(edge['op'])

        #QA checkboxes
        if operation.qaList is not None:
            args = getValue(edge, 'arguments', {})
            self.curOpList = [x for x in operation.qaList]
            for item_pos in range(len(self.curOpList)):
                item = self.curOpList[item_pos]
                try:
                    self.curOpList[item_pos] = item.format(**args)
                except:
                    pass
        else:
            self.curOpList = []
        row += 5
        if self.curOpList is None:
            master.qaData.set_qalink_status(self.link, 'yes')

        for q in self.curOpList:
            box_label = Label(self, text=q, wraplength=250, justify=LEFT)
            ck = Chkbox(parent=self, dialog=master, label=box_label, value=master.qaData.get_qalink_status(link=link))
            ck.box.grid(row=row, column=col - 1)
            ck.label.grid(row=row, column=col, columnspan=4, sticky='W')
            self.checkboxes.boxes.append(ck)
            row += 1
        master.checkboxes[self] = self.checkboxes

        # Main Features- load the overlay for images, load plot graph & overlay page for videos
        if ('<-' in self.link and probe.donorVideoSegments is None) or probe.targetVideoSegments is None:
            self.load_overlay(initialize=True)
        else:
            self.transitionString(None)
            self.setUpFrames()

        #Comment section
        currentComment = master.qaData.get_qalink_caption(self.link)
        self.commentBox.delete(1.0, END)
        self.commentBox.insert(END, currentComment if currentComment is not None else '')

        #Navigation Buttons
        self.acceptButton = Button(self, text='Next', command=master.nex, width=15)
        self.acceptButton.grid(row=12, column=col + 2, columnspan=2, sticky='E', padx=(20, 20))
        self.prevButton = Button(self, text='Previous', command=master.pre, width=15)
        self.prevButton.grid(row=12, column=col - 1, columnspan=2, sticky='W', padx=(20, 20))

        self.acceptnButton = Button(self, text='Next Unchecked', command=master.nexCheck, width=15)
        self.acceptnButton.grid(row=13, column=col + 2, columnspan=2, sticky='E', padx=(20, 20))
        self.prevnButton = Button(self, text='Previous Unchecked', command=master.preCheck, width=15)
        self.prevnButton.grid(row=13, column=col - 1, columnspan=2, sticky='W', padx=(20, 20))
        row = 14
        #Progress Bar
        pb = ttk.Progressbar(self, orient='horizontal', mode='determinate', maximum=100.0001)
        pb.grid(row=row, column=0, sticky=EW, columnspan=8)
        pb.step(master.progress * 100)

        master.progressBars.append(pb)

    def setUpFrames(self):
        """
        Lays out inner display for video temporal and spatial review
        :return:
        """
        displays = [TemporalReviewDisplay(self)]
        if any(segment.filename != None for segment in self.probe.targetVideoSegments):
            displays.append(SpatialReviewDisplay(self))
        self.checkboxes.boxes.append(CheckboxGroup(boxes=[d.checkbox for d in displays], condition='any'))
        self.master.pageDisplays[self] = [0, displays]

    def _add_to_listBox(self, box, string):
        if len(string) < 20:
            box.insert(END, string)
            return 1
        box.insert(END, string[0:15]+"...")
        box.insert(END, "    " + string[max(15-int(len(string)),-10):])
        return 2

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
        self._add_to_listBox(self.pathList,self.master.backs[self.finalNodeName][0].start)
        for p in self.master.backs[self.finalNodeName]:
            edge = self.master.scModel.getGraph().get_edge(p.start, p.end)
            self.pathList.insert(END, 2 * tab + "|")
            c += self._add_to_listBox(self.pathList, edge['op'])
            self.pathList.insert(END, 2 * tab + "|")
            self.pathList.insert(END, 2 * tab + "V")
            c += 3
            c += self._add_to_listBox(self.pathList, self.master.getFileNameForNode(p.end))
            if self.master.getFileNameForNode(p.end) == self.edgeTuple[0]:
                current = c

        self.pathList.selection_set(current)
        self.pathList.see(max(0,current-5))
        return ""

    def load_overlay(self, initialize):
        """
        Lays out display for spatial overlay for image probes
        :param initialize:
        :return:
        """
        edgeTuple = self.edgeTuple
        message = 'final image'
        if (len(self.link.split('->')) > 1):
            probe = [probe for probe in self.master.probes if
                     probe.edgeId[1] in self.master.lookup[self.edgeTuple[0]] and probe.finalNodeId in self.master.lookup[
                         self.edgeTuple[1]]][0]
            n = self.master.scModel.G.get_node(probe.finalNodeId)
            finalFile = os.path.join(self.master.scModel.G.dir,
                                     self.master.scModel.G.get_node(probe.finalNodeId)['file'])
            final = openImage(finalFile)
            finalResized = imageResizeRelative(final, (500, 500), final.size)
            imResized = imageResizeRelative(probe.targetMaskImage, (500, 500),
                                            probe.targetMaskImage.size if probe.targetMaskImage is not None else finalResized.size)


        else:
            message = 'donor'
            probe = \
        [probe for probe in self.master.probes if probe.edgeId[1] in self.master.lookup[edgeTuple[0]] and probe.donorBaseNodeId in self.master.lookup[edgeTuple[1]]][0]
            final, final_file = self.master.scModel.G.get_image(probe.donorBaseNodeId)
            finalResized = imageResizeRelative(final, (500, 500), final.size)
            imResized = imageResizeRelative(probe.donorMaskImage, (500, 500),
                                        probe.donorMaskImage.size if probe.donorMaskImage is not None else finalResized.size)

        edge = self.master.scModel.getGraph().get_edge(probe.edgeId[0],probe.edgeId[1])

        if initialize is True:
            self.c = Canvas(self.cImgFrame, width=510, height=510)
            self.c.pack()
        self.transitionString(None)
        try:
            finalResized = finalResized.overlay(imResized)
        except IndexError:
            tex = self.c.create_text(250,250,width=400,font=("Courier", 20))
            self.c.itemconfig(tex, text="The mask of link {} did not match the size of the {}.".format(self.link, message))
            return
        self.master.photos[self.link] = ImageTk.PhotoImage(finalResized.toPIL())
        self.image_on_canvas = self.c.create_image(255, 255, image=self.master.photos[self.link], anchor=CENTER, tag='imgc')

    def frameMove(self):
        """
        change pages on inner display for videos
        :return:
        """
        if self in self.master.pageDisplays:
            displays = self.master.pageDisplays[self][1]
            d_index = self.cImgFrame.index('current')
            displays[d_index].checkbox.grid()
            for display in displays:
                if display != displays[d_index]:
                    display.checkbox.grid_remove()


    def scrollplt(self, *args):
        """
        Handle scrolling function on temporal review graph.
        :param args:
        :return:
        """
        if (args[0] == 'moveto'):
            na = self.master.pltdata[self]
            end = na[-1]
            total = end[3]-end[2] + 20000
            curframe = self.master.subplots[self].get_children()[1].xaxis.get_view_interval()
            space = curframe[1]-curframe[0]
            total *= float(args[1])
            self.master.subplots[self].get_children()[1].xaxis.set_view_interval(total, total + space, ignore=True)
            self.master.subplots[self].canvas.draw()
        elif (args[0] == 'scroll'):
            self.master.subplots[self].get_children()[1].xaxis.pan(int(args[1]))
            self.master.subplots[self].canvas.draw()

    def cache_designation(self):
        """
        Cache the QA validation of probe designation.
        :return:
        """
        self.master.check_ok()
        displays = self.master.pageDisplays[self][1] if self in self.master.pageDisplays else []
        if len(displays) > 0:
            validation = {'temporal': bool(displays[0].checkbox), 'spatial': bool(displays[1].checkbox) if len(displays) > 1 else False}
            elegibility = [key for key in validation.keys() if validation[key] == True]
            designation = '-'.join(elegibility) if len(elegibility) else 'detect'
        else:
             designation = self.probe.taskDesignation
        self.master.qaData.set_qalink_designation(self.link, designation)

class DummyPage(Frame):
    def __init__(self, master, labeltext = ''):
        Frame.__init__(self, master=master)
        self.mainlabel = Label(self, text= labeltext)
        self.mainlabel.pack()
        self.nextButton = Button(self, text='NEXT', command=master.nex)
        self.nextButton.pack()


class SpatialReviewDisplay(Frame):
    """
    The spatial review display for video
    """

    def __init__(self, page):
        Frame.__init__(self, master=page.cImgFrame, height=500,width=50)
        page.cImgFrame.add(self, text='Spatial')
        self.dialog = self.winfo_toplevel()
        #Add Checkbox for spatial review
        checkbox_info = page.checkboxes.boxes[-1].grid_info() if len(page.checkboxes.boxes) > 0 else {}
        chkboxes_row = int(checkbox_info['row']) + 1 if len(checkbox_info) > 0 else 5
        chkboxes_col = int(checkbox_info['column']) + 1 if len(checkbox_info) > 0 else 4
        spatial_box_label = Label(master=page, text='Spatial Overlay Correct?', wraplength=250, justify=LEFT)
        self.checkbox = Chkbox(parent=page, dialog=page.master, label=spatial_box_label, command=page.cache_designation,
                               value=page.master.qaData.get_qalink_designation(page.link) is not None)
        self.checkbox.box.grid(row=chkboxes_row, column=chkboxes_col -1)
        self.checkbox.label.grid(row=chkboxes_row, column=chkboxes_col, columnspan=4, sticky='W')
        self.checkbox.grid_remove() #hide for now, Will be gridded by the frameMove function

        if (len(page.link.split('->')) > 1):
            probe = [probe for probe in page.master.probes if
                     probe.edgeId[1] in page.master.lookup[page.edgeTuple[0]] and probe.finalNodeId in
                     page.master.lookup[page.edgeTuple[1]]][0]
        else:
            probe = \
                [probe for probe in page.master.probes if
                 probe.edgeId[1] in page.master.lookup[page.edgeTuple[0]] and probe.donorBaseNodeId in
                 page.master.lookup[
                     page.edgeTuple[1]]][0]

        if probe.targetVideoSegments is not None:
            to = os.path.join(self.dialog.scModel.get_dir(),probe.finalImageFileName)
            overlay_file = compose_overlay_name(target_file=to, link=page.link)
            total_range = (probe.targetVideoSegments[0].starttime/1000, probe.targetVideoSegments[-1].endtime/1000)

            self.buttonText = StringVar()

            self.buttonText.set(value=('PLAY: ' if os.path.exists(overlay_file) else 'GENERATE: ') + os.path.split(overlay_file)[1])
            self.playbutton = Button(master=self, textvariable=self.buttonText,
                                     command=lambda: self.openOverlay(probe=probe,
                                                                      target_file=to,
                                                                      overlay_path=overlay_file))
            self.playbutton.grid(row=0, column=0, columnspan=2, sticky='W')
            self.range_label = Label(master=self, text='Range: ' + '{:.2f}'.format(total_range[0]) + 's - ' + '{:.2f}'.format(total_range[1]) + 's')
            self.range_label.grid(row=0, column= 3, columnspan = 1, sticky='W')

    def openOverlay(self, probe=None, target_file = '', overlay_path=''):
        if not os.path.exists(overlay_path):
            GrayBlockOverlayGenerator(locator=self.dialog.meta_extractor.getMetaDataLocator(probe.edgeId[0]),
                                      segments=probe.targetVideoSegments,
                                      target_file=target_file, output_file=overlay_path).generate()
        self.buttonText.set('PLAY: ' + os.path.split(overlay_path)[1])
        openFile(overlay_path)

class TemporalReviewDisplay(Frame):
    """
    The temporal review display for video
    """

    def __init__(self, page):
        Frame.__init__(self, master=page.cImgFrame)
        page.cImgFrame.add(self, text='Temporal')
        # Add Checkbox for spatial review
        checkbox_info = page.checkboxes.boxes[-1].grid_info() if len(page.checkboxes.boxes) > 0 else {}
        chkboxes_row = int(checkbox_info['row']) + 1 if len(checkbox_info) > 0 else 5
        chkboxes_col = int(checkbox_info['column']) + 1 if len(checkbox_info) > 0 else 4
        temporal_box_label = Label(master=page, text='Temporal data correct?', wraplength=250, justify=LEFT)
        self.checkbox = Chkbox(parent=page, dialog=page.master, label=temporal_box_label, command=page.cache_designation,
                               value=page.master.qaData.get_qalink_designation(page.link) is not None)
        self.checkbox.box.grid(row=chkboxes_row, column=chkboxes_col - 1)
        self.checkbox.label.grid(row=chkboxes_row, column=chkboxes_col, columnspan=4, sticky='W')
        self.checkbox.grid_remove() #hide for now, Will be gridded by the frameMove function

        ps = [mpatches.Patch(color="red", label="Target Video"),
              mpatches.Patch(color="blue", label="Current Manipulations"),
              mpatches.Patch(color="green", label="Other Manipulations")]
        data = []
        f = Figure(figsize=(6, 4), dpi=100)
        subplot = f.add_subplot(111)
        subplot.legend(handles=ps, loc=8)
        prolist = []
        maxtsec = 0

        for probe in page.master.probes:
            maxtsec = max(maxtsec, probe.max_time())
            if (page.finalNodeName == None):
                if probe.donorBaseNodeId is not None and page.master.getFileNameForNode(probe.donorBaseNodeId) == \
                        page.edgeTuple[
                            1]:
                    prolist.append(probe)
            else:
                if (page.master.getFileNameForNode(probe.finalNodeId) == page.edgeTuple[1]):
                    prolist.append(probe)
        try:
            tsec = get_end_time_from_segment(getMaskSetForEntireVideo(
                page.master.meta_extractor.getMetaDataLocator(page.master.lookup[page.edgeTuple[1]][0]),
                media_types=probe.media_types())[0]) / 1000.0
        except Exception as ex:
            logging.getLogger("maskgen").error(ex.message)
            logging.getLogger("maskgen").error(
                "{} Duration could not be found the length displayed in the graph is incorrect".format(
                    page.edgeTuple[1]))
            tsec = maxtsec
        ytics = []
        ytic_lbl = []
        count = 0
        high = 0
        low = tsec * 1000 + 20000
        for probe in prolist:
            count += 1
            col = 2
            cur = False
            if (probe.edgeId[1] in page.master.lookup[page.edgeTuple[0]]):
                col = 1
                cur = True
            if page.finalNodeName == None:
                for mvs in probe.donorVideoSegments if probe.donorVideoSegments is not None else []:
                    data.append([count, col, mvs.starttime, mvs.endtime])
                    if cur:
                        high = max(high, mvs.endtime)
                        low = min(low, mvs.starttime)
                        subplot.text(mvs.starttime - 100, count - 0.5, "F:" + str(int(mvs.startframe)),
                                     {'size': 10})
                        subplot.text(mvs.endtime + 100, count - 0.5, "F:" + str(int(mvs.endframe)), {'size': 10})
                        subplot.text(mvs.starttime - 100, count - 0.20, "T:" + str(int(mvs.starttime)),
                                     {'size': 10})
                        subplot.text(mvs.endtime + 100, count - 0.20, "T:" + str(int(mvs.endtime)), {'size': 10})
            else:
                for mvs in probe.targetVideoSegments if probe.targetVideoSegments is not None else []:
                    data.append([count, col, mvs.starttime, mvs.endtime])
                    if cur:
                        high = max(high, mvs.endtime)
                        low = min(low, mvs.starttime)
                        subplot.text(mvs.starttime, count - 0.5, "F:" + str(int(mvs.startframe)), {'size': 10})
                        subplot.text(mvs.endtime, count - 0.5, "F:" + str(int(mvs.endframe)), {'size': 10})
                        subplot.text(mvs.starttime, count - 0.20, "T:" + str(int(mvs.starttime)), {'size': 10})
                        subplot.text(mvs.endtime, count - 0.20, "T:" + str(int(mvs.endtime)), {'size': 10})
            ytics.append(count)
            ytic_lbl.append(str(page.master.abreive(probe.edgeId[0])))

        color_mapper = np.vectorize(lambda x: {0: 'red', 1: 'blue', 2: 'green'}.get(x))
        data.append([count + 1, 0, 0.0, tsec * 1000.0])
        ytics.append(count + 1)
        ytic_lbl.append(page.master.abreive(page.edgeTuple[1]))
        numpy_array = np.array(data)
        subplot.hlines(numpy_array[:, 0], numpy_array[:, 2], numpy_array[:, 3], color_mapper(numpy_array[:, 1]),
                       linewidth=10)
        subplot.set_yticks(ytics)
        subplot.set_yticklabels(ytic_lbl)
        subplot.set_xlabel('Time in Milliseconds')
        subplot.grid()
        i = subplot.yaxis.get_view_interval()
        if (i[1] - i[0] < 10):
            i[0] = i[1] - 8
            subplot.yaxis.set_view_interval(i[0], i[1])
        i = subplot.xaxis.get_view_interval()
        if (i[1] - i[0] > 2000):
            i[0] = low - 1000
            i[1] = high + 1000
            subplot.xaxis.set_view_interval(i[0], i[1])
        page.master.pltdata[page] = numpy_array
        canvas = Canvas(self, height=50, width=50)
        imscroll = Scrollbar(self, orient=HORIZONTAL)
        imscroll.grid(row=1, column=0, sticky=EW)
        imscroll.config(command=page.scrollplt)
        fcanvas = FigureCanvasTkAgg(f, master=canvas)
        fcanvas.show()
        fcanvas.get_tk_widget().grid(row=0, column=0)
        fcanvas._tkcanvas.grid(row=0, column=0)
        canvas.grid(row=0, column=0)
        canvas.config(height=50, width=50)
        page.master.subplots[page] = f

class QAProjectDialog(Toplevel):
    """
    Host window for QA pages
    """
    manny_colors = [[155, 0, 0], [0, 155, 0], [0, 0, 155], [153, 76, 0], [96, 96, 96], [204, 204, 0], [160, 160, 160]]

    def __init__(self, parent):
        self.parent = parent
        self.scModel = parent.scModel
        self.meta_extractor = MetaDataExtractor(parent.scModel.getGraph())
        self.probes = None
        Toplevel.__init__(self, parent)
        self.type = self.parent.scModel.getEndType()
        self.pages = []
        self.current_qa_page = None
        self.checkboxes = {} #Checkboxes, keyed by page
        self.backs = {}
        self.lookup = {}
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
        self.pageDisplays = {} #Frames that go inside pages, keyed by page.
        self.valid = False
        self.mannypage = MannyPage(self)
        self.switch_frame(self.mannypage)
        self.lastpage = None #Assigned in generate Pages
        self.pages.append(self.mannypage)
        self.getProbes()
        if self.probes is None:
            self.mannypage.statusLabelText.set('Probe Generation failed.  Please consult logs for more details.')
            self.parent.update()
        else:
            self.errors = [p for p in self.probes if p.failure]
            if len(self.errors) > 0:
                self.mannypage.statusLabelText.set('Probes Complete with errors. Generating Preview Pages.')
            else:
                self.mannypage.statusLabelText.set('Probes Complete. Generating Preview Pages.')
        self.generate_pages()

    def getProbes(self):
        try:
            generator = ProbeGenerator(
                scModel=self.scModel,
                processors=[
                    DetermineTaskDesignation(
                        scModel=self.scModel,
                        inputFunction=fetch_qaData_designation)])

            self.probes = generator(saveTargets=False, keepFailures=True)
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
        cleanup_temporary_files(probes=self.probes, scModel=self.scModel)

    def help(self,event):
        URL = MaskGenLoader.get_key("apiurl")[:-3] + "journal"
        webbrowser.open_new(URL)

    def generate_pages(self):
        self.crit_links = ['->'.join([self.getFileNameForNode(p.edgeId[1]), self.getFileNameForNode(p.finalNodeId)]) for
                           p in self.probes] if self.probes else []
        self.crit_links = list(set(self.crit_links))

        self.finNodes = []
        for x in range(0, len(self.crit_links)):
            for y in range(x, len(self.crit_links)):
                link1 = self.crit_links[x]
                link2 = self.crit_links[y]
                fin1 = link1.split("->")[1]
                fin2 = link2.split("->")[1]
                self.finNodes.append(fin2)
                if (fin1 > fin2):
                    self.crit_links[x] = self.crit_links[y]
                    self.crit_links[y] = link1
        self.finNodes = list(set(self.finNodes))
        for end in self.finNodes:
            for node in self.lookup[end]:
                if node in self.scModel.finalNodes():
                    break
            self.backs[end] = []
            next = self.getPredNode(node)
            while next != None:
                node = next.start
                self.backs[end].append(next)
                next = self.getPredNode(node)
            self.backs[end].reverse()

        donors = ['<-'.join([self.getFileNameForNode(p.edgeId[1]), self.getFileNameForNode(p.donorBaseNodeId)]) for p in
                  self.probes if
                  p.donorMaskImage is not None or p.donorVideoSegments is not None] if self.probes else []
        donors = set(sorted(donors))
        self.crit_links.extend([x for x in donors])
        count = 0.0
        for k in self.qaData.keys():
            count += 1 if self.qaData.get_qalink_status(k) == 'yes' else 0
        self.progress = count / len(self.crit_links) if len(self.crit_links) != 0 else 0.99999
        count = 1
        for link in self.crit_links:
            self.pages.append(QAPage(master=self, link=link))
            count += 1
        self.lastpage = FinalPage(self)
        self.pages.append(self.lastpage)
        self.mannypage.statusLabelText.set('Preview Pages Complete. Press Next to Continue.')
        self.mannypage.wnext.config(state=NORMAL)


    def validategoodtimes(self):
        v = self.scModel.validate()
        if maskgen.validation.core.hasErrorMessages(v, lambda x: True):
            self.valid = False
            tkMessageBox.showerror("Validation Errors!","It seems this journal has unresolved validation errors. "
                                    "Please address these and try again. Your QA progress will be saved.")
        else:
            self.valid = True
        self.check_ok()

    def abreive(self,str):
        if (len(str)>10):
            return(str[:5]+ "...\n" + str[-6:])
        else:
            return str

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

    def nexCheck(self):
        self.move(1,True)

    def preCheck(self):
        self.move(-1,True)

    def switch_frame(self, frame):
        if self.current_qa_page != None:
            self.current_qa_page.grid_forget()
        self.current_qa_page = frame
        self.current_qa_page.grid()

    def move(self, dir, checked):

        if self.current_qa_page in self.edges.keys():
            self.edges[self.current_qa_page][0]['semanticGroups'] = self.edges[self.current_qa_page][1].get(0, END)

        finish = True
        if self.current_qa_page in self.checkboxes.keys():
            for box in self.checkboxes[self.current_qa_page].boxes:
                if bool(box) is False:
                    finish = False
                    break

        #caching in qaData
        ind = self.pages.index(self.current_qa_page)
        step = 0
        if 0<=ind-1<len(self.crit_links):
            if finish and self.crit_links[ind-1] in self.qaData.keys():
                if self.qaData.get_qalink_status(self.crit_links[ind-1]) == 'no':
                    step += 1.0/len(self.crit_links)*100
                self.qaData.set_qalink_status(self.crit_links[ind-1],'yes')
                self.qaData.set_qalink_caption(self.crit_links[ind-1],self.commentsBoxes[self.crit_links[ind-1]].get(1.0, END).strip())
                self.current_qa_page.cache_designation()
            if not finish:
                if self.qaData.get_qalink_status(self.crit_links[ind-1]) == 'yes':
                    step += -1.0/len(self.crit_links)*100
                self.qaData.set_qalink_status(self.crit_links[ind - 1], 'no')
                self.qaData.set_qalink_caption(self.crit_links[ind - 1], self.commentsBoxes[self.crit_links[ind - 1]].get(1.0, END).strip())

        for p in self.progressBars:
            p.step(step)
        i = self.pages.index(self.current_qa_page) + dir

        if not 0<=i<len(self.pages):
            return
        nex = self.current_qa_page
        while checked:
            nex = self.pages[i]
            finish = True
            if nex in self.checkboxes.keys():
                for t in self.checkboxes[nex]:
                    if t.get() is False:
                        finish = False
                        break
            if i == len(self.pages)-1 or i == 0:
                break
            if not finish:
                break
            i += dir
        self.switch_frame(self.pages[i])

    def qa_done(self, qaState):
        self.qaData.update_All(qaState, self.lastpage.reporterStr.get(), self.lastpage.commentsBox.get(1.0, END), None)
        self.parent.scModel.save()
        self.destroy()
        cleanup_temporary_files(probes=self.probes, scModel=self.scModel)

    def getPredNode(self, node):
        for pred in self.scModel.G.predecessors(node):
            edge = self.scModel.G.get_edge(pred, node)
            if edge['op'] != 'Donor':
                return self.scModel.getModificationForEdge(pred, node)
        return None

    def check_ok(self, event=None):
        if self.lastpage != None:
            if len(self.errors) == 0 and all(bool(page.checkboxes) for page in self.pages):
                self.lastpage.acceptButton.config(state=NORMAL)
            else:
                self.lastpage.acceptButton.config(state=DISABLED)
