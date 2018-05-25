from Tkinter import *
from PIL import ImageTk
from maskgen.tool_set import imageResizeRelative
import  tkFileDialog,tkSimpleDialog

class ScrollCompositeViewer(Frame):

    composite = None
    framescale = 1.0

    def __init__(self, master, image, composite):
        Frame.__init__(self, master, bd=2, relief=SUNKEN)
        self.im = image
        self.composite = composite
        self.canvas = Canvas(self, cursor="cross", width=500, height=500, confine=True,
                             scrollregion=(0, 0, image.size[1] * 10, image.size[0] * 10),
                             relief="groove",
                             bg="blue")

        self.grid_rowconfigure(0, weight=5)
        self.grid_columnconfigure(0, weight=5)
        self.canvas.config(scrollregion=self.canvas.bbox(ALL))
        self.canvas.grid(row=0, column=0, sticky=N + S + E + W)
        self.vscrollbar = Scrollbar(self, orient=VERTICAL)
        self.hscrollbar = Scrollbar(self, orient=HORIZONTAL)
        self.vscrollbar.grid(row=0, column=1, sticky=N + S)
        self.hscrollbar.grid(row=1, column=0, sticky=E + W)
        self.vscrollbar.config(command=self.canvas.yview)
        self.hscrollbar.config(command=self.canvas.xview)
        self.orig_image = image
        self.im = image.overlay(composite).toPIL()
        self.tk_im = ImageTk.PhotoImage(self.im)
        self.canvas_im = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_im)

    def update(self, composite):
        self.im = self.orig_image.overlay(composite).toPIL()
        self.tk_im = ImageTk.PhotoImage(self.im)
        self.canvas_im = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_im)
        scale= self.framescale
        self.framescale = 1.0
        self.set_scale(scale)

    def set_scale(self, scale):
        if abs(scale - self.framescale) < 0.001:
            return
        self.framescale = scale
        self.canvas.delete(self.canvas_im)
        self.tk_im = ImageTk.PhotoImage(
            self.im.resize((int(self.framescale * self.im.size[0]), int(self.framescale * self.im.size[1]))))
        self.canvas_im = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_im)

class CompositeViewer(Frame):

    composite = None

    def __init__(self, master, image, composite):
        Frame.__init__(self, master, bd=2, relief=SUNKEN)
        self.im = image
        self.composite = composite
        compositeResized = imageResizeRelative(self.composite, (500, 500), self.composite.size)
        if self.im is not None:
            imResized = imageResizeRelative(self.im, (500, 500), self.im.size)
            imResized = imResized.overlay(compositeResized)
        else:
            imResized = compositeResized
        self.photo = ImageTk.PhotoImage(imResized.toPIL())
        self.c = Canvas(master, width=compositeResized.size[0] + 10, height=compositeResized.size[1] + 10)
        self.image_on_canvas = self.c.create_image(0, 0, image=self.photo, anchor=NW, tag='imgd')
        self.c.grid(row=0, column=0)

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
        self.f = CompositeViewer(master, self.im, self.composite)
        self.f.grid(row=0)

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