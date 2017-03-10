from tkinter import *
from PIL import ImageTk

class PictureEditor(Frame):
    box = (0,0,0,0)
    def __init__(self,master, image, box):
        Frame.__init__(self,master,bd=2,relief=SUNKEN)
        self.x = 0
        self.y = 0
        self.box = box

        self.canvas = Canvas(self,  cursor="cross", width=500, height=500, confine=True,
                             scrollregion=(0,0,image.size[1],image.size[0]),
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

        self.canvas.bind("<ButtonPress-1>",     self.on_button_press)
        self.canvas.bind("<B1-Motion>",     self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>",     self.on_button_release)
        self.canvas.bind("<Leave>", self.on_button_leave)
        self.canvas.bind("<Enter>", self.on_button_enter)
        self.canvas.bind("<Double-Button-1>",     self.on_double_click)
        self.rect = None
        self.text = None
        self.start_x = None
        self.start_y = None
        self.boxdata = StringVar()
        self.setBoxData()
        self.label = Label(self, textvariable=self.boxdata, justify=CENTER)
        self.label.grid(row=1, column=0, sticky='EW', padx=10)

        self.im = image
        self.wazil,self.lard=self.im.size
        self.tk_im = ImageTk.PhotoImage(self.im)
        self.canvas.create_image(0,0,anchor="nw",image=self.tk_im)
        self.rect = self.canvas.create_rectangle(box[0], box[1], box[2], box[3],
                                                 outline='blue')  # since it's only created once it always remains at the bottom

    out_of_scope = 1

    def setBoxData(self):
        self.boxdata.set(str(self.box))

    def on_button_leave(self, event):
        self.out_of_scope = 2
        #print "out_of_scope....", self.out_of_scope

    def on_button_enter(self, event):
        #print("entering...")
        self.out_of_scope = 1

    def on_double_click(self, event):
        #print("double click")
        pass

    def on_button_press(self, event):
        # save mouse drag start position
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

        # create rectangle if not yet exist
        if not self.rect:
            if self.out_of_scope == 1:
                self.rect = self.canvas.create_rectangle(self.x, self.y, 1, 1, outline='blue') #since it's only created once it always remains at the bottom

    def get_out_of_scope(self, x, y):
        return self.out_of_scope

    def on_move_press(self, event):
        curX = self.canvas.canvasx(event.x)
        curY = self.canvas.canvasy(event.y)
        var=self.get_out_of_scope(event.x, event.y)
        print(var, event.x, event.y)
        if var == 1:
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
            if event.x > 0.9*w:
                self.canvas.xview_scroll(1, 'units')
            elif event.x < 0.1*w:
                self.canvas.xview_scroll(-1, 'units')
            if event.y > 0.9*h:
                self.canvas.yview_scroll(1, 'units')
            elif event.y < 0.1*h:
                self.canvas.yview_scroll(-1, 'units')
    # expand rectangle as you drag the mouse
            self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        self.box = (int(self.start_x),int(self.start_y),int(event.x),int(event.y))
        self.setBoxData()
        pass