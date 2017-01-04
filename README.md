# Dependencies

Install exiftool

Install ffmpeg and ffmprobe for video processing.

## Install commands

### Open CV
```
brew tap homebrew/science
brew install opencv

```
### Tool
```
python setup.py develop
```

## For Anaconda
You may need to update pillow:
```
conda remove PIL
conda remove pillow
pip install Image
```

OpenCV is installed with:
```
conda install -c https://conda.binstar.org/menpo opencv
```

For Anaconda users wishing to use FFMPEG:

*	Dowload and install FFMPEG 3.1.1.
*	Download and install opencv 2.4.13 fro opencv.org using the appropriate architecture (x86 or x64).  Make sure it is built with FFMPEG.  This is confirmed by looking for opencv/build/x64/vc11/opencv_ffmpeg2413_64.dll.  Follow build-from-source instructions for opencv to include FFMPEG.
*	Copy opencv/build/python/2.7/x64/cv2.pyd (or x86/cv2.pyd for the x86 architecture) to Anaconda2/Lib/site-packages
*	Set environment variables:
*	32-bit: Set OPENCV_DIR to the absolute path of opencv/x86/vc11
*	64-bit: Set OPENCV_DIR to the absolute path of opencv/x64/vc11
*	Add to PATH: %OPENCV_DIR%\bin
*	Add to Path: FFMPEG’s bin directory
Test :
*	run python
*	import cv2
*	print cv2.__version__

## Other Packages

HDF5:
```
brew install homebrew/science/hdf5
```

FFMPEG (not Anaconda): 
```
pip install ffmpeg
```

# Usage

## Starting the UI

Assumes operations.json and software.csv are located in the same directory as the tool.  The backup files in the resources are used when the local versions are not found.


```
% python -m maskgen.MaskGenUI --imagedir images
```

The imagedir argument is a project directory with a project JSON file in the project directory.


If the project JSON is not found and the imagedir contains is a set of images, then the images are sorted by time stamp, oldest to newest.  The first image file in the sorted list is used as the base image of the project and as a basis for the project name.  All images in the imagedir are imported into the project. An alternative base image can be chosen using the --base command parameter.  

```
% python -m maskgen.MaskGenUI  --imagedir images --base images/baseimage.jpg
```

If the operations.csv and software.csv are to be downloaded from a S3 bucket, then
(1) Use command aws configure to setup you Access Id and Key
(2) add the argument --s3 bucketname/pathname, for example MyBucket/metaData

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

# Detailed Document

For the most up-to-date detailed documentation, see doc/MediForJournalingTool-public.docx. This README is a summary. 

## Using the Tool

File > Open [Control-o] opens an existing project.

File > Save [Control-s] saves a project (JSON file).  All project artifacts are saved in the to the project directory.
 
File > Save As saves entire project to a new project directory and changes the name of the project.

File > New [Control-n] creates a new project.  Select a base image or video file.  The directory containing that file becomes the project directory.  The name of project is based on the name of the file, removing the file type suffix. All images or videos in the directory are automatically imported into the project.

File > Export > To File [Control-e] creates a compressed archive file of the project including referenced artifacts.

File > Export > To S3 creates a compressed archive file of the project and uploads to a S3 bucket and folder.  The user is prompted for the bucket/folderpath, separated by '/'.

File > Fetch Meta-Data(S3) prompts the user for the bucket and path to pull down operations.csv and software.csv from an S3 bucket. The user is prompted for the bucket/folderpath, separated by '/\'.

File > Validate Runs a validation rules on the project.  Erros are displayed in a list box. Clicking on each error high-lights the link or node in the graph, as if selected in the graph.

File > Group Manager opens a separate dialog to manage groups of plugin filters.

File > Settings > Username allows a user to change their name associated with the project. This setting will be saved for future projects. Changing this will not change the username associated with links that have already been created in the project.

File > Quit [Control-q] Save and Quit

Process > Add Images adds selected images to the project. Each image can be linked to other images within the graph.

Process > Add Video adds selected video to the project. Each video can be linked to other videos within the graph.

Process > Next w/Auto Pick [Control-p] picks a node without neighbors.  The chosen node is the next node in found in lexicographic order. Preference is given to those nodes that share the same prefix as the currently selected node. A dialog appears to capture the manipulation information including the type and additional description (optional).  The dialog displays the next selected node name as confirmation. A link is then formed from the current node to the selected node.

Process > Next w/Auto Pick from File finds a modified version of current file from the project directory.  The modified version of the file contains the same name as the initial file, minus the file type suffix, with some additional characters.  If there is more than one modified version, they are processed in lexicographic order.  A dialog appears for each modification, capturing the type of modification and additional description (optional).  The dialog displays the next selected image or video snapshot as confirmation. A link is formed to the current image to the next selected image file.

Process > Next w/Add [Control-l] prompts with file finding window to select an file whose contents differ from the current selected node's artifact by ONE modifications.  A dialog appears to capture the modification, including the type of modification and additional description (optional). The dialog dispays the next selected artifact as confirmation. A link is formed between the current selected node to the newly loaded artifact.

Process > Next w/Filter [Control-f] prompts with modification to the current selected node.  The tool then applies a filter to the selected node's artifact to create a new artifact.  Unlike the other two 'next' functions, the set of operation is limited to those avaiable from the tool's plugins.  Furthermore, the image shown in the dialog window is the snapshot of current selected artifact to which the selected modification is applied.

