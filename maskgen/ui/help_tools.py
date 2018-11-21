import tkMessageBox
import webbrowser
from Tkinter import *
from maskgen.software_loader import *
from maskgen.tool_set import *
import json
from PIL import Image, ImageTk, ImageOps
from ttk import *
import logging


class HelpFrame(Frame):
    def __init__(self, master, itemtype, textvar):
        self.master = master
        self.itemtype = itemtype
        self.slide_size = (960, 540)
        self.loader = getHelpLoader()
        self.textvar = textvar
        self.tabs = {}
        Frame.__init__(self, master)
        self.setup_window()

    def setup_window(self):
        r = 0
        self.info_text = Label(self, wraplength=750)
        self.info_text.grid(row=r, column=0)
        r += 1

        self.img_nb = Notebook(self)
        self.img_nb.grid(row=r, column=0)
        r += 1

        Label(self, text="Click through the image tabs to view various available information.  Click on any image "
                         "(even Manny) to open it with your default photo viewer or visit the help link if available.")\
            .grid(row=r, column=0)

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
                f.thumbnail(self.slide_size, Image.BILINEAR)
                tkimg = ImageTk.PhotoImage(f)
            fr = Frame(self.img_nb)
            img = Button(fr)
            self.img_nb.add(fr, text="Image 1")
            img.configure(image=tkimg, command=lambda: self.open(get_icon("Manny_icon_color.jpg")))
            img.image = tkimg
            img.grid(row=0, column=0)
            self.tabs["Manny"] = {}
            self.tabs["Manny"]["image"] = img
            self.tabs["Manny"]["frame"] = fr

        else:
            for n, i in enumerate(imglist):
                with Image.open(i, "r") as f:
                    f = f.resize(self.slide_size, Image.BILINEAR)
                    tkimg = ImageTk.PhotoImage(f)
                fr = Frame(self.img_nb)
                img = Button(fr)
                self.img_nb.add(fr, text="Image {0}".format(n + 1))
                img.configure(image=tkimg, command=lambda i=i: self.open(i))
                img.image = tkimg
                img.grid(row=0, column=0)
                self.tabs[i] = {}
                self.tabs[i]["image"] = img
                self.tabs[i]["frame"] = fr

        new_desc = self.loader.get_help_description(self.textvar.get(), self.itemtype)
        self.info_text['text'] = new_desc if new_desc else "No help description is available."

        self.img_nb.select(0)

    def open(self, i):
        name = self.textvar.get()
        dtype = self.itemtype
        url = self.loader.get_help_link(name, dtype)
        imgs = self.loader.get_help_png_list(name, dtype)
        imgs.append("Manny_icon_color.jpg")
        if url and imgs:
            LargerOrLink(self, i)
        elif url:
            webbrowser.open(url)
        elif imgs:
            openFile(i)
        else:
            tkMessageBox.showerror("No Images", "No help images or link has been supplied.")


class LargerOrLink(Toplevel):
    def __init__(self, master, image):
        Toplevel.__init__(self, master)
        self.master = master
        self.image = image
        self.wm_resizable(False, False)
        self.title("Help")
        self.main = Frame(self)
        self.main.pack()
        self.create_widgets()

    def create_widgets(self):
        openLarger = Button(self.main, text="Open Larger", command=self.open_larger)
        openLarger.grid(row=0, column=0)

        openLink = Button(self.main, text="Open Link", command=self.open_link)
        openLink.grid(row=0, column=1)

        close = Button(self.main, text="Cancel", command=lambda: self.destroy())
        close.grid(row=1, column=0, columnspan=2)

    def open_larger(self):
        openFile(self.image)
        self.destroy()

    def open_link(self):
        webbrowser.open(self.master.loader.get_help_link(self.master.textvar.get(), self.master.itemtype), new=2)
        self.destroy()



def getHelpLoader():
    if 'helpLoader' not in global_config:
        global_config['helpLoader'] = HelpLoader()
    return global_config['helpLoader']


class HelpLoader:
    """
    Valid Item Types: 'project', 'semanticgroup', 'operation'
    """
    def __init__(self):
        self.linker = {}
        self.load_image_json()

    def load_image_json(self):
        fpath = getFileName(os.path.join("help", "image_linker.json"))

        with open(fpath) as f:
            self.linker = json.load(f)

        for key in self.linker.keys():
            for subkey in self.linker[key].keys():
                if "images" in self.linker[key][subkey].keys():
                    current = self.linker[key][subkey]["images"]
                    imgs = []
                    for x in current:
                        if getFileName(os.path.join("help", x)) is None:
                            logging.getLogger('maskgen').warning('Couldnt find help image at: ' + os.path.join("help", x))
                        else:
                            imgs.append(getFileName(os.path.join("help", x)))
                    while None in imgs:
                        imgs.remove(None)
                    self.linker[key][subkey]["images"] = imgs

    def get_help_png_list(self, name, itemtype):
        try:
            r = self.linker[itemtype][name]["images"]
        except KeyError:
            r = None
        return r

    def get_help_description(self, name, itemtype):
        if itemtype != "operation":
            desc = getProjectProperty(name, itemtype).information
        else:
            op = getOperation(name)
            desc = op.description if op is not None else ''
        return desc

    def get_help_link(self, name, itemtype):
        try:
            r = self.linker[itemtype][name]["url"][0]
        except KeyError:
            r = None
        return r
