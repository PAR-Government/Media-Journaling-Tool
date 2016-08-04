# Dependencies

Install Python 2.7 (supposedly works with Anaconda)

Install Tkinter

Install PIL

Uses opencv (cv2)

Install exiftool

For optional use of S3:
pip install awscli

## Install commands

```
pip install pillow
brew tap homebrew/science
brew install opencv
pip install numpy
pip install matplotlib
pip install networkx
pip install moviepy
pip install scikit-image
pip install tkintertable
pip install bitstring

For optional use with S3
pip install boto3
```

# Usage

## Starting the UI

Add src/python to your PYTHONPATH.
Assumes operations.csv and software.csv are located in the same directory as the tool.


```
% export PYTHONPATH=${PYTHONPATH}:src/python
% python src/python/MaskGenUI.py  --imagedir images
```

The imagedir argument is a project directory with a project JSON file in the project directory.

If the project JSON is not found and the imagedir contains is a set of images, then the images are sorted alphabetically, in the order JPG, PNG and TIFF, respectively. The first image file in the sorted list is used as the base image of the project and as a basis for the project name.  All images in the imagedir are imported into the project. An alternative base image can be chosen using the --base command parameter.  

```
% python src/python/MaskGenUI.py  --imagedir images --base images/baseimage.jpg
```

If the operations.csv and software.csv are to be downloaded from a S3 bucket, then
(1) Use command aws configure to setup you Access Id and Key
(2) add the argument --s3 bucketname/pathname, for example MyBucket/metaData

## Projects

The tool represents a project as a directory that contanins image, both original and manipulated, image masks and a project file (.json).  The project file describes the project.  A directory should only contain one project file.  The tool 'Save As' function does not permit two project files residing in the same directory.  'Save As' copies the contents of the current project directory to another project directory.  

### Image File Management 

When images are added to a project, if the image does not already reside in the project directory, it is copied to the directory.  If an image file with the same name already exists in the directory, a name is assigned (appending a integer to the existing name).  The file/image type is unchanched. Adding the same image to the project results in a two separate copies of the image.  

If an image file is added to the project directory, then the image file is subject to removal if the image node is removed from the tool.  Removing a image link (manipulation action) results in removing the associated mask.

## Using the Tool

File > Open [Control-o] opens an existing project.

File > Save [Control-s] saves a project (JSON file).  All project artifacts and images are saved in the to the project directory.
 
File > Save As saves entire project to a new project directory and changes the name of the project.

File > New [Control-n] creates a new project.  Select a base image file.  The directory containing that image file becomes the project directory.  The name of project is based on the name of the image file, removing the file type suffix. All images in the directory are automatically imported into the project.

File > Export > To File [Control-e] creates a compressed archive file of the project including images and masks.

File > Export > To S3 creates a compressed archive file of the project and uploads to a S3 bucket and folder.  The user is prompted for the bucket/folderpath, separated by '/'.

File > Fetch Meta-Data(S3) prompts the user for the bucket and path to pull down operations.csv and software.csv from an S3 bucket. The user is prompted for the bucket/folderpath, separated by '/\'.

File > Validate Runs a validation rules on the project.  Erros are displayed in a list box. Clicking on each error high-lights the link or node in the graph, as if selected in the graph.

File > Group Manager opens a separate dialog to manage groups of plugin filters.

File > Quit [Control-q] Save and Quit

Process > Add Images adds selected images to the project. Each image can be linked to other images within the graph.

Process > Next w/Auto Pick [Control-p] picks an image node without neighbors.  The chosen image node is the next node in found in lexicographic order. Preference is given to those image nodes that share the same prefix as the currently selected node. A dialog appears to capture the manipulation information including the type and additional description (optional).  The dialog displays the next selected image as confirmation. A link is then formed forom the current image node to the selected image node.

Process > Next w/Auto Pick from File finds a modified version of current image file from the project directory.  The modified version of the file contains the same name as the initial image file, minus the file type suffix, with some additional characters.  If there is more than one modified version, they are processed in lexicographic order.  A dialog appears for each modification, capturing the type of modification and additional description (optional).  The dialog displays the next selected image as confirmation. A link is formed to the current image to the next selected image file.

Process > Next w/Add [Control-l] prompts with file finding window to select an image that differs from the current selected image by ONE modifications.  A dialog appears to capture the modification, including the type of modification and additional description (optional). The dialog dispays the next select image as confirmation. A link is formed between the current selected image to the newly loaded image.

