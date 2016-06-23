# Dependencies

Install Tkinter

Install PIL

## Install commands

```
pip install pillow
brew tap homebrew/science
brew install opencv
pip install numpy
pip install matplotlib
pip install networkx
```

# Usage

## Starting the UI

Add src/python to your PYTHONPATH.

```
% export PYTHONPATH=${PYTHONPATH}:src/python
% python src/python/MaskGenUI.py  --ops operations.csv images
```

## Using the Tool

Control-o to open a project

Control-s to save a project.  All project artifacts and images are saved in the one directory provided to the tool at start up.
 
Control-n creates a new project.

Control-p to automatically find and pick the next modified version of the file.  The modified version of the file contains the same name as the initial image file, minus the file type suffix, with some additional characters.  If there is more than one modified version, they are processed in lexicographic order.  A dialog appears for each modification, capturing the type of modification and additional description (optional).  The type of modification supports auto-completion using the provided list of operations.

Control-f applies a plugin the selected image, creating new image and mask.

Control-a is like Contron-p, accept the user can pik the next modified version of file using a file browsing dialo.

The Control-p supports two behaviors.  The first is processing a series of modification files to the initial file (named in lexicographic order), where each modification file is in image representing a subsequent modification step.  Thus, the tool compares the last processed modification to the next one.  This is useful if each modification is recorded in a sequence of files.  The second behavior supports using the tool as part of incremental modification process. A user performs a modifiction to an image file, saves the file, then requests the 'next' action in this tool (Control-p), to record the modification.

# Mask Generation

   It most cases, mask generation is a comparison between before and after manipulations of an image.  Full image operations like equlization, blur, color enhance, and anti-aliasing often effect all pixels resulting in a full image mask.  Since there operations can target specific pixels and since they may only effect some pixels (e.g. anti-aliasing), the mask does represent the scope of change.

   The mask generation algorithm gives special treatment to manipulations that alter the image size.  The algorithm first finds most common pixels in the smaller image to match the larger.  This is useful in cropping OR framing.  Interpolation applied when expanding an image may distort many pixels, causing a full change mask.  Smaller manipulated images are produced when cropping or seam cutting is applied. Seam cutting is typically done by finding an optimal cut. Seams can be cut both vertical or horizontally. Seam cutting may be considered as operations of region removal, sliding over the remaining pixels, and cropping.  It is expected that each cut is a separate operation.  For the tool to recognize seams cuts, two things must be present: an image size change, either vertically or horizontally, and a mismatched region.  Do not confuse seam cutting with a splice and crop--two separate manipulations.  Although the procedure to create splice involves a cut, paste, move and crop (of the remaining space), the entire effect is detected by a single edge through an image. 

When performing manipulations, it is important to consider what is detectable in an modified image. A crop may not detectable, depending on the compression configuration, since the initial image is absent in the analysis.  A move manipulation, in itself, resembles an insert.  It is acceptable to group manipulations so long a their final result can be represented as one of the accepted singular operations configured with the tool. A pure crop does not produce a mask with identified changes.  Thus, it is important to the manipulation operation to understand the operation.

# Plugins

Plugin filters are python scripts.  They are located under a plugins directory.  Each plugin is a directory with a file __init__.py  The __init__module must provide two functions: 

(1) 'operation()' that returns a list of three items 'operation name', 'operation category' and 'description'
(2) 'transform(im)' that consumes a PIL Image and returns a PIL Image.
