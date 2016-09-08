# Dependencies

Install Python 2.7 (Works with Anaconda)

Install Tkinter

Install PIL

Uses opencv (cv2)

Install exiftool

Install ffmpeg and ffmprobe for video processing.

For optional use of S3:
pip install awscli

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

### Video Projects

Video projects are similar to image projects.

If the project JSON is not found and the videodir contains is a set of videos, then the videos are sorted by timestamp, oldest to newest. The first video file in the sorted list is used as the base video of the project and as a basis for the project name.  All videos in the videodir are imported into the project. An alternative base video can be chosen using the --base command parameter. 

When using video, the displays used to show images show a select frame from the video.

## Projects

The tool represents a project as a directory that contanins image or video assets, both original and manipulated, masks and a project file (.json).  The project file describes the project.  A directory should only contain one project file.  The tool 'Save As' function does not permit two project files residing in the same directory.  'Save As' copies the contents of the current project directory to another project directory.  

### File Management 

When images or videos are added to a project, if the source file does not already reside in the project directory, it is copied to the directory.  If an file with the same name already exists in the directory, a name is assigned (appending a integer to the existing name).  The file type is unchanched. Adding the same file to the project results in a two separate copies of the file and its contents.  

If a file is added to the project directory, then the file is subject to removal if the associated node is removed from the tool.  Removing a link between nodes (manipulation action) results in removing the associated mask.

### Artifacts

Artifacts are all files associated with links and nodes.  A node represents a single video or image.  A link represents a operation that created the destination artifact from the source node's artifact.

Links record a single action taken on one image to produce another.  An image node can only have one input link (see Paste Splice below).  An image node can contribute to multiple different manipulation paths resulting in many different images.  Therefore, an image node may have many mant output lnks.

![Alt](doc/UIView.jpg "UI View")

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

Link descriptions include parameters.  Some parameters are mandatory, with '* added next to them.  These parameters must be set.  Parameter guidance is provided in the operation description, obtained with the information button, and on the parameter entry dialog.  Many operations include an optional input mask. An input mask is a mask used by the software as a parameter or set of parameters to create the output artifact.  For example, some seam carving tools request a mask describing areas to removal and areas for retention.  The input mask is an optional attachment.  When first attached to the description, the mask is not shown in the description dialog.  On subsequent edits, the input mask is both shown and able to be replaced with a new attachment.

## Other Meta-Data

Not shown in the UI, the project JSON file also contains the operating system used to run the manipulation and the upload time for each artifact.

# Paste Splice

Paste Splice is a special operation that expects a donor artifact.  This is the only type of operation where a node can have two incoming links.  The first link is PasteSplice, recording the difference from the prior node (the mask is only the spliced in image). The second link is a donor node. The tool enforces that a second incoming link to a node is a donor link.  The tool does not force donor links to exist.  Instead, the tool reminds the user to form the link.  There may be several steps to create a donor from an initial artifact (e.g. bluring, cropping, etc).   The tool expects one the last operation to select the component of the donor artifact (SelectRegion operation).  For images, this is done with an alpha-channel.  For videos, this is accomplished through a green screen tyoe approach.  The mask for the SelectRegion must reflect the removal of the irrelvant components (treated as background).  The donor link mask is the inverse of the SelectRegion mask.

# Mask Generation

   It most cases, mask generation is a comparison between before and after manipulations of an artfiact.  Full artifact operations like equlization, blur, color enhance, and anti-aliasing often effect all pixels resulting in a full mask.  Since there operations can target specific pixels(e.g. anti-aliasing), the mask represents the scope of change.

   The mask generation algorithm gives special treatment to manipulations that alter the image size.  The mask is the same size as the source node artifact.  The algorithm finds most common pixels in the smaller image to match the larger.  This is useful in cropping OR framing.  When cropping in image, the mask should inlude the frame around the cropped image.  When expanding image, the mask represents the comparison of the most closely related area.  If the expansion is due adding a frame, rather than some interpolation, then the mask will not reflect any change since the original pixels have not changed.

   The mask generation algorithm also is sensitive to rotations, generating mask reflecting the image after rotation.  A pure rotation with interpolation should have an empty change ask.  Rotations are counter-clockwise in degrees.  Consider a 90 degree rotation: interpolation is not needed and the mask is empty.  When rotating 45 degrees, the size of the resulting image must increase to accomodate entire image.   Since the mask size is the size of the initial image, the mask only indicates some distortion that occurred during the rotation.  The mask is created by first reversing the rotation back to the original image orientation and size.

## Video Masks

   Video masks are organized by video clips per section of the video affected by the change.  The masks are labeled with the start time in the source video where the change is deteced.  There may be more than one video clip.

## Composite Mask

