RequestExecutionLevel admin

!include EnvVarUpdate.nsh
!include WordFunc.nsh
!insertmacro WordReplace

Outfile "jt_installer.exe"
name "JT Installer"

InstallDir $TEMP

Var CONDA 
Var PIP
Var PYTHON 
Var USERDIR 
Var BRANCH 
Var GIT

Section -Prerequisites
    MessageBox MB_OK "Specific versions of each prerequisite are required for$\neverything to work properly.  Please verify that any previously$\ninstalled prerequisites match the following versions:$\n$\n$\tAnaconda2$\t$\t4.4.0$\n$\tFFmpeg$\t$\t$\t3.2.X+$\n$\tExiftool$\t$\t$\t10.6X+$\n$\tOpenCV$\t$\t$\t2.4.13.X+$\n$\tGraphViz$\t$\t$\t2.38"

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
    MessageBox MB_YESNO "Install Visual C++ for Python 2.7?" /SD IDYES IDNO has_vcpp
    File "Prerequisites\VCForPython27.msi"
    ExecWait "msiexec.exe /i $INSTDIR\VCForPython27.msi /quiet"
    Delete "$INSTDIR\VCForPython27.msi"
    
    has_vcpp:
    MessageBox MB_YESNO "Install Visual C++ 2008?" /SD IDYES IDNO has_vc27    
    File "Prerequisites\vcredist_x64.exe"
    ExecWait "$INSTDIR\vcredist_x64.exe /qb"
    Delete "$INSTDIR\vcredist_x64.exe"
    
    has_vc27:
    StrCpy $CONDA "$PROFILE\Anaconda2\Scripts\conda.exe"
    StrCpy $PIP "$PROFILE\Anaconda2\Scripts\pip.exe"
    StrCpy $PYTHON "$PROFILE\Anaconda2\python.exe"

    IfFileExists "$PROGRAMFILES64\Exiftool\*.*" has_exiftool
    File "Prerequisites\exiftool-11.02.zip"
    NsUnzip::Extract "$INSTDIR\exiftool-11.02.zip" /END
    CreateDirectory "$PROGRAMFILES64\Exiftool"
    Rename "$INSTDIR\exiftool(-k).exe" "$PROGRAMFILES64\Exiftool\exiftool.exe"
    Delete "$INSTDIR\exiftool-11.02.zip"
    ${EnvVarUpdate} $0 "PATH" "A" "HKCU" "C:\Program Files\Exiftool"
    
    has_exiftool:
    IfFileExists "$PROGRAMFILES64\ffmpeg-3.4.1-win64-shared\bin\ffmpeg.exe" has_ffmpeg
    File "Prerequisites\ffmpeg-3.4.1-win64-shared.zip"
    NsUnzip::Extract "$INSTDIR\ffmpeg-3.4.1-win64-shared.zip" /d=$PROGRAMFILES64 /END
    Delete "$INSTDIR\ffmpeg-3.4.1-win64-shared.zip"
    ${EnvVarUpdate} $0 "PATH" "P" "HKCU" "C:\Program Files\ffmpeg-3.4.1-win64-shared\bin"

    has_ffmpeg:
    IfFileExists "$PROGRAMFILES32\Graphviz2.38\bin\*.*" has_graphviz
    File "Prerequisites\graphviz-2.38.msi"
    ExecWait "msiexec.exe /i $INSTDIR\graphviz-2.38.msi /quiet"
    Delete "$INSTDIR\graphviz-2.38.msi"
    ${EnvVarUpdate} $0 "PATH" "A" "HKCU" "C:\Program Files (x86)\Graphviz2.38\bin"
    
    has_graphviz:
	IfFileExists "$PROGRAMFILES64\opencv\build\*.*" has_cvd_build
	File "Prerequisites\opencv-3.4.1-vc14_vc15.exe"
	ExecWait "opencv-3.4.1-vc14_vc15.exe -y -o$\"$PROGRAMFILES64$\""
	${EnvVarUpdate} $0 "PATH" "A" "HKCU" "$PROGRAMFILES64\opencv\build\x64\vc14\bin"
	${EnvVarUpdate} $0 "PATH" "A" "HKCU" "$PROGRAMFILES64\opencv\build\bin"
	Delete "$INSTDIR\opencv-3.4.1-vc14_vc15.exe"
    
    has_cvd_build:
    IfFileExists "$PROFILE\Anaconda2\Lib\cv2.pyd" +1 +2
    Rename "$PROFILE\Anaconda2\Lib\cv2.pyd" "$PROGRAMFILES64\opencv\build\python\2.7\x64\cv2.pyd"
    IfFileExists "$PROFILE\Anaconda2\Lib\site-packages\cv2.pyd" has_cv2_installed
    CopyFiles "$PROGRAMFILES64\opencv\build\python\2.7\x64\cv2.pyd" "$PROFILE\Anaconda2\Lib\site-packages\"

    has_cv2_installed:
    IfFileExists "$PROGRAMFILES\GnuPG\bin\gpg.exe" has_gpg_installed
    File "Prerequisites\gpg4win-3.0.3.exe"
    ExecWait "$INSTDIR\gpg4win-3.0.3.exe /S"
	Sleep 5000
    Delete "$INSTDIR\gpg4win-3.0.3.exe"
    
    has_gpg_installed:
    IfFileExists "$PROFILE\medifor_ingest.gpg" has_gpg_key
    SetOutPath "$PROFILE"
    File "Prerequisites\medifor_ingest.gpg"
    
    has_gpg_key:
	IfFileExists "$PROGRAMFILES64\Git\cmd\git.exe" has_git
	File "Prerequisites\Git-2.18.0-64-bit.exe"
	ExecWait "Git-2.18.0-64-bit.exe /VERYSILENT /NORESTART /NOCANCEL /SP-"
	Delete "$INSTDIR\Git-2.18.0-64-bit.exe"
	
	has_git:
    ExecWait "$CONDA install -c conda-forge tifffile -y"
    ExecWait "$CONDA remove pillow -y"
    ExecWait "$PIP uninstall Pillow -y"
    ExecWait "$CONDA remove PIL -y"
    ExecWait "$CONDA install -c anaconda pillow -y"
    ExecWait "$CONDA install scikit-image -y"
    ExecWait "$CONDA install shapely –y"
    ExecWait "$CONDA install scikit-image"
    ExecWait "$PIP install setuptools"
    ExecWait "$PIP install graphviz"
	ExecWait "$PIP install pandastable"
	ExecWait "$PIP install Image"

    SetOutPath "$INSTDIR"
    File "Prerequisites\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
    ExecWait "$PIP install $INSTDIR\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
    Delete "$INSTDIR\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
    File "Prerequisites\Shapely-1.6.4.post1-cp27-cp27m-win_amd64.whl"
    ExecWait "$PIP install $INSTDIR\Shapely-1.6.4.post1-cp27-cp27m-win_amd64.whl"
    Delete "$INSTDIR\Shapely-1.6.4.post1-cp27-cp27m-win_amd64.whl"
    
    SetShellVarContext all
    Delete "$DESKTOP\Kleopatra.lnk"
	
    prereqs_installed:

