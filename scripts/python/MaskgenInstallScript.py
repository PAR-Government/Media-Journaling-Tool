import os
import subprocess
from Tkinter import *
import tkMessageBox
import tkFileDialog
import tkSimpleDialog
import git
import shutil
from datetime import datetime
from pkg_resources import DistributionNotFound


def write_log(msg):
    with open(os.path.join(os.path.expanduser("~"), "install_log.log"), "a+") as f:
        f.write(msg + "\n")


def get_maskgen_dir():
    def ask_dir():
        select_message = "If you have already downloaded maskgen, select the root maskgen folder.  If you have not " \
                         "already downloaded maskgen, select the directory you would like to install maskgen to.\n" \
                         "Note: A maskgen folder will automatically be created in your selected directory if maskgen " \
                         "has not been downloaded."
        if sys.platform.startswith("darwin"):
            tkMessageBox.showinfo("Select Directory", select_message)
        mdir = tkFileDialog.askdirectory(title=select_message, initialdir=os.path.join(os.path.expanduser("~"),
                                                                                       "Documents"))
        return mdir

    try:
        import maskgen
        # returns location/maskgen/maskgen/__init__.py
        # we want just location
        d = os.path.split(os.path.dirname(maskgen.__file__))[0]
        return True, d
    except (ImportError, DistributionNotFound):
        d = check_frequents()
        if d is not None:
            return True, d
        else:
            retry = True
            while retry:
                d = ask_dir()
                if os.path.isdir(d):
                    if os.path.isdir(os.path.join(d, "maskgen")) and not \
                            os.path.isdir(os.path.join(d, "maskgen", "maskgen")):
                        return True, d
                    elif os.path.isdir(os.path.join(d, "maskgen", "maskgen")):
                        return True, os.path.join(d, "maskgen")
                    else:
                        if os.path.split(d)[1] == "maskgen":
                            return d
                        else:
                            return False, os.path.join(d, "maskgen")
                retry = tkMessageBox.askretrycancel("Invalid Directory", "{0} is an invalid directory.".format(d))

            # This only hits if the user gives up
            m = "Fatal Error: Failed to select a valid maskgen installation target directory."
            print(m)
            write_log(m)
            exit(1)


def run_uninstalls():
    dnull = open(os.devnull, "w")
    subprocess.Popen(["python", "-m", "pip", "uninstall", "rawphoto-wrapper", "-y"], stdout=dnull, stderr=dnull).wait()
    dnull.close()


