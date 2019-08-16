import os
import tempfile
import tkFileDialog
from Tkinter import *
import tkMessageBox
import json
import requests
import subprocess
import maskgen.maskgen_loader
from maskgen.software_loader import getFileName
from tkinter import ttk
from hp.hp_data import orgs

key = os.path.join(os.path.expanduser("~"), "medifor_ingest.gpg")
hp_settings = os.path.join(os.path.expanduser("~"), ".hpsettings")


class Window(Frame):
    def __init__(self, parent, errors):
        Frame.__init__(self, parent)
        self.parent = parent
        self.parent.title("Settings")
        self.loader = maskgen.maskgen_loader.MaskGenLoader()
        self.setup_window()
        maskgen.maskgen_loader.imageLoaded = False
        if errors:
            tkMessageBox.showerror("Error", "\n".join(errors))

        self.info = {"username": ["Username Field", "Enter your project codename."],
                     "organization": ["Organization Field", "Enter the organization you are affiliated with."],
                     "apiurl": ["API URL Field", "Enter the API URL for the browser."],
                     "busername": ["Browser Username Field", "Enter your browser username."],
                     "bpassword": ["Browser Password Field", "Enter your browser password."],
                     "hporganization": ["HP Organization Field", "Enter your organization abbreviation for the HP Tool."],
                     "uploadfolder": ["Folder Field", "Enter the location you would like to upload the tar files to."
                                                      "\n\"s3://\" is not necessary."],
                     "s3-endpoint": ["AWS endpoint URL field", "Enter your endpoint url if you have one."],
                     "s3-profile": ["AWS profile name field", "Enter your aws profile name if you have multiple config profiles."],
                     "s3-region": ["AWS region field", "Enter your aws region if you have one."],
                     "help": ["Help", "For additional help contact MediFor_Manipulators@partech.com."]}

    def setup_window(self):
        r = 0
        # Info heading
        info_text = Label(text="Enter all of the following\ninformation in order to guarantee\nproper setup of"
                               " the Journaling Tool\nand High Provenance Tool.\nFields marked with an * are"
                               " mandatory")
        info_text.grid(row=r, columnspan=2, pady=5)
        r += 1

        ufile = getFileName("ManipulatorCodeNames.txt")
        if ufile:
            with open(ufile, "r") as names:
                self.valid_usernames = sorted(names.read().splitlines())
        else:
            self.valid_usernames = []
            self.maskgen_button = Button(text="Select Maskgen Folder", command=self.get_maskgen)
            self.maskgen_button.grid(row=r, column=0, columnspan=2)
            r += 1
            self.master.withdraw()
            tkMessageBox.showerror("No Username File", "A username list file could not be found.")
            self.master.deiconify()

        # General Header
        general_label = Label(text="General Setup")
        general_label.grid(row=r, columnspan=2)
        r += 1

        # API URL
        self.apiurl_label = Button(text="API URL*", command=lambda: self.get_info("apiurl"))
        self.apiurl_label.grid(row=r, column=0, padx=10)
        self.apiurl_field = Entry(self.parent)
        self.apiurl_field.insert(0, self.loader.get_key('apiurl', ''))
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

        # Username
        self.username_label = Button(text="Username*", command=lambda: self.get_info("username"))
        self.username_label.grid(row=r, column=0, padx=10)
        self.username_field = ttk.Combobox(values=self.valid_usernames)
        self.username_field.insert(0, self.loader.get_key('username', ''))
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
        self.organization_field.insert(0, self.loader.get_key('organization', ''))
        self.organization_field.grid(row=r, column=1, padx=10)
        r += 1

        # Journal Upload Folder
        self.jt_uploadfolder_label = Button(text="Journal Upload Folder", command=lambda: self.get_info("uploadfolder"))
        self.jt_uploadfolder_label.grid(row=r, column=0, padx=10)
        self.jt_uploadfolder_field = Entry(self.parent)
        self.jt_uploadfolder_field.insert(0, self.loader.get_key('s3info', ''))
        self.jt_uploadfolder_field.grid(row=r, column=1, padx=10)
        r += 1

        # HP Tool Setup
        jt_setup = Label(text="High Provenance Tool Setup")
        jt_setup.grid(row=r, columnspan=2, pady=5)
        r += 1

        # HP Organization
        hporg_button = Button(text="HP Organization*", command=lambda: self.get_info("hporganization"))
        hporg_button.grid(row=r, column=0, padx=10)
        self.hporganization = StringVar()
        self.hporganization.set(self.loader.get_key('hporganization', ''))
        hporg_optionmenu = OptionMenu(None, self.hporganization, *orgs.keys())
        hporg_optionmenu.grid(row=r, column=1, padx=10)
        r += 1

        # High Provenance Upload Folder
        self.hpupload_button = Button(text="HP Upload Folder", command=lambda: self.get_info("uploadfolder"))
        self.hpupload_button.grid(row=r, column=0, padx=10)
        self.hpupload_field = Entry(self.parent)
        self.hpupload_field.insert(0, self.loader.get_key('aws-hp', ''))
        self.hpupload_field.grid(row=r, column=1, padx=10)
        r += 1

        # PRNU Upload Folder
        self.prnuupload_button = Button(text="PRNU Upload Folder", command=lambda: self.get_info("uploadfolder"))
        self.prnuupload_button.grid(row=r, column=0, padx=10)
        self.prnuupload_field = Entry(self.parent)
        self.prnuupload_field.insert(0, self.loader.get_key('aws-prnu', ''))
        self.prnuupload_field.grid(row=r, column=1, padx=10)
        r += 1

        # AWS Profile
        self.profile_button = Button(text="AWS Profile Name", command=lambda: self.get_info("s3-profile"))
        self.profile_button.grid(row=r, column=0, padx=10)
        self.profile_field = Entry(self.parent)
        self.profile_field.insert(0, self.loader.get_key('s3-profile', 'default'))
        self.profile_field.grid(row=r, column=1, padx=10)
        r+=1

        # AWS Endpoint
        self.endpoint_button = Button(text="AWS Endpoint URL", command=lambda: self.get_info("s3-endpoint"))
        self.endpoint_button.grid(row=r, column=0, padx=10)
        self.endpoint_field = Entry(self.parent)
        self.endpoint_field.insert(0, self.loader.get_key('s3-endpoint', ''))
        self.endpoint_field.grid(row=r, column=1, padx=10)
        r += 1

        # AWS Region
        self.region_button = Button(text="AWS Region", command=lambda: self.get_info("s3-region"))
        self.region_button.grid(row=r, column=0, padx=10)
        self.region_field = Entry(self.parent)
        self.region_field.insert(0, self.loader.get_key('s3-region', 'us-east-1'))
        self.region_field.grid(row=r, column=1, padx=10)
        r += 1

        # Submit Button
        submit = Button(text="Submit", command=lambda: self.submit_data())
        submit.grid(row=r, column=0, padx=10, pady=5)

        # Help Button
        help = Button(text="Help", command=lambda: self.get_info("help"))
        help.grid(row=r, column=1, padx=10, pady=5)

    def get_info(self, item):
        tkMessageBox.showinfo(*self.info[item])

    def submit_data(self):
        self.username = self.username_field.get()
        self.organization = self.organization_field.get()
        self.apiurl = self.apiurl_field.get()
        self.busername = self.busername_field.get()
        self.bpassword = self.bpassword_field.get()
        self.jt_uploadfolder = self.jt_uploadfolder_field.get()
        self.hpupload_folder = self.hpupload_field.get()
        self.prnuupload_folder = self.prnuupload_field.get()
        self.s3_profile = self.profile_field.get()
        self.s3_endpoint = self.endpoint_field.get()
        self.s3_region = self.region_field.get()
        self.eemail = self.get_recipient()
        self.full_org = self.hporganization.get() + " (" + orgs[self.hporganization.get()] + ")"

        if not all([self.username, self.organization, self.apiurl, self.busername, self.bpassword,
                    self.hporganization.get()]):
            tkMessageBox.showerror("Missing Fields", "One or more fields are missing required information.")
            return

        if self.username not in self.valid_usernames:
            tkMessageBox.showerror("Invalid Username", "Username not in list of valid usernames.")

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

        try:
            gpg_result = subprocess.Popen(["gpg", "--with-colons", key], stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE).communicate()
        except Exception:
            tkMessageBox.showerror("Error", "There has been an error retrieving the encryption key.")
            return

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
                self.hpupload_folder, "aws-prnu": self.prnuupload_folder, "autosave": "600", "fullorgname":
                self.full_org, "hp-organization": orgs[self.hporganization.get()], "git.branch": branch,
                "s3-endpoint": self.s3_endpoint, "s3-profile": self.s3_profile, "s3-region": self.s3_region}

        self.loader.saveall(data.items())

    def get_maskgen(self):
        maskgen_dir = tkFileDialog.askdirectory()

        if maskgen_dir:
            namefile = os.path.join(maskgen_dir, "resources", "ManipulatorCodeNames.txt")
            if not os.path.isfile(namefile):
                tkMessageBox.showerror("Usernames Not Found", "Could not find username text file at {0}.".format(
                    namefile))
                return
            with open(namefile) as f:
                self.valid_usernames = sorted(f.read().splitlines())
                self.username_field['values'] = self.valid_usernames


