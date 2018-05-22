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
        self.slide_size = (960, 540)
        self.loader = getHelpLoader()
        self.textvar = textvar
        self.tabs = {}
        Frame.__init__(self, master)
        self.setup_window()

    def setup_window(self):
        self.info_text = Label(self, wraplength=750)
        self.info_text.grid(row=self.r, column=0)
        self.r += 1

        self.img_nb = Notebook(self)
        self.img_nb.grid(row=self.r, column=0)
        self.r += 1

        Label(self, text="Click through the image tabs to view various available information.  Click on any image to"
                         " open it with your default photo viewer.").grid(row=self.r, column=0)

        self.textvar.trace("w", lambda *args: self.update_choice(self.textvar))
        self.update_choice(self.textvar)

    def update_choice(self, var):
        self.selection = var.get()
        imglist = self.loader.get_help_png_list(self.selection, self.itemtype)

        # Clear all tabs
        for k in self.tabs.keys():
            self.tabs[k]["image"].grid_forget()
            self.tabs[k]["frame"].grid_forget()
            self.tabs.pop(k)
            self.img_nb.forget(0)

        image_count = len(imglist) if imglist else 0

        if image_count == 0:
            with Image.open(get_icon("Manny_icon_color.jpg"), "r") as f:
                f = f.resize(self.slide_size, Image.ANTIALIAS)
                tkimg = ImageTk.PhotoImage(f)
            item = "semantic group" if self.itemtype == 'semanticgroup' else "operation" if self.itemtype == "operation" else "project property"
            fr = Frame(self.img_nb)
            img = Button(fr)
            self.img_nb.add(fr, text="Image 1")
            img.configure(image=tkimg, command=lambda: tkMessageBox.showerror("No Images", "No help images have been "
                                                                              "supplied for this {0}.".format(item)))
            img.image = tkimg
            img.grid(row=0, column=0)
            self.tabs["Manny"] = {}
            self.tabs["Manny"]["image"] = img
            self.tabs["Manny"]["frame"] = fr

        else:
            for n, i in enumerate(imglist):
                with Image.open(i, "r") as f:
                    f = f.resize(self.slide_size, Image.ANTIALIAS)
                    tkimg = ImageTk.PhotoImage(f)
                item = "semantic group" if self.itemtype == 'semanticgroup' else "operation" if self.itemtype == "operation" else "project property"
                fr = Frame(self.img_nb)
                img = Button(fr)
                self.img_nb.add(fr, text="Image {0}".format(n + 1))
                img.configure(image=tkimg, command=lambda i=i: openFile(i))
                img.image = tkimg
                img.grid(row=0, column=0)
                self.tabs[i] = {}
                self.tabs[i]["image"] = img
                self.tabs[i]["frame"] = fr

        new_desc = self.loader.get_help_description(self.textvar.get(), self.itemtype)
        self.info_text['text'] = new_desc if new_desc else "No help description is available."

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
