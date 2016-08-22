hp_data
Renames files, copies them into a new directory with new name, and changes select metadata fields.

Requires install of Exiftool (http://www.sno.phy.queensu.ca/~phil/exiftool/)
--------------------------------------------
Usage:

python hp_data.py <args>
--------------------------------------------
arguments currently supported:
-D <dir>: Directory of images to be copied
-f <files>: Specific files to be copied
-r <files>: Will take a range of files to be copied
-R: Include to also grab images from subdirectories if using -D
-S <dir>: Secondary directory for images to be copied to
-m <file>: metadata text file. Uses metadata.txt in current working directory (cwd) by default
-P <file>: preferences text file. Uses preferences.txt in cwd by default
-A <str>: Adds additional info to new filenames
-X <extraData>: additional metadata to be stored externally (xdata.csv)
-K <keywords>: keywords associated with image set, to be stored externally (keywords.csv)
-B <dir>: S3 bucket/path to download preferences and upload CSV's with keywords and other external metadata
--------------------------------------------
The Keywords argument (-K)
This argument allows the user to attach keywords to the image set.
Keywords should be separated by spaces. If a multi-word keyword is desired, place them in quotation marks.

ex.
-K fog blurry "zoo animals"
This will associate the keywords "fog", "blurry", and "zoo animals" to the specified image set.

If keywords are supplied, the tool will generate a corresponding CSV file. These will assist with managing the images later.
They are formatted in the following way for easy editing in Excel or other editor:
keywords.csv
image1.jpg, keyword1
image1.jpg, keyword1
image1.jpg, keyword3
image2.jpg, keyword1
image2.jpg, keyword2
...

This file is saved with the renamed images and should be uploaded with the image set.
--------------------------------------------
The Extra Metadata argument (-X)
This argument allows the user to set metadata that is to be stored externally in a CSV file. Unlike keywords,
these are set as key-value pairs, similar to how standard Exif metadata is stored (Manufacturer: Nikon, etc.).
They should be specified in key value order on the command line.

ex.
-X fog true "zoo animals" 20
This will indicate to future users of this data that there was fog in this image, and 20 zoo animals.

If this extra metadata is supplied, the tool will generate a corresponding CSV file. These will assist with managing the images later.
They are formatted in the following way for easy editing in Excel or other editor:
xdata.csv
Filename, key1, key2, key3...
image1.jpg, value1, value2, value3...
image2.jpg, value1, value2, value3...
image3.jpg, value1, value2, value3...
...
Note that the first row and column simply has the word "Filename".

This file is saved with the renamed images and should be uploaded with the image set.
--------------------------------------------
Format of metadata text file:
TAG1=VALUE1
TAG2=VALUE2
...
Tags should be specified according to Exiftool documentation (http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/index.html)
--------------------------------------------
Preferences text file:
These two lines must be in the file:
username=USERNAME
organization=ORG
seq=00000

Valid organization names:
R, RIT,
M, U of M,
D, Drexel,
P, PAR

The seq line is used to generate the new filename. The tool will automatically generate/maintain this number. Do not change it.
A user may optionally specify an S3 bucket/path with the -B switch. Using this will search for preferences.txt 
in the specified location on the configured AWS cloud.
--------------------------------------------