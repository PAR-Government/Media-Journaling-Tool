RequestExecutionLevel admin

!include EnvVarUpdate.nsh

Outfile "jt_installer.exe"
name "JT Installer"

InstallDir $DESKTOP

Var CONDA 
Var PIP
Var PYTHON 

Section -Prerequisites
	
	MessageBox MB_YESNO "Do you need the prerequisites installed?$\n(e.g. anaconda, exiftool, graphviz etc.)" /SD IDYES IDNO prereqs_installed
	
    SetOutPath $INSTDIR
    ReadRegStr $0 HKLM "SOFTWARE\Python\ContinuumAnalytics\Anaconda27-64" SysVersion
    StrCmp $0 "" lbl_install_conda lbl_has_conda
    StrCmp $0 "2.7" lbl_has_conda lbl_install_conda

    lbl_install_conda:

    MessageBox MB_YESNO "Install Anaconda Python 2.7?" /SD IDYES IDNO lbl_has_conda
    File "Prerequisites\Anaconda2-4.4.0-Windows-x86_64.exe"
	Sleep 5000
    ExecWait "$INSTDIR\Anaconda2-4.4.0-Windows-x86_64.exe /S /InstallationType=JustMe /AddToPath=1 /D=$PROFILE\Anaconda2\"
	Delete "$INSTDIR\Anaconda2-4.4.0-Windows-x86_64.exe"

    lbl_has_conda:
	StrCpy $CONDA "$PROFILE\Anaconda2\Scripts\conda.exe"
	StrCpy $PIP "$PROFILE\Anaconda2\Scripts\pip.exe"
	StrCpy $PYTHON "$PROFILE\Anaconda2\python.exe"

	IfFileExists "$PROGRAMFILES64\Exiftool\*.*" has_exiftool
    File "Prerequisites\exiftool-10.61.zip"
    NsUnzip::Extract "$INSTDIR\exiftool-10.61.zip" /END
	CreateDirectory "$PROGRAMFILES64\Exiftool"
	Rename "$INSTDIR\exiftool (-k).exe" "$PROGRAMFILES64\Exiftool\exiftool.exe"
	Delete "$INSTDIR\exiftool-10.61.zip"
    ${EnvVarUpdate} $0 "PATH" "A" "HKCU" "C:\Program Files\Exiftool"
    
	has_exiftool:
    IfFileExists "$PROGRAMFILES64\ffmpeg-3.2-win64-shared\bin\ffmpeg.exe" has_ffmpeg
    File "Prerequisites\ffmpeg-3.2-win64-shared.zip"
    NsUnzip::Extract "$INSTDIR\ffmpeg-3.2-win64-shared.zip" /d=$PROGRAMFILES64 /END
	Delete "$INSTDIR\ffmpeg-3.2-win64-shared.zip"
    ${EnvVarUpdate} $0 "FFMPEG" "A" "HKCU" "C:\Program Files\ffmpeg-3.2-win64-shared"
    ${EnvVarUpdate} $0 "PATH" "P" "HKCU" "%FFMPEG%\bin"

    has_ffmpeg:
	IfFileExists "$PROGRAMFILES32\Graphviz2.38\bin\*.*" has_graphviz
	File "Prerequisites\graphviz-2.38.msi"
	ExecWait "msiexec.exe /i $INSTDIR\graphviz-2.38.msi /quiet"
	Delete "$INSTDIR\graphviz-2.38.msi"
    ${EnvVarUpdate} $0 "PATH" "A" "HKCU" "C:\Program Files (x86)\Graphviz2.38\bin"
	
	has_graphviz:
	MessageBox MB_YESNO "Install Visual C++ for Python 2.7?" /SD IDYES IDNO has_vc27
	File "Prerequisites\VCForPython27.msi"
	ExecWait "msiexec.exe /i $INSTDIR\VCForPython27.msi /quiet"
	Delete "$DESKTOP\VCForPython27.msi"
	
	has_vc27:
	IfFileExists "$PROGRAMFILES64\opencv\build\*.*" has_cvd_build
	File "Prerequisites\opencv-2.4.13.3-vc14.exe"
	ExecWait "opencv-2.4.13.3-vc14.exe -y"
	Rename "$DESKTOP\opencv" "$PROGRAMFILES64\opencv"
	${EnvVarUpdate} $0 "CV2" "A" "HKCU" "$PROGRAMFILES64\opencv\build\x64\vc14\bin"
	${EnvVarUpdate} $0 "PATH" "A" "HKCU" "%CV2%"
	Delete "$DESKTOP\opencv-2.4.13.3-vc14.exe"
	
	has_cvd_build:
	IfFileExists "$PROFILE\Anaconda2\Lib\cv2.pyd" has_cv2_installed
	Rename "$PROGRAMFILES64\opencv\build\python\2.7\x64\cv2.pyd" "$PROFILE\Anaconda2\Lib\cv2.pyd"

	has_cv2_installed:
	ExecWait "$CONDA install -c conda-forge tifffile -y"
	ExecWait "$CONDA remove pillow -y"
	ExecWait "$CONDA install scikit-image -y"

	SetOutPath "$INSTDIR"
	ExecWait "$PIP install graphviz"
	File "Prerequisites\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
	ExecWait "$PIP install $INSTDIR\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
	Delete "$INSTDIR\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
	
	prereqs_installed:
	IfFileExists "$DESKTOP\maskgen\*.*" 0 +1
	RMDir /r $DESKTOP\maskgen
SectionEnd

Section "Maskgen"

    SetOutPath $INSTDIR

	StrCpy $CONDA "$PROFILE\Anaconda2\Scripts\conda.exe"
	StrCpy $PIP "$PROFILE\Anaconda2\Scripts\pip.exe"
	StrCpy $PYTHON "$PROFILE\Anaconda2\python.exe"
	
    inetc::get /POPUP "" /CAPTION "master.zip" "https://github.com/rwgdrummer/maskgen/archive/master.zip" "$INSTDIR\master.zip"
    Pop $0 # return value = exit code, "OK" if OK
    MessageBox MB_OK "Download Status: $0" 

    DetailPrint "Extracting Maskgen..."
    NsUnzip::Extract "$INSTDIR\master.zip" /END
	Sleep 5000
	Rename "$INSTDIR\maskgen-master" "$INSTDIR\maskgen"

    SetOutPath  "$DESKTOP\maskgen"
	ExecWait "$PIP install setuptools"
	SetOutPath "$DESKTOP\maskgen\setuptools-version"
    ExecWait "$PYTHON setup.py install"

    SetOutPath  "$DESKTOP\maskgen\wrapper_plugins\rawphoto_wrapper"
    ExecWait "$PYTHON setup.py sdist"
    ExecWait "$PIP install -e ."

    SetOutPath  "$DESKTOP\maskgen"
    ExecWait "$PYTHON setup.py sdist"
    ExecWait "$PIP install -e ."

	SetOutPath "$DESKTOP\maskgen\hp_tool"
	ExecWait "$PYTHON setup.py install"

	SetOutPath "$DESKTOP"
	File "Prerequisites\jtprefs.py"
	ExecWait "$PYTHON jtprefs.py"
	Delete "$DESKTOP\jtprefs.py"

	Delete "$DESKTOP\master.zip"

SectionEnd