Process > Next w/Filter [Control-f] prompts with modification to the current selected imaged.  The tool then applies the selected image to create a new image.  Unlike the other two 'next' functions, the set of operation is limited to those avaiable from the tool's plugins.  Furthermore, the image shown in the dialog window is the current selected image to which the selected modification is applied.

Process > Next w/Filter Group runs a group of plugin transforms against the selected image, creating an image node for each transform and a link to the new images from the selected image.

Process > Next w/Filter Sequence runs a group of plugin transforms in a sequence starting with the selected image.  Each transform results in a new image node.  The result from one transform is the input into the next transform.  Links are formed between each image node, in the same sequence.

Process > Create JPEG is a convenience operation that runs two plugin filters, JPEG compression using the base image QT and EXIF copy from the base image, on the final manipulation nodes.  The end result is two additional nodes per each final manipulation node, sequenced from the manipulation node.  Included is the Donor links from the base image.  This operation only applies to JPEG base images.

Process > Undo [Control-z] Undo the last operation performed.  The tool does not support undo of an undo.

# Links and Image Nodes

Links record a single action taken on one image to produce another.  An image node can only have one input link (see Paste Splice below).  An image node can contribute to multiple different manipulation paths resulting in many different images.  Therefore, an image node may have many mant output lnks.

![Alt](doc/UIView.jpg "UI View")

## Graph Operations

Image nodes may be selected, changing image display.  The image associated with selected image node is shown in the left most image box.  The right two boxes are left blank.  Image nodes can be removed.  All input and output links are removed.  All down-stream (output linked) nodes and links are removed.  Images can be connected to another image node.  When 'connect to' is selected, the cursor changes to a cross. Select on the another image node that is either an image node without any links (input or output) links OR an image node with one input link with operation PasteSplice (see Paste Splice below).  Image nodes may be exported.  Exporting an image node results the creation of compressed archive file with the node and all edges and nodes leading up to the node.  The name of the compressed file and the enclosed project is the node's image name (replacing '.' with '_').

