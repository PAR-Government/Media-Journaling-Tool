import os
import subprocess
from datetime import datetime
import json
from sys import argv
import shutil
import tempfile

commands = {"remove": {"conda": ["pillow"]},
            "install": {
                "conda": ["-c conda-forge tifffile",
                          "scikit-image"],
                "pip": ["Image",
                        os.path.join(tempfile.gettempdir(), "pygraphviz-1.3.1-cp27-none-win_amd64.whl"),
                        os.path.join(tempfile.gettempdir(), "Shapely-1.6.4.post1-cp27-cp27m-win_amd64.whl"),
                        "GitPython",
                        "opencv-contrib-python==3.4.5.20"]
            }
            }


def write_log(msg):
    with open(os.path.expanduser("~\\install_log.log"), "a+") as logf:
        logf.write(msg + "\n")


def check_installations():
    p = subprocess.Popen(['python', '-m', 'pip', 'install', '--upgrade', 'pip'], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    d = p.communicate()
    if p.returncode != 0:
        m = "Failed to upgrade pip:\n" + d[1]
    else:
        m = "Successfully upgraded pip"
    write_log(m)
    conda_process = subprocess.Popen(['conda', 'list', '--json'], shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
    conda_data = conda_process.communicate()

    pip_process = subprocess.Popen(['pip', 'list', '--format=freeze'], shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    pip_data = pip_process.communicate()

    if conda_process.returncode != 0:
        write_log("Failed to verify conda version:\n" + conda_data[1])
    if pip_process.returncode != 0:
        write_log("Failed to verify pip version:\n" + pip_data[1])
    if conda_process.returncode != 0 or pip_process.returncode != 0:
        return False

    conda_list = json.loads(conda_data[0])
    needed_packages = {"conda": [x.split(" ")[-1].lower() for x in commands["install"]["conda"]],
                       "pip": [y.lower() for y in commands["install"]["pip"]]}
    packages_found = {"conda": {}, "pip": {}}

    for pack in conda_list:
        if pack["name"].lower() in needed_packages["conda"]:
            packages_found["conda"][pack["name"].lower()] = pack

    for pack in pip_data[0].splitlines():
        name, version = pack.split("==")
        if name.lower() in needed_packages["pip"]:
            packages_found["pip"][name.lower()] = version

    # Verify all packages needed have been found
    if sorted(needed_packages["conda"]) != sorted(packages_found["conda"].keys()) or sorted(needed_packages["pip"]) != \
            sorted(packages_found["pip"].keys()):
        return False

    return True


def install_package(module, install_type, package):
    if force:
        if module == "conda":
            cmd = ["python", "-m", module, install_type, "--force"] + package.split(" ")
        else:
            cmd = ["python", "-m", module, install_type, "--force-reinstall"] + package.split(" ")
    else:
        cmd = ["python", "-m", module, install_type] + package.split(" ")

    if os.sep in package:
        pname = os.path.split(package)[1].split("-")[0]
        if not os.path.isfile(package):
            return "Failed to locate {0} at {1}.".format(pname, package)
    else:
        pname = cmd[-1]

    cmd = ["echo", "y", "|"] + cmd
    print ("Attempting to {0:.<50s}".format(install_type + " " + pname)),  # Stay under 80 characters
    pro = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = pro.communicate()

    if pro.returncode == 0:
        log_data = "Successfully {0} {1}".format(install_type + ("ed" if install_type != "remove" else "d"), pname)
        print("success")
    elif out[1].startswith("\r\nPackagesNotFoundError: The following packages are missing from the target environment"):
        log_data = "Skipped removing {0} - Package does not exist.".format(pname)
        print("skipped")
    else:
        log_data = "Failed to {0} {1}\n{2}".format(install_type, pname, out[1])
        print("failed")
    return log_data


def main():
    write_log("<---{0:^50s}--->".format("Maskgen Dependency Installation Process"))
    start_time = datetime.strftime(datetime.now(), "%b %d, %Y    %I:%M:%S%p")

    if not force:
        already_exists = check_installations()

        if already_exists:
            print("Packages already installed.")
            write_log("Package installation process skipped, all packages to be installed have been found.")
            return

    successful = []
    skipped = []
    failed = []

    for inst_type in sorted(commands.keys(), reverse=True):  # uninstall, then install
        for module in sorted(commands[inst_type].keys()):  # conda, then pip
            for package in commands[inst_type][module]:  # package (+ channel if needed)
                log_data = install_package(module, inst_type, package)

                if log_data.startswith("Success"):
                    successful.append(package)
                elif log_data.startswith("Skip"):
                    skipped.append(package)
                else:
                    failed.append(package)

                write_log(log_data)

    write_log("+" * 64)
    write_log("+ {0:<60s} +".format("Maskgen Package Installation Info"))
    write_log("+ {0:<60s} +".format("Skipped:    " + ", ".join(skipped)))
    write_log("+ {0:<60s} +".format("Failed:     " + ", ".join(failed)))
    write_log("+ {0:<60s} +".format("Start Time: " + start_time))
    write_log("+ {0:<60s} +".format("End Time:   " + datetime.strftime(datetime.now(), "%b %d, %Y    %I:%M:%S%p")))
    write_log("+" * 64 + "\n" * 5)


if __name__ == '__main__':
    try:
        force = True if argv[1] in ["-f", "--force"] else False
    except IndexError:
        force = False
    print("Running Python package installation commands.  This may take several minutes.")
    main()
