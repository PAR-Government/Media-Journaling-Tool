import os
from Tkinter import *
import tkMessageBox
import json

import requests


class Window(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)
        self.master = master
        self.master.title("Settings")
        self.setup_window()

    def setup_window(self):
        info_text = Label(text="Please enter all of the following\n information in order to guarantee\nproper setup of"
                               " the Journaling Tool.")
        info_text.grid(row=0, columnspan=2, pady=5)

        # Journaling Username
        self.username_label = Button(text="Username", command=lambda: self.get_info("username"))
        self.username_label.grid(row=1, column=0, padx=10)
        self.username_field = Entry(self.master)
        self.username_field.grid(row=1, column=1, padx=10, sticky=E)

        # Organization
        self.organization_label = Button(text="Organization", command=lambda: self.get_info("organization"))
        self.organization_label.grid(row=2, column=0, padx=10)
        self.organization_field = Entry(self.master)
        self.organization_field.grid(row=2, column=1, padx=10, sticky=E)

        # API URL
        self.apiurl_label = Button(text="API URL", command=lambda: self.get_info("apiurl"))
        self.apiurl_label.grid(row=3, column=0, padx=10)
        self.apiurl_field = Entry(self.master)
        self.apiurl_field.grid(row=3, column=1, padx=10)

        # Browser Username
        self.busername_label = Button(text="Browser Username", command=lambda: self.get_info("busername"))
        self.busername_label.grid(row=4, column=0, padx=10)
        self.busername_field = Entry(self.master)
        self.busername_field.grid(row=4, column=1, padx=10)

        # Browser Password
        self.bpassword_label = Button(text="Browser Password", command=lambda: self.get_info("bpassword"))
        self.bpassword_label.grid(row=5, column=0, padx=10)
        self.bpassword_field = Entry(self.master, show="*")
        self.bpassword_field.grid(row=5, column=1, padx=10)

        # Upload Folder
        self.uploadfolder_label = Button(text="Upload Folder", command=lambda: self.get_info("uploadfolder"))
        self.uploadfolder_label.grid(row=6, column=0, padx=10)
        self.uploadfolder_field = Entry(self.master)
        self.uploadfolder_field.grid(row=6, column=1, padx=10)

        # Submit Button
        submit = Button(text="Submit", command=lambda: self.submit_data())
        submit.grid(row=7, column=0, padx=10, pady=5)

        # Help Button
        help = Button(text="Help", command=lambda: self.get_info("help"))
        help.grid(row=7, column=1, padx=10, pady=5)

    def get_info(self, item):
        if item == "username":
            tkMessageBox.showinfo("Username Field", "Please enter your project codename.")
        elif item == "organization":
            tkMessageBox.showinfo("Organization Field", "Please enter the organization you are affiliated with.")
        elif item == "apiurl":
            tkMessageBox.showinfo("API URL Field", "Please enter the API URL for the browser.")
        elif item == "busername":
            tkMessageBox.showinfo("Browser Username Field", "Please enter your browser username.")
        elif item == "bpassword":
            tkMessageBox.showinfo("Browser Password Field", "Please enter your browser password.")
        elif item == "uploadfolder":
            tkMessageBox.showinfo("Folder Field", "Please enter the location you would like to upload to folder to."
                                                  "\n\"s3://\" is not necessary.")
        elif item == "help":
            tkMessageBox.showinfo("Help", "For additional help contact MediFor_Manipulators@partech.com.")

    def submit_data(self):
        self.username = self.username_field.get()
        self.organization = self.organization_field.get()
        self.apiurl = self.apiurl_field.get()
        self.busername = self.busername_field.get()
        self.bpassword = self.bpassword_field.get()
        self.uploadfolder = self.uploadfolder_field.get()

        if not all([self.username, self.organization, self.uploadfolder, self.apiurl, self.busername, self.bpassword]):
            tkMessageBox.showerror("Missing Fields", "One or more fields are missing required information.")
            return

        self.apitoken = self.get_token(self.apiurl, self.busername, self.bpassword)

        if len(list(self.apitoken.split(" "))) == 1:
            create_json(self.username, self.organization, self.uploadfolder, self.apiurl, self.apitoken)
            tkMessageBox.showinfo("Success!", "Configuration file for {0} has been successfully created!".format(
                self.username))
            self.master.destroy()

        else:
            tkMessageBox.showerror("Invalid API Token", self.apitoken)

    def get_token(self, url, username, password):
        try:
            url = url[:-1] if url.endswith('/') else url
            headers = {'Content-Type': 'application/json'}
            url = url + '/login/'
            data = '{"username": "' + username + '","password":"' + password + '"}'
            response = requests.post(url, data=data, headers=headers)
            if response.status_code != requests.codes.ok:
                return "Error calling external service {} : {}".format(url, str(response.content))
            else:
                r = json.loads(response.content)
                return r['key']
        except Exception as e:
            return "Error calling external service: {} : {}".format(url, str(e.message))


def create_json(username, organization, s3info, apiurl, apitoken):
    with open(os.path.expanduser("~\\.maskgen2"), "w") as f:
        data = {"username": username, "apitoken": apitoken, "organization": organization,
                "s3info": s3info, "apiurl": apiurl}
        json_data = json.dumps(data, indent=4)

        f.write(json_data)

    return


if __name__ == "__main__":
    if os.path.isfile(os.path.expanduser("~\\Desktop\\JT.cmd")):
        os.remove(os.path.expanduser("~\\Desktop\\JT.cmd"))
    with open(os.path.expanduser("~\\Desktop\\JT.cmd"), "a+") as startjt:
        startjt.writelines(["title Journaling Tool\n", "cd {0}\n".format(os.path.expanduser("~")), "cls\n", "jtui"])
    if os.path.isfile(os.path.expanduser("~\\Desktop\\HP_Tool.cmd")):
        os.remove(os.path.expanduser("~\\Desktop\\HP_Tool.cmd"))
    with open(os.path.expanduser("~\\Desktop\\HP_Tool.cmd"), "a+") as starthp:
        starthp.writelines(["title HP Tool\n", "cd {0}\n".format(os.path.expanduser("~")), "cls\n", "hpgui"])

    try:
        open(os.path.expanduser("~/.maskgen2"))
        exit()
    except IOError:
        pass
    root = Tk()
    Window(root)
    root.wm_resizable(width=FALSE, height=FALSE)
    root.mainloop()