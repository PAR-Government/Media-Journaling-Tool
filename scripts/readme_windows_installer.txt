############INDEX##############
*0*			Windows Server Installation
*1*			Building th JT Installer on your own machine















*0* Windows Server Installation
On a Windows Server installation of the JT, there may be problems with path setup during the prerequisite installation.
This will involve manual path additions to the following locations:
	C:\Program Files (x86)\GnuPG\bin
	C:\Program Files\fmpeg-3.2-win64-shared\bin
	C:\Users\<USERNAME HERE>\Anaconda2
	C:\Users\<USERNAME HERE>\Anaconda2\Library\usr\bin
	C:\Users\<USERNAME HERE>\Anaconda2\Library\bin
	C:\Users\<USERNAME HERE>\Anaconda2\Scripts
	C:\Users\<USERNAME HERE>\AppData\Local\Microsoft\WindowsApps
	C:\Program Files\Exiftool
	C:\Program Files (x86)\Graphviz2.38\bin
	C:\Program Files\opencv\build\x64\vc14\bin











*1* Building the JT Installer on your own machine
###########Downloads#############

NSIS Requirements:
NSIS 									https://downloads.sourceforge.net/project/nsis/NSIS%203/3.02.1/nsis-3.02.1-setup.exe
EnvVarUpdate							http://nsis.sourceforge.net/mediawiki/images/a/ad/EnvVarUpdate.7z
WordFunc                                http://forums.winamp.com/attachment.php?attachmentid=37933&d=1158992399
INetC									http://nsis.sourceforge.net/Inetc_plug-in 
nsUnzip									http://nsis.sourceforge.net/NsUnzip_plugin

Prerequisites:
Anaconda2 4.4.0							https://repo.continuum.io/archive/Anaconda2-4.4.0-Windows-x86_64.exe
Exiftool								https://www.sno.phy.queensu.ca/~phil/exiftool/exiftool-10.63.zip
ffmpeg									https://ffmpeg.zeranoe.com/builds/win64/shared/ffmpeg-3.2-win64-shared.zip
GraphViz								http://www.graphviz.org/pub/graphviz/stable/windows/graphviz-2.38.msi
jtprefs.py								maskgen/scripts/python
opencv-2.4.13.3							https://downloads.sourceforge.net/project/opencvlibrary/opencv-win/2.4.13/opencv-2.4.13.3-vc14.exe
pygraphviz								http://www.lfd.uci.edu/~gohlke/pythonlibs/zhckc95n/pygraphviz-1.3.1-cp27-none-win_amd64.whl
Visual C++ For Python 2.7				https://www.microsoft.com/en-us/download/confirmation.aspx?id=44266

Installer File:
windows_installer.nsh					maskgen/scripts






#############SETUP###############

Install NSIS and add it to your PATH

Install INetC by copying Inetc.zip\Plugins\x86-ansi\INetC.dll to C:\Program Files (x86)\NSIS\Plugins\x86-ansi\
Install NsUnzip by copying NsUnzip.zip\nsUnzip.dll to C:\Program Files (x86)\NSIS\Plugins\x86-ansi\
Install EnvVarUpdate by copying EnvVarUpdate.7z\EnvVarUpdate.nsh to the directory you placed "windows_installer.nsh" in
Install WordFunc by extracting all files in the zip to any folder and running the setup exe file
Download all prerequisites and place them in a folder named "Prerequisites", placed in the same folder as "windows_installer.nsh"






###########MODIFYING#############

To modify the installer edit the "windows_installer.nsh" file with a text editor






###########BUILDING##############

Open a command line (cygwin or cmd)
Change directory into the folder containing "windows_installer.nsh"
run "makensis windows_installer.nsh"

This will output a file named "jt_installer.exe"
