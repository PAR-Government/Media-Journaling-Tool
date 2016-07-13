# Dependencies

Install Python 2.7 (supposedly works with Anaconda)

Install Tkinter

Install PIL

Uses opencv (cv2)

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
```

# Usage

## Starting the UI

Add src/python to your PYTHONPATH.

```
% export PYTHONPATH=${PYTHONPATH}:src/python
% python src/python/MaskGenUI.py  --ops operations.csv images
```

The second argument is an initial project directory or project (JSON) file in the project directory.

## Projects

The tool represents a project as a directory that contanins image, both original and manipulated, image masks and a project file (.json).  The project file describes the project.  A directory should only contain one project file.  The tool 'Save As' function does not permit two project files residing in the same directory.  'Save As' copies the contents of the current project directory to another project directory.  

### Image File Management 

When images are added to a project, if the image does not already reside in the project directory, it is copied to the directory.  If an image file with the same name already exists in the directory, a name is assigned (appending a integer to the existing name).  The file/image type is unchanched. Adding the same image to the project results in a two separate copies of the image.  

If an image file is added to the project directory, then the image file is subject to removal if the image node is removed from the tool.  Removing a image link (manipulation action) results in removing the associated mask.

## Using the Tool

File > Open [Control-o] opens an existing project.

File > Save [Control-s] saves a project (JSON file).  All project artifacts and images are saved in the to the project directory.
 
File > Save As saves entire project to a new project directory and changes the name of the project.

File > New [Control-n] creates a new project.

File > Export [Control-e] creates a compressed archive file of the project including images and masks.

File > Quit [Control-q] Save and Quit

Process > Add Add a selected image to the project. The image can be linked to other images within the graph.

Process > Next w/Auto Pick [Control-p] automatically finds and picks the next modified version of the current image file.  The modified version of the file contains the same name as the initial image file, minus the file type suffix, with some additional characters.  If there is more than one modified version, they are processed in lexicographic order.  A dialog appears for each modification, capturing the type of modification and additional description (optional).  The dialog displays the next selected image as confirmation. A link is formed to the current image to the next selected image file.   If the next file is NOT found, the tool assumes the currently selected image has been overwritten, reloads that image file and gives it a new name.

Process > Next w/Add [Control-l] prompts with file finding window to select an image that differs from the current selected image by ONE modifications.  A dialog appears to capture the modification, including the type of modification and additional description (optional). The dialog dispays the next select image as confirmation. A link is formed between the current selected image to the newly loaded image.

Process > Next w/Filter [Control-f] prompts with modification to the current selected imaged.  The tool then applies the selected image to create a new image.  Unlike the other two 'next' functions, the set of operation is limited to those avaiable from the tool's plugins.  Furthermore, the image shown in the dialog window is the current selected image to which the selected modification is applied.

Process > Undo [Control-z] Undo the last operation performed.  The tool does not support undo of an undo.

# Links and Image Nodes

Links record a single action taken on one image to produce another.  An image node can only have one input link (see Paste Splice below).  An image node can contribute to multiple different manipulation paths resulting in many different images.  Therefore, an image node may have many mant output lnks.

![Alt](doc/UIView.jpg "UI View")

## Graph Operations

Image nodes may be selected, changing image display.  The image associated with selected image node is shown in the left most image box.  The right two boxes are left blank.  Image nodes can be removed.  All input and output links are removed.  All down-stream (output linked) nodes and links are removed.  Images can be connected to another image node.  When 'connect to' is selected, the cursor changes to a cross. Select on the another image node that is either an image node without any links (input or output) links OR an image node with one input link with operation PasteSplice (see Paste Splice below).  Image nodes may be exported.  Exporting an image node results the creation of compressed archive file with the node and all edges and nodes leading up to the node.  The name of the compressed file and the enclosed project is the node's image name (replacing '.' with '_').

Links may be selected, change the image display to show the output node, input node and associated different mask.  Removing link results in removeing the link and all downstream nodes and links.  Editing a link permits the user to change the operation and description.  Caution: do not change the operation name and description when using a plugin operation ([Process Next w/Filter [Ctrl-f]).


## Link Descriptions

Link descriptions include a category of operations, an operation name, a free-text description (optional), and software with version that performed the manipulation. The category and operation are either derived from the operations.csv file provided at the start of the tool or the plugins. Plugin-based manipulations prepopulate descriptions.  The software information is saved, per user, in a local user file. This allows the user to select from software that they currently use.  Adding a new software name or version results in extending the possible choices for that user.  Since each user may use different software with differant versions to manipulate images, the tool is not equipped nor does it enforce a single set, as is done with operations.

Link descriptions can include an input mask. An input mask is a mask used by the software as a parameter or set of parameters to create the output image.  For example, some seam carving tools request a mask describing areas to removal and areas for retention.  The input mask is an optional attachment.  When first attached to the description, the mask is not shown in the description dialog.  On subsequent edits, the image is both shown and able to be replaced with a new attachment.

## Other Meta-Data

No shown in the UI, the project JSON file also contains the operating system used to run the manipulation and the upload time for each image.

# Paste Splice

Paste Splice is a special operation that expects a donor image.  This is the only type of operation where a image node can have two incoming links.  The first link is PasteSplice, recording the difference from the prior image (the mask is only the spliced in image). The second link is a donor image. The tool enforces that a second incoming link to a node is a donor link.  The tool does not force donor links to exist.  Instead, the tool reminds the user to form the link.  There may be several steps to create a donor image from an initial image (e.g. bluring, cropping, etc). 

# Mask Generation

   It most cases, mask generation is a comparison between before and after manipulations of an image.  Full image operations like equlization, blur, color enhance, and anti-aliasing often effect all pixels resulting in a full image mask.  Since there operations can target specific pixels and since they may only effect some pixels (e.g. anti-aliasing), the mask does represent the scope of change.

   The mask generation algorithm gives special treatment to manipulations that alter the image size.  The algorithm first finds most common pixels in the smaller image to match the larger.  This is useful in cropping OR framing.  Interpolation applied when expanding an image may distort many pixels, causing a full change mask.  Smaller manipulated images are produced when cropping or seam cutting is applied. Seam cutting is typically done by finding an optimal cut. Seams can be cut both vertical or horizontally. Seam cutting may be considered as operations of region removal, sliding over the remaining pixels, and cropping.  It is expected that each cut is a separate operation.  For the tool to recognize seams cuts, two things must be present: an image size change, either vertically or horizontally, and a mismatched region.  Do not confuse seam cutting with a splice and crop--two separate manipulations.  Although the procedure to create splice involves a cut, paste, move and crop (of the remaining space), the entire effect is detected by a single non-linear line through an image. 

When performing manipulations, it is important to consider what is detectable in an modified image. A crop may not detectable, depending on the compression configuration, since the initial image is absent in the analysis.  A move manipulation, in itself, resembles an insert.  It is acceptable to group manipulations so long a their final result can be represented as one of the accepted singular operations configured with the tool. A pure crop does not produce a mask with identified changes.  Thus, it is important to the manipulation operation to understand the operation.

## Analytics

During mask generation, analytics are processed on the images.  
The analytics include:

* [Structural Similarity](https://en.wikipedia.org/wiki/Structural_similarity)
* [Peak Signal to Noise Ratio](https://en.wikipedia.org/wiki/Peak_signal-to-noise_ratio)

NOTE: Structual Similarity produces a warning on the tool command line output that can be safely ignored.  There is a bug within the scikit-image package where the compare_ssim function calls a known deprecated function for multichannel images.  Furthermore, the deprecation warning module reinstates the warning filter prior to issuing the warning, thus overriding warning suppression.

# Plugins

Plugin filters are python scripts.  They are located under a plugins directory.  Each plugin is a directory with a file __init__.py  The __init__ module must provide two functions: 

(1) 'operation()' that returns a list of five items 'operation name', 'operation category', 'description', 'python package','package version'
(2) 'transform(im)' that consumes a PIL Image and returns a PIL Image.

The python package and package version are automatically added to the list of software used by the manipulator.

# Known Issues

During mask calculation, the system r