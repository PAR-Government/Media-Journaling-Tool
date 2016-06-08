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
```

# Usage

## Starting the UI

Add src/python to your PYTHONPATH.

```
% export PYTHONPATH=${PYTHONPATH}:src/python
% python src/python/MaskGenUI.py  --ops operations.csv images
```

## Using the Tool

Control-o to open an initial image file.

Control-n to find the next modified version of the file.  The modified version of the file contains the same name as the initial image file, minus the file type suffix, with some additional characters.  If there is more than one modified version, they are processed in lexicographic order.  A dialog appears for each modification, capturing the type of modification and additional description (optional).  The type of modification supports auto-completion using the provided list of operations.

Control-f finishes the full set of modifications to the initial image file. During finishing step, the tool writes the series of modifiction descriptions to a json file, recording all the steps for taken to process the initial image file.  

The tool supports two behaviors.  The first is processing a series of modification files to the initial file (named in lexicographic order), where each modification file is in image representing a subsequent modification step.  Thus, the tool compares the last processed modification to the next one.  This is useful if each modification is recorded in a sequence of files.  The second behavior supports using the tool as part of incremental modification process. A user performs a modifiction to an image file, saves the file, then requests the 'next' action in this tool (Control-n), to record the modification. The steps continue until the user finishes (Control-f).