def update_user_name():
    import json
    from maskgen.software_loader import getFileName
    property_file = getFileName('project_properties.json')

    if property_file is None:
        return

    with open(property_file, 'r') as f:
        props = json.load(f)
        for prop in props['properties']:
            if prop['name'] == 'username':
                prop['type'] = 'listfromfile:ManipulatorCodeNames.txt'
    with open(property_file, 'w') as f:
        json.dump(props, f, indent=2, encoding='utf-8')


def setup():
    errors = []

    if os.path.isfile(key):
        try:
            key_installed = subprocess.Popen(["gpg", "--list-keys", key], stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, shell=True)
            key_installed.communicate()
            if key_installed.returncode == 2:
                subprocess.Popen(["gpg", "--import", key])
            else:
                os.remove(key)
        except WindowsError as e:
            errors.append("Error encountered while installing encryption key: " + str(e))

    # Set autosave to 600s by default
    maskgen.maskgen_loader.imageLoaded = False
    settings = maskgen.maskgen_loader.MaskGenLoader()
    autosave = settings.get_key("autosave")
    if autosave is None:
        settings.save("autosave", "600")

    if sys.platform.startswith("win"):
        # Will only run if .maskgen2 doesn't exist, so delete the old commands
        if os.path.isfile(os.path.join(os.path.expanduser("~"), "Desktop", "JT.cmd")):
            os.remove(os.path.join(os.path.expanduser("~"), "Desktop", "JT.cmd"))
        with open(os.path.join(os.path.expanduser("~"), "Desktop", "JT.cmd"), "a+") as startjt:
            startjt.writelines(["title Journaling Tool\n", "cd {0}\n".format(os.path.expanduser("~")), "cls\n",
                                "jtui"])
        if os.path.isfile(os.path.join(os.path.expanduser("~"), "Desktop", "HP_Tool.cmd")):
            os.remove(os.path.join(os.path.expanduser("~"), "Desktop", "HP_Tool.cmd"))
        with open(os.path.join(os.path.expanduser("~"), "Desktop", "HP_Tool.cmd"), "a+") as starthp:
            starthp.writelines(["title HP Tool\n", "cd {0}\n".format(os.path.expanduser("~")), "cls\n", "hpgui"])

    update_user_name()
    return errors


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


def main():
    root = Tk()

    if os.path.isfile(hp_settings):
        combine_settings()

    if os.path.isfile(os.path.join(os.path.expanduser("~"), ".maskgen2")):
        # Get a maskgen loader to check if fields are defined
        maskgen.maskgen_loader.imageLoaded = False
        loader = maskgen.maskgen_loader.MaskGenLoader()
        if "apitoken" in loader:
            exit(0)
        if "git.branch" in loader:
            global branch
            branch = loader.get_key("git.branch")
        maskgen.maskgen_loader.imageLoaded = False

    errs = setup()

    Window(root, errs)
    root.wm_resizable(width=FALSE, height=FALSE)
    root.mainloop()


if __name__ == "__main__":
    branch = "master"
    main()
