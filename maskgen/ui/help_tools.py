from Tkinter import *
from maskgen.software_loader import *
from maskgen.tool_set import *
import json
from PIL import Image, ImageTk


class HelpFrame(Frame):
    def __init__(self, master, semanticgroup, node, textvar):
        self.master = master
        if semanticgroup or not node:
            self.info = getProjectProperties()
        if node:
            self.info = getOperations()
        Frame.__init__(self, master)
        self.setup_window(textvar)

    def setup_window(self, textvar):
        self.info_text = Label(self.master)
        self.info_text.grid(row=2, column=0, columnspan=3)

        self.info_image0 = Button(self.master)
        self.info_image1 = Button(self.master)
        self.info_image2 = Button(self.master)

        textvar.trace("w", lambda *args: self.update_choice(textvar))
        self.update_choice(textvar)

    def update_choice(self, var):
        path = getFileName("help\\group_config.json")  # TODO: Change to use the self.info data instead of this file
        with open(path) as f:
            self.data = json.load(f)

        self.selection = var.get()

        imglist = self.data[self.selection]['images']

        if len(imglist) >= 1:
            path = getFileName(os.path.join("help", imglist[0]))
            with Image.open(path, "r") as i:
                i = i.resize((480, 360), Image.ANTIALIAS)
                tkimg = ImageTk.PhotoImage(i)
            self.info_image0.configure(image=tkimg, command=lambda path=path: openFile(path))
            self.info_image0.image = tkimg
            self.info_image0.grid(row=3, column=0)
        else:
            self.info_image0.grid_forget()
            self.info_image1.grid_forget()
            self.info_image2.grid_forget()

        if len(imglist) >= 2:
            path = getFileName(os.path.join("help", imglist[1]))
            with Image.open(path, "r") as i:
                i = i.resize((480, 360), Image.ANTIALIAS)
                tkimg = ImageTk.PhotoImage(i)
            self.info_image1.configure(image=tkimg, command=lambda path=path: openFile(path))
            self.info_image1.image = tkimg
            self.info_image1.grid(row=3, column=1)
        else:
            self.info_image1.grid_forget()
            self.info_image2.grid_forget()

        if len(imglist) >= 3:
            path = getFileName(os.path.join("help", imglist[2]))
            with Image.open(path, "r") as i:
                i = i.resize((480, 360), Image.ANTIALIAS)
                tkimg = ImageTk.PhotoImage(i)
            self.info_image2.configure(image=tkimg, command=lambda path=path: openFile(path))
            self.info_image2.image = tkimg
            self.info_image2.grid(row=3, column=2)
        else:
            self.info_image2.grid_forget()

        self.info_text['text'] = self.data[self.selection]["text_description"]
