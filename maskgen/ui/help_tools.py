import tkMessageBox
from Tkinter import *
from maskgen.software_loader import *
from maskgen.tool_set import *
import json
from PIL import Image, ImageTk
from ttk import *


class HelpFrame(Frame):
    def __init__(self, master, itemtype, textvar):
        self.master = master
        self.r = 0
        self.itemtype = itemtype
        self.slide_size = (720, 480)
        self.loader = getHelpLoader()
        self.textvar = textvar
        Frame.__init__(self, master)
        self.setup_window()

    def setup_window(self):
        self.info_text = Label(self)
        self.info_text.grid(row=self.r, column=0)
        self.r += 1

        self.img_nb = Notebook(self)
        self.img0f = Frame(self.img_nb)
        self.img1f = Frame(self.img_nb)
        self.img2f = Frame(self.img_nb)
        self.img_nb.add(self.img0f, text="Image 1")
        self.img_nb.add(self.img1f, text="Image 2")
        self.img_nb.add(self.img2f, text="Image 3")
        self.img_nb.grid(row=self.r, column=0)
        self.r += 1

        self.info_image0 = Button(self.img0f)
        self.info_image1 = Button(self.img1f)
        self.info_image2 = Button(self.img2f)

        Label(self, text="Click through the image tabs to view various available information.  Click on any image to"
                         " open it with your default photo viewer.").grid(row=self.r, column=0)

        self.textvar.trace("w", lambda *args: self.update_choice(self.textvar))
        self.update_choice(self.textvar)

    def update_choice(self, var):
        self.selection = var.get()
        imglist = self.loader.get_help_png_list(self.selection, self.itemtype)

        # Clear all tabs
        try:
            self.img_nb.hide(1)
            self.img_nb.hide(2)
        except TclError:
            pass
        self.info_image0.grid_forget()
        self.info_image1.grid_forget()
        self.info_image2.grid_forget()

        if len(imglist) == 0:
            with Image.open(get_icon("Manny_icon_color.jpg"), "r") as i:
                i = i.resize(self.slide_size, Image.ANTIALIAS)
                tkimg = ImageTk.PhotoImage(i)
            item = "semantic group" if self.itemtype == 'semanticgroup' else "operation" if self.itemtype == "operation" else "project property"
            self.info_image0.configure(image=tkimg, command=lambda: tkMessageBox.showerror("No Images", "No help images have been supplied for this {0}.".format(item)))
            self.info_image0.image = tkimg

            self.info_image0.grid(row=0, column=0)

        if len(imglist) >= 1:
            with Image.open(imglist[0], "r") as i:
                i = i.resize(self.slide_size, Image.ANTIALIAS)
                tkimg = ImageTk.PhotoImage(i)
            self.info_image0.configure(image=tkimg, command=lambda: openFile(imglist[0]))
            self.info_image0.image = tkimg
            self.info_image0.grid(row=0, column=0)

        if len(imglist) >= 2:
            with Image.open(imglist[1], "r") as i:
                i = i.resize(self.slide_size, Image.ANTIALIAS)
                tkimg = ImageTk.PhotoImage(i)
            self.info_image1.configure(image=tkimg, command=lambda: openFile(imglist[1]))
            self.info_image1.image = tkimg
            self.info_image1.grid(row=0, column=0)
            self.img_nb.add(self.img1f)

        if len(imglist) >= 3:
            with Image.open(imglist[2], "r") as i:
                i = i.resize(self.slide_size, Image.ANTIALIAS)
                tkimg = ImageTk.PhotoImage(i)
            self.info_image2.configure(image=tkimg, command=lambda: openFile(imglist[2]))
            self.info_image2.image = tkimg
            self.info_image2.grid(row=0, column=0)
            self.img_nb.add(self.img2f)

        new_desc = self.loader.get_help_description(self.textvar.get(), self.itemtype)
        self.info_text['text'] = new_desc

        self.img_nb.select(0)

    def no_image_help(self):
        tkMessageBox.showError("No Images", "No help images have been found.")


def getHelpLoader():
    if 'helpLoader' not in global_config:
        global_config['helpLoader'] = HelpLoader()
    return global_config['helpLoader']


class HelpLoader:
    """
    Valid Item Types: 'project', 'semanticgroup', 'operation'
    """
    def __init__(self):
        self.imglist = {}
        self.load_image_json()

    def load_image_json(self):
        fpath = getFileName(os.path.join("help", "image_linker.json"))

        with open(fpath) as f:
            self.imglist = json.load(f)

        for key in self.imglist.keys():
            for subkey in self.imglist[key].keys():
                current = self.imglist[key][subkey]
                new = [getFileName(os.path.join("help", x)) for x in current]
                self.imglist[key][subkey] = new

    def get_help_png_list(self, name, itemtype):
        try:
            r = self.imglist[itemtype][name]
        except KeyError:
            r = None
        return r

    def get_help_description(self, name, itemtype):
        if itemtype != "operation":
            desc = getProjectProperty(name, itemtype).information
        else:
            desc = getOperation(name).description
        return desc
