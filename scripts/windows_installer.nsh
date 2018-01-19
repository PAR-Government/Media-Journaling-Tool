RequestExecutionLevel admin

!include EnvVarUpdate.nsh
!include WordFunc.nsh
!insertmacro WordReplace

Outfile "jt_installer.exe"
name "JT Installer"

InstallDir $DESKTOP

Var CONDA 
Var PIP
Var PYTHON 
Var USERDIR 
Var BRANCH 

Section -Prerequisites
    MessageBox MB_OK "Specific versions of each prerequisite are required for$\neverything to work properly.  Please verify that any previously$\ninstalled prerequisites match the following versions:$\n$\n$\tAnaconda2$\t$\t4.4.0$\n$\tFFmpeg$\t$\t$\t3.2.X$\n$\tExiftool$\t$\t$\t10.61$\n$\tOpenCV$\t$\t$\t2.4.13.X$\n$\tGraphViz$\t$\t$\t2.38"

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
    IfFileExists "$PROFILE\Anaconda2\Lib\cv2.pyd" +1 +2
    Rename "$PROFILE\Anaconda2\Lib\cv2.pyd" "$PROGRAMFILES64\opencv\build\python\2.7\x64\cv2.pyd"
	IfFileExists "$PROFILE\Anaconda2\Lib\site-packages\cv2.pyd" has_cv2_installed
	CopyFiles "$PROGRAMFILES64\opencv\build\python\2.7\x64\cv2.pyd" "$PROFILE\Anaconda2\Lib\site-packages\"

	has_cv2_installed:
	ExecWait "$CONDA install -c conda-forge tifffile -y"
	ExecWait "$CONDA remove pillow -y"
    ExecWait "$PIP uninstall Pillow -y"
	ExecWait "$CONDA remove PIL -y"
    ExecWait "$CONDA install -c anaconda pillow -y"
	ExecWait "$CONDA install scikit-image -y"

	SetOutPath "$INSTDIR"
	ExecWait "$PIP install graphviz"
	File "Prerequisites\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
	ExecWait "$PIP install $INSTDIR\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
	Delete "$INSTDIR\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
	
	prereqs_installed:

SectionEnd

Section "Maskgen"

	IfFileExists "$DESKTOP\install_options.txt" +5
	FileOpen $9 "$DESKTOP\install_options.txt" w
	FileWrite $9 "$DESKTOP$\r$\n"
	FileWrite $9 "master"
    FileClose $9
	MessageBox MB_OK "To change the installation directory, change line 1 of the text file.$\nTo change the branch change the second line of the text file."
    
    ExecWait "notepad.exe $DESKTOP\install_options.txt"
    FileOpen $9 "$DESKTOP\install_options.txt" r
    FileRead $9 $USERDIR
    FileRead $9 $BRANCH
    FileClose $9
    
    ${WordReplace} $USERDIR "$\r$\n" "" "+" $USERDIR
    ${WordReplace} $BRANCH "$\r$\n" "" "+" $BRANCH

	IfFileExists "$USERDIR\maskgen\*.*" +1 +2
	RMDir /r $USERDIR\maskgen

    SetOutPath $USERDIR
	StrCpy $CONDA "$PROFILE\Anaconda2\Scripts\conda.exe"
	StrCpy $PIP "$PROFILE\Anaconda2\Scripts\pip.exe"
	StrCpy $PYTHON "$PROFILE\Anaconda2\python.exe"
	
    inetc::get /POPUP "" /CAPTION "master.zip" "https://github.com/rwgdrummer/maskgen/archive/$BRANCH.zip" "$USERDIR\$BRANCH.zip"
    Pop $0 # return value = exit code, "OK" if OK
    MessageBox MB_OK "Download Status: $0" 

    DetailPrint "Extracting Maskgen..."
    NsUnzip::Extract "$USERDIR\$BRANCH.zip" /END
	Sleep 5000
	Rename "$USERDIR\maskgen-$BRANCH" "$USERDIR\maskgen"

    SetOutPath  "$USERDIR\maskgen"
	ExecWait "$PIP install setuptools"
	SetOutPath "$USERDIR\maskgen\setuptools-version"
    ExecWait "$PYTHON setup.py install"

    SetOutPath  "$USERDIR\maskgen\wrapper_plugins\rawphoto_wrapper"
    ExecWait "$PYTHON setup.py sdist"
    ExecWait "$PIP install -e ."

    SetOutPath  "$USERDIR\maskgen"
    ExecWait "$PYTHON setup.py sdist"
    ExecWait "$PIP install -e ."

	SetOutPath "$USERDIR\maskgen\hp_tool"
	ExecWait "$PYTHON setup.py install"

	SetOutPath "$USERDIR"
	File "Prerequisites\jtprefs.py"
	ExecWait "$PYTHON jtprefs.py"
	Delete "$USERDIR\jtprefs.py"

	Delete "$USERDIR\$BRANCH.zip"
    
    MessageBox MB_OK "If this is your first installation, you will need to$\nrestart your computer to use the HP Tool."

SectionEnd