Links may be selected, change the image display to show the output node, input node and associated different mask.  Removing link results in removeing the link and all downstream nodes and links.  Editing a link permits the user to change the operation and description.  Caution: do not change the operation name and description when using a plugin operation ([Process Next w/Filter [Ctrl-f]).


## Link Descriptions

Link descriptions include a category of operations, an operation name, a free-text description (optional), and software with version that performed the manipulation. The category and operation are either derived from the operations.csv file provided at the start of the tool or the plugins. Plugin-based manipulations prepopulate descriptions.  The software information is saved, per user, in a local user file. This allows the user to select from software that they currently use.  Adding a new software name or version results in extending the possible choices for that user.  Since each user may use different versions of software to manipulate images, the user can override the version set, as the versions associated with each software may be incomplete.  It is important to reach out the management team for the software.csv to add the appropriate version.

Link descriptions include parameters.  Some parameters are mandatory, with '* added next to them.  These parameters must be set.  Parameter guidance is provided in the operation description, obtained with the information button.  Many operations include an optional input mask. An input mask is a mask used by the software as a parameter or set of parameters to create the output image.  For example, some seam carving tools request a mask describing areas to removal and areas for retention.  The input mask is an optional attachment.  When first attached to the description, the mask is not shown in the description dialog.  On subsequent edits, the image is both shown and able to be replaced with a new attachment.

## Other Meta-Data

No shown in the UI, the project JSON file also contains the operating system used to run the manipulation and the upload time for each image.

# Paste Splice

Paste Splice is a special operation that expects a donor image.  This is the only type of operation where a image node can have two incoming links.  The first link is PasteSplice, recording the difference from the prior image (the mask is only the spliced in image). The second link is a donor image. The tool enforces that a second incoming link to a node is a donor link.  The tool does not force donor links to exist.  Instead, the tool reminds the user to form the link.  There may be several steps to create a donor image from an initial image (e.g. bluring, cropping, etc). 

# Mask Generation

   It most cases, mask generation is a comparison between before and after manipulations of an image.  Full image operations like equlization, blur, color enhance, and anti-aliasing often effect all pixels resulting in a full image mask.  Since there operations can target specific pixels and since they may only effect some pixels (e.g. anti-aliasing), the mask does represent the scope of change.

   The mask generation algorithm gives special treatment to manipulations that alter the image size.  The algorithm first finds most common pixels in the smaller image to match the larger.  This is useful in cropping OR framing.  Interpolation applied when expanding an image may distort many pixels, causing a full change mask.  Smaller manipulated images are produced when cropping or seam cutting is applied. Seam cutting is typically done by finding an optimal cut. Seams can be cut both vertical or horizontally. Seam cutting may be considered as operations of region removal, sliding over the remaining pixels, and cropping.  It is expected that each cut is a separate operation.  

When performing manipulations, it is important to consider what is detectable in an modified image. A crop may not detectable, depending on the compression configuration, since the initial image is absent in the analysis.  A move manipulation, in itself, resembles an insert.  It is acceptable to group manipulations so long a their final result can be represented as one of the accepted singular operations configured with the tool. A pure crop does not produce a mask with identified changes.  Thus, it is important to the manipulation operation to understand the operation.

# Composite Mask

The tool support creation of a summary mask, composed of masks from a leaf manipulated image to a base image.  By default, all masks that involve marking or pasting specific regions of the image are included in the composite mask.  Those links are colored blue and the link operation name is appended with an asterisk.  The status of the link can changed with the Composite Mask menu option.  Furthermore, the mask used for the composite can override the link mask, as a substitute.  

## EXIF Comparison

The tool has a dependency on the [exiftool](http://www.sno.phy.queensu.ca/~phil/exiftool).  By default, the tool is expected to be accessible via the name 'exiftool'.  This can be overwritten by the environmen variable MASKGEN_EXIFTOOL.  EXIF Comparison results are visible by inspecting the contents of a link.

## Analytics

During mask generation, analytics are processed on the images.  
The analytics include:

* [Structural Similarity](https://en.wikipedia.org/wiki/Structural_similarity)
* [Peak Signal to Noise Ratio](https://en.wikipedia.org/wiki/Peak_signal-to-noise_ratio)

NOTE: Structual Similarity produces a warning on the tool command line output that can be safely ignored.  There is a bug within the scikit-image package where the compare_ssim function calls a known deprecated function for multichannel images.  Furthermore, the deprecation warning module reinstates the warning filter prior to issuing the warning, thus overriding warning suppression.

# Plugins

Plugin filters are python scripts.  They are located under a plugins directory.  Each plugin is a directory with a file __init__.py  The __init__ module must provide three functions: 

(1) 'operation()' that returns a list of five items 'operation name', 'operation category', 'description', 'python package','package version'
(2) 'transform(im,source,target,**kwargs)' that consumes a PIL Image, the source file name, the target file name and a set of arguments.  The function returns True if the EXIF should be copied from the source to target.
(3) 'arguments()' returns a list of tuples or None.  Each tuple contains an argument name and a default value. 

Plugins may provide a fourth function called 'suffix()'.  The function returns the file suffix of the image file it expects (e.g. .tiff, .jpg).  The expectation is that the plugin overwrites the contents of the file with data corresponding the suffix.

The tool creates a copy of the source image into a new file.  The path (i.e. location) of the new file is provided in the third argument (target).  The transform changes the select contents of that image file.  The image provided in the first argument the transform is a convenience, providing a copy of the image from the file.  The image is disconnected from the file, residing in memory.  If the transform returns True, then the tool copies the EXIF from the source image to the new image file.  This is often required since PIL(Pillow) Images do not retain all the EXIF data, with the exception of working with TIFF.  

The python package and package version are automatically added to the list of software used by the manipulator.

## Arguments

There are two special arguments: 'donor' and 'inputmaskpathname'.  

The system will prompt a user for an image node to fulfill the obligation of the donor. The transform function will be called with the user selected image (e.g. donor=image). Upon completion, separate Donor link is makde between the donor image node and the image node created from the output of the transform operation.

The system prompts for an image file to fulfill the obligation of the inputmaskpathname.  The path name is provided the transform function (e.g. inputmaskpathname='/somepath').  The tool does not load the image in this case.  The image will be preserved within the project as the inputmask of the link, which references the image, upon completion of the operation.

All other arguments collected by the user will br provided as strings to the transform function.

# Group Manager

The Group Manager allows the user to create, remove and manage groups.  Groups are sets of plugin image transforms.  Only those transforms that do not require arguments are permitted within the group at this time.

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