def install_setuptools():
    print("Attempting to {0:.<50s}".format("install setuptools")),
    os.chdir(os.path.join(maskgen_dir, "setuptools-version"))

    if os.path.isdir(os.path.join(os.getcwd(), "build")) and os.path.isdir(os.path.join(os.getcwd(), "dist")):
        print("skipped")
        write_log("Skipping setuptools install")
        return

    py = subprocess.Popen(["python", "setup.py", "install"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = py.communicate()
    if py.returncode != 0:
        m = "Failed to install setuptools:\n" + d[1]
        print("failed")
    else:
        m = "Successfully installed setuptools"
        print("success")
    write_log(m)


def install_jt():
    print("Attempting to {0:.<50s}".format("install JT")),
    os.chdir(maskgen_dir)

    py = subprocess.Popen(["python", "setup.py", "sdist"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = py.communicate()

    if py.returncode != 0:
        exit(0)
        write_log("Failed to run JT setup.py:\n" + d[1] + "\nSkipping JT install")
        print("failed")
        return False
    else:
        write_log("Successfully ran JT python setup.py")

    pi = subprocess.Popen(["python", "-m", "pip", "install", "-e", "."],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = pi.communicate()
    if pi.returncode != 0:
        write_log("Failed to install JT: \n" + d[1])
        print("failed")
        return False
    else:
        write_log("Successfully ran JT install")
        print("success")
        return True


def install_hp():
    os.chdir(os.path.join(maskgen_dir, "hp_tool"))

    print("Attempting to {0:.<50s}".format("install HP Tool")),
    py = subprocess.Popen(["python", "setup.py", "install"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = py.communicate()
    if py.returncode != 0:
        m = "Failed to run HP Tool setup.py:\n" + d[1]
    else:
        m = "Successfully ran HP Tool setup.py"
    write_log(m)

    pi = subprocess.Popen(["python", "-m", "pip", "install", "-e", "."],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = pi.communicate()
    if pi.returncode != 0:
        m = "Failed to pip install HP Tool:\n" + d[1]
    else:
        m = "Successfully ran HP Tool pip install"
    write_log(m)

    if pi.returncode != 0 or py.returncode != 0:
        print("failed")
    else:
        print("success")


def install_trello():
    os.chdir(os.path.join(maskgen_dir, "notify_plugins", "trello_plugin"))
    print("Attempting to {0:.<50s}".format("install Trello API Plugin")),
    py = subprocess.Popen(["python", "setup.py", "install"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = py.communicate()
    if py.returncode != 0:
        m = "Failed to install Trello API Plugin:\n" + d[1]
        print("failed")
    else:
        m = "Successfully installed Trello API Plugin"
        print("success")
    write_log(m)


def empty_maskgen_dir():
    try:
        shutil.rmtree(maskgen_dir)
    except Exception:
        # Can't except WindowsError on Mac
        winerr = "Error removing previous non-git maskgen installation.  Close all programs in the maskgen directory " \
                 "(including the file explorer) and try again."
        tkMessageBox.showerror("Installation Error", winerr)
        write_log(winerr)
        exit(1)


def clone():
    print("{0:.<64s}".format("Cloning maskgen.  This may take a while.")),

    if os.path.isdir(maskgen_dir):
        empty_maskgen_dir()

    r = git.Repo.clone_from("https://github.com/rwgdrummer/maskgen.git", maskgen_dir)
    print("done")
    return r


def update():
    current_sha = repo.head.object.hexsha
    retry = True
    while retry:
        try:
            from maskgen.maskgen_loader import MaskGenLoader
            default_branch = MaskGenLoader().get_key("git.branch", "master")
        except ImportError:
            default_branch = "master"
        b = tkSimpleDialog.askstring("Select Branch", "Enter the branch of maskgen you want to use.  Note: this is "
                                                      "case sensitive.", initialvalue=default_branch)
        try:
            repo.remotes.origin.fetch(b)
            print("{0:.<64s}".format("Updating maskgen from " + b)),
            repo.git.reset("--hard")
            repo.git.checkout(b)
            repo.git.pull()

            try:
                remote_sha = repo.heads.__getattr__(b).object.hexsha
            except AttributeError:
                remote_sha = None

            if current_sha == remote_sha:  # SHA before checkout and pull equals latest
                print("skipped")
                return b, True
            elif repo.head.object.hexsha == remote_sha:  # SHA after checkout and pull equals latest
                print("success")
                return b, False
            else:
                print("failed")  # SHA after checkout and pull is still not latest
                return b, False

        except git.exc.GitCommandError as e:
            retry = tkMessageBox.askretrycancel("Invalid Branch", "{0} is an invalid branch.".format(b))
        except TypeError:
            # user hit cancel
            break

    # this only runs if there is never a valid branch selected
    try:
        remote_sha = repo.heads.__getattr__("master").object.hexsha
    except AttributeError:
        remote_sha = None
    print("{0:.<64s}".format("Updating maskgen from master")),
    repo.remotes.origin.fetch("master")
    repo.git.reset("--hard")
    repo.git.checkout("master")
    repo.git.pull()
    if current_sha == remote_sha:  # SHA before checkout and pull equals latest
        print("skipped")
        return "master", True
    elif repo.head.object.hexsha == remote_sha:  # SHA after checkout and pull equals latest
        print("success")
        return "master", False
    else:
        print("failed")  # SHA after checkout and pull is still not latest
        return "master", False


def remove_installed():
    remove_dirs = ["dist", os.path.join("hp_tool", "build"), os.path.join("hp_tool", "dist")]
    for d in remove_dirs:
        d = os.path.join(maskgen_dir, d)
        if os.path.isdir(d):
            shutil.rmtree(d)


def installed():
    return git.repo.Repo(path=maskgen_dir)


def check_frequents():
    frequent = [os.path.join(os.path.expanduser("~"), "maskgen"),
                os.path.join(os.path.expanduser("~"), "Desktop", "maskgen"),
                os.path.join(os.path.expanduser("~"), "Documents", "maskgen")
                ]

    for f in frequent:
        if os.path.isdir(f):
            return f

    return None


def copy_code_names():
    print ("Attempting to {0:.<50s}".format("set manipulator code names")),
    import tempfile

    temp_names = os.path.join(tempfile.gettempdir(), "ManipulatorCodeNames.txt")
    if os.path.isfile(os.path.join(maskgen_dir, "resources", "ManipulatorCodeNames.txt")):
        m = "ManipulatorCodeNames.txt already exists"
        print "skipped"

    elif os.path.isfile(temp_names):
        try:
            shutil.copy(temp_names, os.path.join(maskgen_dir, "resources"))
            m = "Successfully copied ManipulatorCodeNames.txt"
            print("success")
        except Exception as e:
            m = "Failed to copy manipulator code names.\n" + e.message
            print("failed")
    else:
        m = "Failed to locate manipulator code names."
        print("failed")

    write_log(m)


def write_branch_to_config():
    try:
        from maskgen.maskgen_loader import MaskGenLoader
        loader = MaskGenLoader()
        loader.save("git.branch", branch)
    except ImportError:
        pass


if __name__ == '__main__':
    root = Tk()
    root.withdraw()

    write_log("<---{0:^50s}--->".format("Maskgen Installation Process"))

    start_time = datetime.strftime(datetime.now(), "%b %d, %Y    %I:%M:%S%p")

    already_installed, maskgen_dir = get_maskgen_dir()

    if already_installed:
        repo = None
        while repo is None:
            try:
                repo = installed()
            except git.exc.InvalidGitRepositoryError:
                if not tkMessageBox.askretrycancel("Invalid repository", "{0} is an invalid Git repository.  Would you "
                                                                         "like to try again?".format(maskgen_dir)):
                    break
                maskgen_dir = tkFileDialog.askdirectory(initialdir=os.path.join(os.path.expanduser("~"), "Documents"))
        if repo is None:
            write_log("Maskgen Installation Failed: Valid git repository never selected")
            exit(2)
    else:
        repo = clone()
    branch, up_to_date = update()

    if not up_to_date or not already_installed or (up_to_date and tkMessageBox.askyesno(
            "Update Anyways?", "Your maskgen installation is already up to date.  Would you like to reinstall?")):
        run_uninstalls()
        remove_installed()

        install_setuptools()
        jt_success = install_jt()
        install_hp()

        copy_code_names()
    else:
        jt_success = True

    if jt_success:
        write_branch_to_config()
        t = tkMessageBox.askyesno("Install Trello Plugin", "Would you like to install the Trello integration "
                                                           "plugin?")
        if t:
            install_trello()

    write_log("+" * 64)
    write_log("+ {0:<60s} +".format("Maskgen Installation Info"))
    write_log("+ {0:<60s} +".format("Branch:     " + branch))
    write_log("+ {0:<60s} +".format("SHA:        " + repo.head.object.hexsha))
    write_log("+ {0:<60s} +".format("Start Time: " + start_time))
    write_log("+ {0:<60s} +".format("End Time:   " + datetime.strftime(datetime.now(), "%b %d, %Y    %I:%M:%S%p")))
    write_log("+" * 64 + "\n" * 3)

    if not already_installed:
        tkMessageBox.showwarning("First Installation", "If this is your first installation, you will need to restart "
                                                       "your computer before using the HP Tool.")
