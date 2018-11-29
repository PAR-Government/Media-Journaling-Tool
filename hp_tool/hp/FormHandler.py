import os
import shutil
import tkFileDialog
import tkMessageBox
from Tkinter import *
from PIL import Image, ImageTk
from maskgen import tool_set, ImageWrapper
from maskgen.ui.ui_tools import ScrollableListbox
import PyPDF2
from maskgen.tool_set import fileType


class FormSelector(Toplevel):
    def __init__(self, form_directory, listvariable, table, master=None):
        Toplevel.__init__(self, master)
        self.master = master
        self.formdir = form_directory
        self.table = table

        if not os.path.exists(form_directory):
            os.mkdir(form_directory)

        self.listvar = listvariable
        self.create_widgets()
        self.wm_resizable(False, False)

    def create_widgets(self):
        Label(self, text="Available Forms").grid(row=0, column=0, columnspan=2)

        self.available = ScrollableListbox(self, 16, 40)
        self.available.grid(row=1, column=0, columnspan=2, rowspan=2, sticky=N + S)
        self.available.get_listbox().bind("<Triple-Button-1>", self.delete)
        self.available.get_listbox().bind("<<ListboxSelect>>", self.update_picture)
        for i in self.listvar:
            self.available.get_listbox().insert(END, i)

        Label(self, text="Picture").grid(row=0, column=3)
        self.photo = Canvas(self, width=250, height=250)
        self.photo.grid(row=1, column=3, rowspan=2)

        add_avail = Button(self, text="Add Form", command=self.add)
        add_avail.grid(row=3, column=0, sticky=E)

        delete_avail = Button(self, text="Remove Form", command=self.delete)
        delete_avail.grid(row=3, column=1, sticky=W)

        finish_controls = Frame(self)
        finish_controls.grid(row=4, column=0, columnspan=4)

        ok = Button(finish_controls, text="Save", command=self.submit)
        ok.grid(row=0, column=0, sticky=E)

        cancel = Button(finish_controls, text="Exit", command=self.destroy)
        cancel.grid(row=0, column=1, sticky=W)

    def add(self):
        tkMessageBox.showinfo("Select Form", "Select the PDF of the signed release form.", master=self)
        form = tkFileDialog.askopenfilename(filetypes=[("Adobe Acrobat Document (PDF)", "*.pdf")],
                                            initialdir=os.path.expanduser("~"), title="Add Release Form")
        path, name = os.path.split(os.path.splitext(form)[0])
        name = name.title()
        if len(name.split(" ")) not in [2, 3]:
            tkMessageBox.showerror("Error", "Release forms must be named under the name of the individual that signed "
                                            "it (ex. John Smith's release form would be \"John Smith.pdf\")",
                                   master=self)
            return

        pdf_page_count = PyPDF2.PdfFileReader(form).getNumPages()

        if pdf_page_count == 1:
            tkMessageBox.showinfo("Select Image", "Select an image of the individual whose form was previously "
                                                  "selected.", master=self)
            images = [tkFileDialog.askopenfilename(filetypes=tool_set.imagefiletypes, initialdir=path,
                                                   title="Add Image", master=self)]
        else:
            tkMessageBox.showinfo("Select Image Directory", "Select the directory containing an image for each person "
                                                            "in the release form collection.")

            # Continuously retry until we get the right count or just give up
            retry = True
            while retry:
                image_dir = tkFileDialog.askdirectory(title="Select Image Directory",
                                                      initialdir=os.path.expanduser("~"), master=self)
                images = [os.path.join(image_dir, x) for x in os.listdir(image_dir) if fileType(
                    os.path.join(image_dir, x)) == "image"]

                # check count
                if len(images) != pdf_page_count:
                    retry = tkMessageBox.askretrycancel("PDF/Image Mismatch",
                                                        "The image directory must contain one image for every "
                                                        "release form.  {0} release forms were found while {1} "
                                                        "images were found.".format(pdf_page_count,
                                                                                    len(images)), master=self)
                    if not retry:
                        return
                else:
                    retry = False

        person_dir = os.path.join(self.formdir, name)
        if not os.path.exists(person_dir):
            os.mkdir(person_dir)
        shutil.copy2(form, person_dir)

        for im in images:
            shutil.copy2(im, person_dir)

        self.listvar.append(name)
        self.available.get_listbox().insert(END, name)
        return

    def delete(self, event=None):
        col = self.table.get_col_by_name("HP-ReleaseForms")
        rows = self.table.rows
        vals = []
        selected = self.available.get_listbox().get(ACTIVE)

        for i in range(0, rows):
            forms = self.table.model.getValueAt(i, col)
            if forms != "":
                vals.append((i, forms.split(", ")))
        if vals:
            tkMessageBox.askyesno("Warning", "Some videos have release forms attached.  Continuing will remove {0}'s "
                                             "form from all media that it is currently applied to.  Are you sure you "
                                             "want to continue?".format(selected), icon=tkMessageBox.WARNING)

            for i in vals:
                if selected in i[1]:
                    i[1].pop(i[1].index(selected))
                    self.table.model.setValueAt(", ".join(i[1]), i[0], col)
            self.table.redraw()

        self.listvar.pop(self.listvar.index(selected))
        self.available.get_listbox().delete(ACTIVE)
        shutil.rmtree(os.path.join(self.formdir, selected))

    def update_picture(self, event=None):
        selection = event.widget.curselection()
        if selection == ():
            return

        name = event.widget.get(selection[0])
        self.photo.delete("all")
        files_in_dir = os.listdir(os.path.join(self.formdir, name))
        files_in_dir.remove(name + ".pdf")
        img_path = os.path.join(self.formdir, name, files_in_dir[0])
        with Image.open(img_path) as f:
            f.thumbnail((250, 250))
            img = ImageTk.PhotoImage(f)
        self.photo.image = img
        self.photo.create_image(0, 0, image=img, anchor=NW)

    def submit(self):
        self.listvar = sorted(self.available.get_listbox().get(0, END))
        self.destroy()
