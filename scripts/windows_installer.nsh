RequestExecutionLevel admin

!include EnvVarUpdate.nsh

Outfile "jt_installer.exe"
name "JT Installer"

InstallDir $TEMP

Section -Prerequisites
    MessageBox MB_OK "Specific versions of each prerequisite are required for$\neverything to work properly.  Please verify that any previously$\ninstalled prerequisites match the following versions:$\n$\n$\tAnaconda2$\t$\t4.4.0$\n$\tFFmpeg$\t$\t$\t3.2+$\n$\tExiftool$\t$\t$\t10.6X+$\n$\tOpenCV$\t$\t$\t2.4.13+$\n$\tGraphViz$\t$\t$\t2.38"
    
    MessageBox MB_YESNO "Do you need the prerequisites installed?$\n(e.g. exiftool, graphviz etc.)" /SD IDYES IDNO prereqs_installed
    
    ; Search for Anaconda Installed
    SetRegView 64
    ClearErrors
    ReadRegStr $R0 HKLM "SOFTWARE\Python\ContinuumAnalytics\Anaconda27-64" "SysVersion"
    DetailPrint "Local Machine Anaconda found version $R1"
    IfErrors +1 verify_python
    
    ClearErrors
    Pop $R0
    ReadRegStr $R0 HKCU "SOFTWARE\Python\ContinuumAnalytics\Anaconda27-64" "SysVersion"
    DetailPrint "Current User Git found version $R1"
    IfErrors no_git_or_python +1
    
    verify_python:
    StrCmp $R0 "2.7" find_git no_git_or_python
    
    ; Search for Git Installed
    find_git:
    ClearErrors  ; Shouldn't change anything, but just in case
    ReadRegStr $R1 HKLM "SOFTWARE\GitForWindows" "CurrentVersion"
    DetailPrint "Local Machine Git found version $R1"
    IfErrors +1 inst_ready
    
    ClearErrors
    Pop $R1
    ReadRegStr $R1 HKCU "SOFTWARE\GitForWindows" "CurrentVersion"
    DetailPrint "Current User Git found version $R1"
    IfErrors +1 inst_ready
    
    no_git_or_python:
        MessageBox MB_YESNO "Do you have Anaconda for Python 2.7 installed?$\n" IDYES inst_ready IDNO +1
        MessageBox MB_OK "Anaconda for Python 2.7 and Git must be installed prior to JT Installation.  Please install Anaconda and Git and try again."
        Quit

    inst_ready:
    SetOutPath $INSTDIR
    
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
    IfFileExists "$PROGRAMFILES64\Exiftool\*.*" has_exiftool
    File "Prerequisites\exiftool-11.02.zip"
    NsUnzip::Extract "$INSTDIR\exiftool-11.02.zip" /END
    CreateDirectory "$PROGRAMFILES64\Exiftool"
    Rename "$INSTDIR\exiftool(-k).exe" "$PROGRAMFILES64\Exiftool\exiftool.exe"
    Delete "$INSTDIR\exiftool-11.02.zip"
    ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "C:\Program Files\Exiftool"
    
    has_exiftool:
    IfFileExists "$PROGRAMFILES64\ffmpeg-3.3.4-win64-static\bin\ffmpeg.exe" has_ffmpeg
    File "Prerequisites\ffmpeg-3.3.4-win64-static.zip"
    NsUnzip::Extract "$INSTDIR\ffmpeg-3.3.4-win64-static.zip" /d=$PROGRAMFILES64 /END
    Delete "$INSTDIR\ffmpeg-3.3.4-win64-static.zip"
    ${EnvVarUpdate} $0 "PATH" "P" "HKLM" "$PROGRAMFILES64\ffmpeg-3.3.4-win64-static\bin"

    has_ffmpeg:
    IfFileExists "$PROGRAMFILES32\Graphviz2.38\bin\*.*" has_graphviz
    File "Prerequisites\graphviz-2.38.msi"
    ExecWait "msiexec.exe /i $INSTDIR\graphviz-2.38.msi /quiet"
    Delete "$INSTDIR\graphviz-2.38.msi"
    ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "C:\Program Files (x86)\Graphviz2.38\bin"
    
    has_graphviz:
    IfFileExists "$PROFILE\medifor_ingest.gpg" has_gpg_key
    SetOutPath "$PROFILE"
    File "Prerequisites\medifor_ingest.gpg"
    
    has_gpg_key:
    IfFileExists "$PROGRAMFILES64\opencv\*.*" +1 no_opencv
    RMDir /r $PROGRAMFILES64\opencv
    ${EnvVarUpdate} $0 "PATH" "R" "HKLM" "$PROGRAMFILES64\opencv\bin"
    
    no_opencv:
    SetOutPath "$INSTDIR"
    File "Prerequisites\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
    File "Prerequisites\Shapely-1.6.4.post1-cp27-cp27m-win_amd64.whl"
    File "WindowsInstallScript.py"
    ExecWait "python $INSTDIR\WindowsInstallScript.py"
    Delete "$INSTDIR\pygraphviz-1.3.1-cp27-none-win_amd64.whl"
    Delete "$INSTDIR\Shapely-1.6.4.post1-cp27-cp27m-win_amd64.whl"
    Delete "$INSTDIR\WindowsInstallScript.py"
    
    SetShellVarContext all
    Delete "$DESKTOP\Kleopatra.lnk"
	SetShellVarContext current
	
    prereqs_installed:

SectionEnd

Section "Maskgen"
    SetOutPath "$TEMP"
    
    File "Prerequisites\ManipulatorCodeNames.txt"
    
    File "MaskgenInstallScript.py"
    ExecWait "python $\"$TEMP\MaskgenInstallScript.py$\""
    Delete "$TEMP\MaskgenInstallScript.py"
    
    File "Prerequisites\jtprefs.py"
    ; ExecWait "python $\"$USERDIR\maskgen\scripts\python\jtprefs.py$\""
    ExecWait "python $\"$TEMP\jtprefs.py$\""
    Delete "$TEMP\jtprefs.py"

    Delete "$DESKTOP\maskgen.log"

SectionEnd
