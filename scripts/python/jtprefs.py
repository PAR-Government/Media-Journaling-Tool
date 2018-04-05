import os
from Tkinter import *
import tkMessageBox
import json
import requests
import subprocess
import maskgen.maskgen_loader

key = os.path.join(os.path.expanduser("~"), "medifor_ingest.gpg")
hp_settings = os.path.join(os.path.expanduser("~"), ".hpsettings")


class Window(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent
        self.parent.title("Settings")
        self.setup_window()
        maskgen.maskgen_loader.imageLoaded = False
        self.loader = maskgen.maskgen_loader.MaskGenLoader()

    def setup_window(self):
        r = 0
        # Info heading
        info_text = Label(text="Enter all of the following\ninformation in order to guarantee\nproper setup of"
                               " the Journaling Tool\nand High Provenance Tool.\nFields marked with an * are"
                               " mandatory")
        info_text.grid(row=r, columnspan=2, pady=5)
        r += 1

        # General Header
        general_label = Label(text="General Setup")
        general_label.grid(row=r, columnspan=2)
        r += 1

        # API URL
        self.apiurl_label = Button(text="API URL*", command=lambda: self.get_info("apiurl"))
        self.apiurl_label.grid(row=r, column=0, padx=10)
        self.apiurl_field = Entry(self.parent)
        self.apiurl_field.grid(row=r, column=1, padx=10)
        r += 1

        # Browser Username
        self.busername_label = Button(text="Browser Username*", command=lambda: self.get_info("busername"))
        self.busername_label.grid(row=r, column=0, padx=10)
        self.busername_field = Entry(self.parent)
        self.busername_field.grid(row=r, column=1, padx=10)
        r += 1

        # Browser Password
        self.bpassword_label = Button(text="Browser Password*", command=lambda: self.get_info("bpassword"))
        self.bpassword_label.grid(row=r, column=0, padx=10)
        self.bpassword_field = Entry(self.parent, show="*")
        self.bpassword_field.grid(row=r, column=1, padx=10)
        r += 1

        # Journaling Username
        self.username_label = Button(text="Username*", command=lambda: self.get_info("username"))
        self.username_label.grid(row=r, column=0, padx=10)
        self.username_field = Entry(self.parent)
        self.username_field.grid(row=r, column=1, padx=10)
        r += 1

        # JT Setup
        jt_setup = Label(text="Journaling Tool Setup")
        jt_setup.grid(row=r, columnspan=2, pady=5)
        r += 1

        # Organization
        self.organization_label = Button(text="Organization*", command=lambda: self.get_info("organization"))
        self.organization_label.grid(row=r, column=0, padx=10)
        self.organization_field = Entry(self.parent)
        self.organization_field.grid(row=r, column=1, padx=10)
        r += 1

        # Journal Upload Folder
        self.jt_uploadfolder_label = Button(text="Journal Upload Folder", command=lambda: self.get_info("uploadfolder"))
        self.jt_uploadfolder_label.grid(row=r, column=0, padx=10)
        self.jt_uploadfolder_field = Entry(self.parent)
        self.jt_uploadfolder_field.grid(row=r, column=1, padx=10)
        r += 1

        # HP Tool Setup
        jt_setup = Label(text="High Provenance Tool Setup")
        jt_setup.grid(row=r, columnspan=2, pady=5)
        r += 1

        # High Provenance Upload Folder
        self.hpupload_button = Button(text="HP Upload Folder", command=lambda: self.get_info("uploadfolder"))
        self.hpupload_button.grid(row=r, column=0, padx=10)
        self.hpupload_field = Entry(self.parent)
        self.hpupload_field.grid(row=r, column=1, padx=10)
        r += 1

        # PRNU Upload Folder
        self.prnuupload_button = Button(text="PRNU Upload Folder", command=lambda: self.get_info("uploadfolder"))
        self.prnuupload_button.grid(row=r, column=0, padx=10)
        self.prnuupload_field = Entry(self.parent)
        self.prnuupload_field.grid(row=r, column=1, padx=10)
        r += 1

        # Submit Button
        submit = Button(text="Submit", command=lambda: self.submit_data())
        submit.grid(row=r, column=0, padx=10, pady=5)

        # Help Button
        help = Button(text="Help", command=lambda: self.get_info("help"))
        help.grid(row=r, column=1, padx=10, pady=5)

    def get_info(self, item):
        if item == "username":
            tkMessageBox.showinfo("Username Field", "Enter your project codename.")
        elif item == "organization":
            tkMessageBox.showinfo("Organization Field", "Enter the organization you are affiliated with.")
        elif item == "apiurl":
            tkMessageBox.showinfo("API URL Field", "Enter the API URL for the browser.")
        elif item == "busername":
            tkMessageBox.showinfo("Browser Username Field", "Enter your browser username.")
        elif item == "bpassword":
            tkMessageBox.showinfo("Browser Password Field", "Enter your browser password.")
        elif item == "uploadfolder":
            tkMessageBox.showinfo("Folder Field", "Enter the location you would like to upload the tar files to."
                                                  "\n\"s3://\" is not necessary.")
        elif item == "help":
            tkMessageBox.showinfo("Help", "For additional help contact MediFor_Manipulators@partech.com.")

    def submit_data(self):
        self.username = self.username_field.get()
        self.organization = self.organization_field.get()
        self.apiurl = self.apiurl_field.get()
        self.busername = self.busername_field.get()
        self.bpassword = self.bpassword_field.get()
        self.jt_uploadfolder = self.jt_uploadfolder_field.get()
        self.hpupload_folder = self.hpupload_field.get()
        self.prnuupload_folder = self.prnuupload_field.get()
        self.eemail = self.get_recipient()

        if not all([self.username, self.organization, self.apiurl, self.busername, self.bpassword]):
            tkMessageBox.showerror("Missing Fields", "One or more fields are missing required information.")
            return
        elif not self.eemail:
            ans = tkMessageBox.askyesno("No Recipient", "The encryption file was not found.  You can continue with"
                                                        " out an encryption file, but the HP Tool media will not be"
                                                        " ingested.  Would you like to continue?")
            if not ans:
                return
            self.eemail = ""

        self.apitoken = self.get_token()

        if self.apitoken:
            self.create_json()
            tkMessageBox.showinfo("Success!", "Configuration file for {0} has been successfully created!".format(
                self.username))
            if os.path.isfile(key):
                os.remove(key)
            self.parent.destroy()

    def get_recipient(self):
        if not os.path.isfile(key):
            return None

        gpg_result = subprocess.Popen(["gpg", "--with-colons", key], stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE).communicate()

        for line in gpg_result[0].split("\n"):
            if line.startswith("uid"):
                email = line.split("<")[1].split(">")[0]
                return email
        return None

    def get_token(self):
        try:
            url = self.apiurl[:-1] if self.apiurl.endswith('/') else self.apiurl
            headers = {'Content-Type': 'application/json'}
            url = url + '/login/'
            data = '{"username": "' + self.busername + '","password":"' + self.bpassword + '"}'
            response = requests.post(url, data=data, headers=headers)
            if response.status_code != requests.codes.ok:
                tkMessageBox.showerror("Invalid API Token", "Error calling external service {0} : {1}".format(
                    url, str(response.content)))
                return None
            else:
                r = json.loads(response.content)
                return r['key']
        except Exception as e:
            return "Error calling external service: {0} : {1}".format(url, str(e.message))

    def create_json(self):
        data = {"username": self.username, "apitoken": self.apitoken, "organization": self.organization,
                "s3info": self.jt_uploadfolder, "apiurl": self.apiurl, "archive_recipient": self.eemail, "aws-hp":
                    self.hpupload_folder, "aws-prnu": self.prnuupload_folder}
        self.loader.saveall(data.items())


def setup():
    if os.path.isfile(key):
        key_installed = subprocess.Popen(["gpg", "--list-keys", key], stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE).communicate()
        if not key_installed[0]:
            subprocess.Popen(["gpg", "--import", key])
            print(key_installed[0])
        else:
            os.remove(key)

    if os.path.isfile(os.path.join(os.path.expanduser("~"), "Desktop", "JT.cmd")):
        os.remove(os.path.join(os.path.expanduser("~"), "Desktop", "JT.cmd"))
    with open(os.path.join(os.path.expanduser("~"), "Desktop", "JT.cmd"), "a+") as startjt:
        startjt.writelines(["title Journaling Tool\n", "cd {0}\n".format(os.path.expanduser("~")), "cls\n", "jtui"])
    if os.path.isfile(os.path.join(os.path.expanduser("~"), "Desktop", "HP_Tool.cmd")):
        os.remove(os.path.join(os.path.expanduser("~"), "Desktop", "HP_Tool.cmd"))
    with open(os.path.join(os.path.expanduser("~"), "Desktop", "HP_Tool.cmd"), "a+") as starthp:
        starthp.writelines(["title HP Tool\n", "cd {0}\n".format(os.path.expanduser("~")), "cls\n", "hpgui"])


def combine_settings():
    maskgen.maskgen_loader.imageLoaded = False
    hp_loader = maskgen.maskgen_loader.MaskGenLoader(hp_settings)
    hp_keys = {}

    for hp_key in hp_loader.__iter__():
        hp_keys[hp_key] = hp_loader.get_key(hp_key)

    conversions = {"aws": "aws-hp", "aws-prnu": "aws-prnu", "archive_recipient":
                   "archive_recipient", "inputdir": "inputdir", "outputdir": "outputdir", "organization":
                   "hp-organization", "seq": "seq"}

    maskgen.maskgen_loader.imageLoaded = False
    jt_loader = maskgen.maskgen_loader.MaskGenLoader()
    jt_keys = {}

    for jt_key in jt_loader.__iter__():
        jt_keys[jt_key] = jt_loader.get_key(jt_key)

    for k, v in hp_keys.items():
        if k in conversions.keys():
            jt_keys[conversions[k]] = hp_keys[k]
        if k == "metadata":
            for mk, mv in v.items():
                jt_keys[mk] = mv

    jt_loader.saveall(jt_keys.items())

    os.remove(hp_settings)


if __name__ == "__main__":
    setup()

    if os.path.isfile(hp_settings):
        combine_settings()

    if os.path.isfile(os.path.join(os.path.expanduser("~"), ".maskgen2")):
        exit(0)

    root = Tk()
    Window(root)
    root.wm_resizable(width=FALSE, height=FALSE)
    root.mainloop()
