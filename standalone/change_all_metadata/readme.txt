change_all_metadata.py

changes the metadata specified in metadata text file of ALL jpeg and tiff format images in directory.

dependencies:
pyexiv2: http://tilloy.net/dev/pyexiv2/download.html

run on command line using:
python change_all_metadata.py <args>

by default, changes metadata of images in current directory based on file metadata.txt (in current directory).

all arguments are optional:

use -d to specify image directory:
python change_all_metadata.py -d C:\otherDir

use -m to specify metadata file (metadata.txt is default):
python change_all_metadata.py -m newmetadatafile.txt

use -p to instead delete all tags in file:
python change_all_metadata.py -p

use -r to change metadata in all subdirectories as well
python change_all_metadata.py -r


metadata text file must have contents formatted correctly:
TAG1=VALUE1
TAG2=VALUE2

-> TAG must be spelled exactly according to Exiv2 documentation (http://exiv2.org/metadata.html)
-> No space around equals sign
-> User can delete an individual tag's value by leaving the right side blank (no spaces)
	i.e. TAG3=