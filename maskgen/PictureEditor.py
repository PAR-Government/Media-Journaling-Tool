# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from Tkinter import *
from PIL import ImageTk


class PictureEditor(Frame):
    box = (0, 0, 0, 0)
    polygon_item = None
    framescale = 1.0
    corner = 0

    def __init__(self, master, image, box, angle=0):
        Frame.__init__(self, master, bd=2, relief=SUNKEN)
        self.x = 0
        self.y = 0
        self.box = box

        self.canvas = Canvas(self, cursor="cross", width=500, height=500, confine=True,
                             scrollregion=(0, 0, image.size[0] * 1.1, image.size[1] * 1.1),
                             relief="groove",
                             bg="white")

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

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Leave>", self.on_button_leave)
        self.canvas.bind("<Enter>", self.on_button_enter)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.rect = None
        self.text = None
        self.boxdata = StringVar()

        self.label = Label(self, textvariable=self.boxdata, justify=CENTER)
        self.label.grid(row=2, column=0, sticky='EW', padx=10)

        self.im = image
        self.wazil, self.lard = self.im.size
        self.tk_im = ImageTk.PhotoImage(self.im)
        self.canvas_im = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_im)
        self.rect = self.canvas.create_rectangle(box[0], box[1], box[2], box[3],
                                                 outline='blue',
                                                 tags="rect")  # since it's only created once it always remains at the bottom
        self.angle = 0
        if angle != 0:
            self.rotate(angle)
        self.setBoxData()

    out_of_scope = 1

    def set_scale(self, scale):
        if abs(scale - self.framescale) < 0.001:
            return
        self.framescale = scale
        self.canvas.delete(self.canvas_im)
        self.tk_im = ImageTk.PhotoImage(
            self.im.resize((int(self.framescale * self.im.size[0]), int(self.framescale * self.im.size[1]))))
        self.canvas_im = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_im)
        (x0, y0, x1, y1) = tuple(self.box)
        x0 = int(float(x0) * self.framescale)
        y0 = int(float(y0) * self.framescale)
        x1 = int(float(x1) * self.framescale)
        y1 = int(float(y1) * self.framescale)
        if self.rect:
            self.canvas.coords(self.rect, x0, y0, x1, y1)
            self.canvas.tag_raise('rect')
        if self.angle != 0:
            self.rotate(self.angle)
            self.canvas.tag_raise('rect')

    def setBoxData(self):
        # bounds = self.canvas.bbox(self.canvas_im)  # returns a tuple like (x1, y1, x2, y2)
        ## width = bounds[2] - bounds[0]
        # height = bounds[3] - bounds[1]
        upper_x = min(self.box[0], self.box[2])
        upper_y = min(self.box[1], self.box[3])
        lower_x = max(self.box[0], self.box[2])
        lower_y = max(self.box[1], self.box[3])

        ratio = 1.0 / self.framescale
        self.box = (max(0, int(upper_x * ratio)),
                    max(0, int(upper_y * ratio)),
                    min(int(lower_x * ratio), self.wazil),
                    min(int(lower_y * ratio), self.lard))

        self.boxdata.set(str(self.box))

    def on_button_leave(self, event):
        self.out_of_scope = 2

    def on_button_enter(self, event):
        self.out_of_scope = 1

    def on_double_click(self, event):
        pass

    def getCorners(self):
        if self.rect is not None:
            coords = self.canvas.coords(self.rect)
            corners = [(coords[0], coords[1], 0), (coords[0], coords[3], 1),
                       (coords[2], coords[3], 2), (coords[2], coords[1], 3)]
            return corners
        return []

    def updateCorners(self, x, y):
        coords = self.canvas.coords(self.rect)
        upper_choices = [
            (x, y),
            (x, coords[1]),
            (coords[0], coords[1]),
            (coords[0], y)
        ]
        lower_choices = [
            (coords[2], coords[3]),
            (coords[2], y),
            (x, y),
            (x, coords[3])
        ]
        self.canvas.coords(self.rect,
                           upper_choices[self.corner][0],
                           upper_choices[self.corner][1],
                           lower_choices[self.corner][0],
                           lower_choices[self.corner][1])

    def on_button_press(self, event):
        # save mouse drag start position
        click_position_x = self.canvas.canvasx(event.x)
        click_position_y = self.canvas.canvasy(event.y)
        self.corner = 0
        found_corner = False
        rebuild_rect = True
        for corner in self.getCorners():
            if abs(click_position_x - corner[0]) <= 5 and \
                            abs(click_position_y - corner[1]) < 5:
                self.corner = corner[2]
                found_corner = True
                rebuild_rect = False
                break

        if not found_corner:
            self.corner = 2

        rebuild_rect = (self.out_of_scope == 1) and rebuild_rect

        if self.polygon_item:
            self.canvas.delete(self.polygon_item)
            self.polygon_item = None

        if rebuild_rect:
            if not self.rect:
                self.rect = self.canvas.create_rectangle(click_position_x, click_position_y,
                                                         click_position_x + 1, click_position_y + 1,
                                                         outline='blue', tags='rect')
            else:
                self.canvas.coords(self.rect, click_position_x, click_position_y,
                                   click_position_x + 1, click_position_y + 1)

    def get_out_of_scope(self, x, y):
        return self.out_of_scope

    def on_move_press(self, event):
        curX = self.canvas.canvasx(event.x)
        curY = self.canvas.canvasy(event.y)
        var = self.get_out_of_scope(event.x, event.y)
        if var == 1:
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
            if event.x > 0.95 * w:
                self.canvas.xview_scroll(1, 'units')
            elif event.x < 0.05 * w:
                self.canvas.xview_scroll(-1, 'units')
            if event.y > 0.95 * h:
                self.canvas.yview_scroll(1, 'units')
            elif event.y < 0.05 * h:
                self.canvas.yview_scroll(-1, 'units')
             # expand rectangle as you drag the mouse
            self.updateCorners(curX, curY)

    def on_button_release(self, event):
        coords = self.canvas.coords(self.rect)
        self.box = (int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3]))
        self.setBoxData()
        pass

    def rotate(self, angle):
        import math
        scale = self.framescale if self.framescale <= 1.0 else 1.0
        scaled_box = [scale * self.box[0], scale * self.box[1], scale * self.box[2], scale * self.box[3]]
        self.angle = angle
        # calculate current angle relative to initial angle
        if angle == 0:
            if self.polygon_item:
                self.canvas.delete(self.polygon_item)
                self.polygon_item = None
                if not self.rect:
                    self.rect = self.canvas.create_rectangle(scaled_box[0], scaled_box[1],
                                                             scaled_box[2], scaled_box[3],
                                                             outline='blue', tags='rect')
            return
        rangle = math.radians(angle)
        if self.rect:
            self.canvas.delete(self.rect)
            self.rect = None
        center = (scaled_box[0] + (scaled_box[2] - scaled_box[0]) / 2,
                  scaled_box[1] + (scaled_box[3] - scaled_box[1]) / 2)
        newxy = []
        xy = [(scaled_box[0], scaled_box[1]), (scaled_box[2], scaled_box[1]), (scaled_box[2], scaled_box[3]),
              (scaled_box[0], scaled_box[3])]
        if self.polygon_item is None:
            self.polygon_item = self.canvas.create_polygon(xy, outline='blue', fill='', tags="rect")
        for x, y in xy:
            newX = center[0] + math.cos(rangle) * (x - center[0]) - math.sin(rangle) * (y - center[1])
            newY = center[1] + math.sin(rangle) * (x - center[0]) + math.cos(rangle) * (y - center[1])
            newxy.append(newX)
            newxy.append(newY)
        self.canvas.coords(self.polygon_item, *newxy)