Process > Next w/Filter Group runs a group of plugin transforms against the selected node, creating a node for each transform and a link to the new node from the selected node.

Process > Next w/Filter Sequence runs a group of plugin transforms in a sequence starting with the selected node.  Each transform results in a new node.  The result from one transform is the input into the next transform.  Links are formed between each node, in the same sequence.

Process > Create JPEG is a convenience operation that runs two plugin filters, JPEG compression using the base image QT and EXIF copy from the base image, on the final manipulation nodes.  The end result is two additional nodes per each final manipulation node, sequenced from the manipulation node.  Included is the Donor links from the base image.  This operation only applies to JPEG base images.

Process > Undo [Control-z] Undo the last operation performed.  The tool does not support undo of an undo.

# Graph Operations

Nodes may be selected, changing image display.  The image associated with selected node is shown in the left most image box. For videos, the image shown is a select frame from the video.  The right two boxes are left blank.  

Nodes can be removed.  All input and output links are removed.  Nodes can be connected to another node via a link.  When 'connect to' is selected, the cursor changes to a cross. Select on the another node that is either an node without any links (input or output) links OR a node with one input link with operation PasteSplice (see Paste Splice below).  Nodes may be exported.  Exporting an node results the creation of compressed archive file with the node and all links and nodes leading up to the node.  The name of the compressed file and the enclosed project is the node's name (replacing '.' with '_').

Links may be selected, change the image display to show the output node, input node and associated different mask.  Removing link results in removeing the link and all downstream nodes and links.  Editing a link permits the user to change the operation and description.  Caution: do not change the operation name and description when using a plugin operation ([Process Next w/Filter [Ctrl-f]).


## Link Descriptions

Link descriptions include a category of operations, an operation name, a free-text description (optional), and software with version that performed the manipulation. The category and operation are either derived from the operations.csv file provided at the start of the tool or the plugins. Plugin-based manipulations prepopulate descriptions.  The software information is saved, per user, in a local user file. This allows the user to select from software that they currently use.  Adding a new software name or version results in extending the possible choices for that user.  Since each user may use different versions of software to manipulate artficats, the user can override the version set, as the versions associated with each software may be incomplete.  It is important to reach out the management team for the software.csv to add the appropriate version.

Link descriptions include parameters.   These parameters must be set.  Parameter guidance is provided in the operation description, obtained with the parameter name button.  Many operations include an optional input mask. An input mask is a mask used by the software as a parameter or set of parameters to create the output artifact.  For example, some seam carving tools request a mask describing areas to removal and areas for retention.  


# Mask Generation

   It most cases, mask generation is a comparison between before and after manipulations of an artfiact.  Full artifact operations like equlization, blur, color enhance, and anti-aliasing often effect all pixels resulting in a full mask.  Since there operations can target specific pixels(e.g. anti-aliasing), the mask represents the scope of change.

   The mask generation algorithm gives special treatment to manipulations that alter the image size.  The mask is the same size as the source node artifact.  The algorithm finds most common pixels in the smaller image to match the larger.  This is useful in cropping OR framing.  When cropping in image, the mask should inlude the frame around the cropped image.  When expanding image, the mask represents the comparison of the most closely related area.  If the expansion is due adding a frame, rather than some interpolation, then the mask will not reflect any change since the original pixels have not changed.

   The mask generation algorithm also is sensitive to rotations, generating mask reflecting the image after rotation.  A pure rotation with interpolation should have an empty change ask.  Rotations are counter-clockwise in degrees.  Consider a 90 degree rotation: interpolation is not needed and the mask is empty.  When rotating 45 degrees, the size of the resulting image must increase to accomodate entire image.   Since the mask size is the size of the initial image, the mask only indicates some distortion that occurred during the rotation.  The mask is created by first reversing the rotation back to the original image orientation and size.

## Video Masks

   Video masks are organized by video clips per section of the video affected by the change.  The masks are labeled with the start time in the source video where the change is deteced.  There may be more than one video clip.

## Composite Mask

The tool support creation of an aggregate summary mask, composed of masks from a leaf manipulated node to a base node.  By default, all masks that involve marking or pasting specific regions of the node are included in the composite mask.  Those links are colored blue and the link operation name is appended with an asterisk.  The status of the link can changed with the Composite Mask menu option.  Furthermore, the mask used for the composite can override the link mask, as a substitute.  

## Donor mask

The tool support creation of a donor mask, transforming a donor mask onto the original donor image. 

The image manipulator must insure the composite mask accurrately reflects ALL localize changes to a manipulated node from the base node. 
## EXIF Comparison

The tool has a dependency on the [exiftool](http://www.sno.phy.queensu.ca/~phil/exiftool).  By default, the tool is expected to be accessible via the name 'exiftool'.  This can be overwritten by the environmen variable MASKGEN_EXIFTOOL.  EXIF Comparison results are visible by inspecting the contents of a link.

## Frame Comparison

Video frames contain several types of meta-data including expected display time and frame type.  The tool performs a frame-by-frame comparison between source and destination video nodes for each link.  Packet position and size are excluded from the analysis, as these frequently change and tell very little about the actual change.  The presentation time stamp is used to compare the frames, as frames do not have their own identifiers.  The comparison includes changes in the meta-data per fram, and the detection of added or deleted frames.