The tool support creation of an aggregate summary mask, composed of masks from a leaf manipulated node to a base node.  By default, all masks that involve marking or pasting specific regions of the node are included in the composite mask.  Those links are colored blue and the link operation name is appended with an asterisk.  The status of the link can changed with the Composite Mask menu option.  Furthermore, the mask used for the composite can override the link mask, as a substitute.  

The image manipulator must insure the composite mask accurrately reflects ALL localize changes to a manipulated node from the base node. 

## EXIF Comparison

The tool has a dependency on the [exiftool](http://www.sno.phy.queensu.ca/~phil/exiftool).  By default, the tool is expected to be accessible via the name 'exiftool'.  This can be overwritten by the environmen variable MASKGEN_EXIFTOOL.  EXIF Comparison results are visible by inspecting the contents of a link.

## Frame Comparison

Video frames contain several types of meta-data including expected display time and frame type.  The tool performs a frame-by-frame comparison between source and destination video nodes for each link.  Packet position and size are excluded from the analysis, as these frequently change and tell very little about the actual change.  The presentation time stamp is used to compare the frames, as frames do not have their own identifiers.  The comparison includes changes in the meta-data per fram, and the detection of added or deleted frames.

## Analytics

### Images

During mask generation, analytics are processed on the images.  
The analytics include:

* [Structural Similarity](https://en.wikipedia.org/wiki/Structural_similarity)
* [Peak Signal to Noise Ratio](https://en.wikipedia.org/wiki/Peak_signal-to-noise_ratio)

NOTE: Structual Similarity produces a warning on the tool command line output that can be safely ignored.  There is a bug within the scikit-image package where the compare_ssim function calls a known deprecated function for multichannel images.  Furthermore, the deprecation warning module reinstates the warning filter prior to issuing the warning, thus overriding warning suppression.

### Video

Video does not have additional analytics at this time.


# Plugins

Plugin filters are python scripts.  They are located under a plugins directory.  Each plugin is a directory with a file __init__.py  The __init__ module must provide three functions: 

(1) 'operation()' that returns a list of five items 'operation name', 'operation category', 'description', 'python package','package version'
(2) 'transform(im,source,target,**kwargs)' that consumes a PIL Image, the source file name, the target file name and a set of arguments.  The function returns True if the EXIF should be copied from the source to target.
(3) 'arguments()' returns a list of tuples or None.  Each tuple contains an argument name, a default value and a string description. 

Plugins may provide a fourth function called 'suffix()'.  The function returns the file suffix of the image file it expects (e.g. .tiff, .jpg).  The expectation is that the plugin overwrites the contents of the file with data corresponding the suffix.

The tool creates a copy of the source image into a new file.  The path (i.e. location) of the new file is provided in the third argument (target).  The transform changes the select contents of that image file.  The image provided in the first argument the transform is a convenience, providing a copy of the image from the file.  The image is disconnected from the file, residing in memory.  If the transform returns True, then the tool copies the EXIF from the source image to the new image file.  This is often required since PIL(Pillow) Images do not retain all the EXIF data, with the exception of working with TIFF.  

The python package and package version are automatically added to the list of software used by the manipulator.

NOTE: At this time, the arguments are not typed.  

## Arguments

There are two special arguments: 'donor' and 'inputmaskpathname'.  

The system will prompt a user for an image node to fulfill the obligation of the donor. The transform function will be called with the user selected image (e.g. donor=image). Upon completion, separate Donor link is made between the donor image node and the image node created from the output of the transform operation.

The system prompts for an image file to fulfill the obligation of the inputmaskpathname.  The path name is provided the transform function (e.g. inputmaskpathname='/somepath').  The tool does not load the image in this case.  The image will be preserved within the project as the inputmask of the link, which references the image, upon completion of the operation.

All other arguments collected by the user will be provided as strings to the transform function.

# Group Manager

The Group Manager allows the user to create, remove and manage groups.  Groups are sets of plugin image transforms.  Only those transforms that do not require arguments are permitted within the group at this time.

# Batch Processing

The journaling tool currently supports a rudimentary batch processing feature. This is designed to operate on large quantities of images with the same type of simple manipulation. For example, 100 images are manipulated to have varying levels of saturation. These images can be specified with the tool’s batch feature, and will automatically generate the project, including the mask image and graph.

At its core, the batch tool requires only 1 directory, a directory of project directories. It can be run with the following:
```
python -m maskgen.batch.batch_process <args>

Mandatory arguments:
--projects <dir>: directory of project directories.

At least one of these three arguments must be present (see below for an explanation):
--sourceDir <dir>: directory of images
--plugin <pluginName>: plugin to perform
--jpg: Copies quantization tables and exif data from base image to save new jpeg image.

These arguments may be used only if using sourceDir:
--op <operation>: operation performed (required)
--softwareName <name>: manipulation software used (required)
--softwareVersion <version>: manipulation software version (required)
--endDir <dir>: directory of manipulated images (optional)
--inputMaskPath <dir>: directory containing input masks (optional)
--description <"descr">: description of manipulation performed (optional)
--additional <name1 value1 name2 value2...>: additional operation arguments, such as rotation (optional)

Optional arguments:
--projectDescription <"descr">: description of project (only used if creating new projects)
--technicalSummary <"descr">: technical summary of project (only used if creating new projects)
--username <"name">: username associated with the project
--continueWithWarning: use this tag to ignore warnings that check for valid operations, software, etc.
--s3 <bucket/path>: if included, will automatically upload projects to specified S3 bucket after performing operation
```

Different arguments will trigger different functionality:
1. Using both --sourceDir and --endDir will create new projects, using the images in sourceDir as base, and link them with the specified operation. This will also create the project directories and JSON files if necessary.
```
python -m maskgen.batch.batch_process --projects <DIR> --sourceDir <DIR> --endDir <DIR> --op ColorColorBalance --softwareName GIMP --softwareVersion 2.8
```
2. --sourceDir without --endDir will add the images in the source directory to the current project and link them to the most recent node with the specified operation.
```
python -m maskgen.batch.batch_process --projects <DIR> --sourceDir <DIR> --op ColorColorBalance --softwareName GIMP --softwareVersion 2.8
```
3. Use --plugin to specify a plugin to perform on the most recent image node.
```
python -m maskgen.batch.batch_process --projects <DIR> --plugin ColorEqHist
```
4. Using both --sourceDir and --plugin will assume you wish to create new projects using the images in sourceDir as base and performing the plugin operation on them.
```
python -m maskgen.batch.batch_process --projects <DIR> --sourceDir <DIR> --plugin ColorEqHist
```
5. Using --jpg will perform antiforensic jpeg export and exif copy on existing projects.
```
python -m maskgen.batch.batch_process --projects <DIR> --jpg
```
6. --jpg can be appended to any other input to also perform that functionality after the specified operation/plugin.
```
python -m maskgen.batch.batch_process --projects <DIR> --sourceDir <DIR> --plugin ColorEqHist --jpg
```

All images that are to be placed in the same project should have the same basename. Manipulated images should be appended with an underscore followed by some text and a number (i.e. image.jpg, image_01.jpg). 
For example :

sourceDir|endDir
---------|------
imageA.jpg|imageA_01.png
imageB.jpg|imageB_01.png
imageC.jpg|imageC_01.png

It is recommended the user view generated graphs by opening the projects in MaskGenUI once the processing is complete to verify.

## Bulk Operations
'''
python -m maskgen.batch.bulk_validate --projectDir <directoryOfProjects>
python -m maskgen.batch.bulk_export  -s <S3 bucker/folder> --dir <directoryOfProjects>
# Known Issues

# Latest Changes

7/21/2016:
1. EXIF Compare
2. Changed JSON
  * Move the 'idcount' data to the graph data.  
  * Edges may contain 'arguments'--a set of arguments used by a plugin
  * New edges will contain 'exifdiff', describing changes to each attribute of the exif.  Changes are 'add','delete' and 'change'. A 'change' contains old new value.
  * Graph data includes 'igversion' to indicate the version of the graph
  * Graph data includes 'typespref' contain the image type prefences in the order they are used by the tool for the specific project
3. Link view contains arguments and EXIF comparison data
4. About menu displays software verion
5. Changed the plugins to give more control to the plugin over the contents of the image file.

7/27/2016:
1. S3 Export
2. Software name/version validation
3. Operations and Software download from S3 or Http 
4. Validation Rules
5. Start up of new projects now can do a bulk add

8/1/2016:
1. Updated Software list
2. Fixed several validation rules
3. Fixed mask generation for JPEG Creation step
4. Removed Seam mask estimation
5. Fixed mask generation when an alpha-channel is introduced
6. Unified parameters
7. Introduced parameters for operations
8. Fixed back door to change a Donor link to some other operation

8/3/2016:
1. Fixed Image Rotation Mask
2. Fixed image shape size (X,Y) reversed.
3. Fixed Yellow select on link always selected.
4. Enforced mandatory parameters by disabling 'ok' button for link.
5. Added Operation descriptions and more parameters

8/12/2016
1. Added plugin support for batch tool
2. Added JPEG create option for batch tool
3. Added bulk validation tool

8/16/2016
1. Added Video Support (minus Composite video construction)
2. Added typed arguments
3. Fixed archiving and saveas losing mask overrides on links when constructing composite images.
4. Plugins argument require third item--the description of the argument.  Arguments associated with Operation parameters are prompted for the appropriate type.
