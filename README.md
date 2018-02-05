# Detailed Document

For the most up-to-date detailed documentation, see doc/MediForJournalingTool-public.pdf. This README is a summary.

# WHAT IS THIS?

This tool is used to journal image, video and audio manipulations applied to high provenance media to produce manipulated media.  The intent is to capture all the steps for the purpose of evaluating effectiveness and accuracy of manipulation detection algorithms, training detectors and evaluating manipulation software for their effectiveness and correctness.  The tool has numerous pluggable components including validation rules, mask generation rules, summarization rules, image readers, and image manipulation plugins.

# INSTALLATION

Install exiftool

Install ffmpeg and ffprobe for video processing.

Install graphviz

## Installation Details

Use one of the installers from the scripts directory.  Windows uses nsis.sourceforge.net.

### FFMPEG
For Anaconda users, the windows installer sets up the following installation.

*	Dowload and install FFMPEG 3.1.1.
*	Download and install opencv 2.4.13 from opencv.org using the appropriate architecture (x86 or x64).  Make sure it is built with FFMPEG.  This is confirmed by looking for opencv/build/x64/vc11/opencv_ffmpeg2413_64.dll.  Follow build-from-source instructions for opencv to include FFMPEG.
*	Copy opencv/build/python/2.7/x64/cv2.pyd (or x86/cv2.pyd for the x86 architecture) to Anaconda2/Lib/site-packages
*	Set environment variables:
*	32-bit: Set OPENCV_DIR to the absolute path of opencv/x86/vc11
*	64-bit: Set OPENCV_DIR to the absolute path of opencv/x64/vc11
*	Add to PATH: %OPENCV_DIR%\bin
*	Add to Path: FFMPEG’s bin directory

### FFMPEG (not Anaconda): 

ffmpeg should installed with x265 and x265 codecs prior to installing python package.
For example, a Mac user can use the following command.
```
brew install ffmpeg --with-fdk-aac --with-ffplay --with-freetype --with-libass --with-libquvi --with-libvorbis --with-libvpx --with-opus --with-x265
```

```
pip install ffmpeg
```

## GRAPHVIZ:
### (MAC)
```
brew install graphviz
pip install pygraphviz
```
See http://www.graphviz.org/Download..php for other options.

### (WINDOWS)
1.	Download the current stable release from http://www.graphviz.org/Download_windows.php. Get the .msi, not the .zip.
2.	Run the graphviz msi installer, and walk through the steps to install.
3.	Add the graphviz “bin” directory to PATH variable. Most likely will be C:\Program Files (x86)\Graphviz2.38\bin
4.	Restart computer to complete the install
5.	Pull down the correct wheel from http://www.lfd.uci.edu/~gohlke/pythonlibs/#pygraphviz and perform:
```
pip install pygraphviz-1.3.1-cp27-none-win_amd64.whl 
```

## tiffile:

For use with using plugins that write TIFF files, install tifffile. For Mac users, XCode needs to be installed.  For Windows users, Microsoft Visual C++ 9.x for python needs to be installed.   An alternative is to find a prebuilt libtiff library for Mac or Windows.  Download at your own risk.
```
pip install tifffile
```

## RAWPY:

The installation may fail on installing rawpy.  Here other some other options, before restarting the install.

1. pip install rawpy (may still give the same error)
2. Pick and install the appropriate WHL from https://pypi.python.org/pypi/rawpy
3. Install git and rerun the setup.

## PDF:

```
pip install PyPDF2
```

# RESOURCES

The tool uses three key resource files: 
*	software.csv lists the permitted software and versions to select.  This enables consistent naming.
*	operations.json provides the description of all journaled operations and require parameters, along with defining validation rules, analysis requirements, and parameters.
*	project_properties.json defines all final image node and project properties.  Final image node properties are summarizations of activities that contributed to a final image node of a project.
Resource files are stored in one of the following locations, searched in the order given:
	*	Directory as indicated by the MASKGEN_RESOURCES environment variable
	*	current working directory
	*	resources subdirectory
	*	The resource installation as determined by Python’s sys path.

# Usage

## Starting the UI


```
% jtuiw
```

The imagedir argument is a project directory with a project JSON file in the project directory.

An optional folder can be specified to open an existing journal directory or create a new journal using all the media in the provided directory.

```
% jtuiw --imagedir directory_name
```

If the project JSON is not found and the provided imagedir folder contains is a set of images, then the images are sorted by time stamp, oldest to newest.  The first image file in the sorted list is used as the base image of the project and as a basis for the project name.  All images in the imagedir are imported into the project. An alternative base image can be chosen using the --base command parameter.  

```
% jtui  --imagedir images --base images/baseimage.jpg
```

## Projects

The tool represents a project as a directory that contanins image or video assets, both original and manipulated, masks and a project file (.json).  The project file describes the project.  A directory should only contain one project file.  The tool 'Save As' function does not permit two project files residing in the same directory.  'Save As' copies the contents of the current project directory to another project directory.  

### File Management 

When images or videos are added to a project, if the source file does not already reside in the project directory, it is copied to the directory.  If an file with the same name already exists in the directory, a name is assigned (appending a integer to the existing name).  The file type is unchanched. Adding the same file to the project results in a two separate copies of the file and its contents.  

If a file is added to the project directory, then the file is subject to removal if the associated node is removed from the tool.  Removing a link between nodes (manipulation action) results in removing the associated mask.

## Video Projects

Video projects are similar to image projects.

If the project JSON is not found and the videodir contains is a set of videos, then the videos are sorted by timestamp, oldest to newest. The first video file in the sorted list is used as the base video of the project and as a basis for the project name.  All videos in the videodir are imported into the project. An alternative base video can be chosen using the --base command parameter. 

When using video, the displays used to show images show a select frame from the video.

## Artifacts

Artifacts are all files associated with links and nodes.  A node represents a single video or image.  A link represents a operation that created the destination artifact from the source node's artifact.

Links record a single action taken on one image to produce another.  An image node can only have one input link (see Paste Splice below).  An image node can contribute to multiple different manipulation paths resulting in many different images.  Therefore, an image node may have many mant output lnks.

![Alt](doc/UIView.jpg "UI View")