SectionEnd

Section "Maskgen"
	SetShellVarContext current

    IfFileExists "$TEMP\install_options.txt" +5
    FileOpen $9 "$TEMP\install_options.txt" w
    FileWrite $9 "$DESKTOP$\r$\n"
    FileWrite $9 "master"
    FileClose $9
    MessageBox MB_OK "To change the installation directory, change line 1 of the text file.$\nTo change the branch change the second line of the text file."
    
    ExecWait "notepad.exe $TEMP\install_options.txt"
    FileOpen $9 "$TEMP\install_options.txt" r
    FileRead $9 $USERDIR
    FileRead $9 $BRANCH
    FileClose $9
    
    ${WordReplace} $USERDIR "$\r$\n" "" "+" $USERDIR
    ${WordReplace} $BRANCH "$\r$\n" "" "+" $BRANCH

    SetOutPath $USERDIR
    StrCpy $CONDA "$PROFILE\Anaconda2\Scripts\conda.exe"
    StrCpy $PIP "$PROFILE\Anaconda2\Scripts\pip.exe"
    StrCpy $PYTHON "$PROFILE\Anaconda2\python.exe"
	StrCpy $GIT "$PROGRAMFILES64\Git\cmd\git.exe"
	
	IfFileExists $GIT has_git no_git
	
	no_git:
	inetc::get /POPUP "" /CAPTION "master.zip" "https://github.com/rwgdrummer/maskgen/archive/$BRANCH.zip" "$TEMP\$BRANCH.zip"
    Pop $0 # return value = exit code, "OK" if OK
    MessageBox MB_OK "Download Status: $0" 
	
	DetailPrint "Extracting Maskgen..."
    NsUnzip::Extract "$USERDIR\$BRANCH.zip" /END
	Sleep 5000
	Rename "$USERDIR\maskgen-$BRANCH" "$USERDIR\maskgen"
	Sleep 5000
    Delete "$TEMP\$BRANCH.zip"
	
	MessageBox MB_OK "This update did not use Git.  Run the prerequisites portion of the installer, and click yes when prompted to install Git.  This will allow a much faster download in the future."
	Goto downloaded
	
	has_git:
	IfFileExists "$USERDIR\maskgen\*.*" has_maskgen
	CreateDirectory "$USERDIR\maskgen"
	
	has_maskgen:
	IfFileExists "$USERDIR\maskgen\.git" has_git_dir
	RMDir /r "$USERDIR\maskgen"
	ExecWait "$GIT clone https://github.com/rwgdrummer/maskgen $USERDIR\maskgen"

	has_git_dir:
	ExecWait "$GIT -C $USERDIR\maskgen checkout $BRANCH"
	ExecWait "$GIT -C $USERDIR\maskgen pull"
    
	downloaded:
    SetOutPath "$USERDIR\maskgen\resources"
    File "Prerequisites\ManipulatorCodeNames.txt"
    
    SetOutPath  "$USERDIR\maskgen"
    SetOutPath "$USERDIR\maskgen\setuptools-version"
    ExecWait "$PYTHON setup.py install"

    SetOutPath  "$USERDIR\maskgen"
    ExecWait "$PYTHON setup.py sdist"
    ExecWait "$PIP install -e ."

    SetOutPath "$USERDIR\maskgen\hp_tool"
    ExecWait "$PYTHON setup.py install"

	; SetOutPath "$TEMP"
	; File "Prerequisites\jtprefs.py"
    ExecWait "$PYTHON $USERDIR\maskgen\scripts\python\jtprefs.py" ; $TEMP\jtprefs.py"
	; Delete "$TEMP\jtprefs.py"

    Delete "$DESKTOP\maskgen.log"
	
	IfFileExists "$USERDIR\maskgen\notify_plugins\trello_plugin\build\*.*" has_trello
	MessageBox MB_YESNO "Install Trello Plugin?" /SD IDYES IDNO has_trello
	SetOutPath "$USERDIR\maskgen\notify_plugins\trello_plugin"
	ExecWait "$PYTHON setup.py install"
	
    has_trello:
    MessageBox MB_OK "If this is your first installation, you will need to$\nrestart your computer to use the HP Tool."

SectionEnd
