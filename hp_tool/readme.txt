hp_data
Renames files, copies them into a new directory with new name, and changes select metadata fields.

Requires install of Exiftool (http://www.sno.phy.queensu.ca/~phil/exiftool/)
Dependencies:
change_all_metadata.py (included)
--------------------------------------------
Usage:

python hp_data.py <args>
--------------------------------------------
arguments currently supported:
(either switch, - or -- can be used)
-S, --secondary <dir>: Secondary directory for images to be copied to. If not provided, will copy to current working directory (cwd)
-D, --dir <dir>: Directory of images to be copied
-R, --recursive: Include to also grab images from subdirectories if using -D
-f, --files <files>: Specific files to be copied
-r, --range <files>: Will take a range of files to be copied
-m, --metadata <file>: metadata text file. Uses metadata.txt in cwd by default
-X, --extraMetadata <key value...>: additional metadata to be stored externally (xdata.csv)
-K, --keywords <keywords>: keywords associated with image set, to be stored externally (keywords.csv)
-P, --preferences <file>: preferences text file. Uses preferences.txt in cwd by default
-A, --additionalInfo <str>: Adds additional info to new filenames
-T, --tally: generates tally file

The following arguments set data in the output tally and RIT CSVs only:
-C, --collection <data>: Collection Req. #
-i, --id <data>: Camera serial number
-o, --lid <data>: Local ref number (RIT cage #, etc)
-L, --lens <data>: Lens serial number
-H, --hd <data>: Custom hard drive location (e.g. A)
-s, --sspeed <data>: Shutter speed
-N, --fnum <data>: F-number
-e, --expcomp <data>: Exposure Compensation
-I, --iso <data>: ISO
-n, --noisered <data>: Noise reduction
-w, --whitebal <data>: White balance mode
-k, --kval <data>: Color temperature (in K)
-E, --expmode <data>: Exposure mode
-F, --flash <data>: Flash setting
-a, --autofocus <data>: Focus setting
-l, --location <data>: General location
-c, --filter <data>: Specify on-board filter

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

This file is saved with the renamed images.
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

This file is saved with the renamed images.
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
It is recommended to store this file somewhere externally, so that it can be pulled and used regardless of the user's machine.
--------------------------------------------
RIT CSV
The RIT CSV includes the following information for each image:
ImageFilename	CollectionAssignmentID	HDLocation	OriginalImageName	MD5	DeviceSN	DeviceLocalID	LensSN	LensLocalId
FileType	JpgQuality	ShutterSpeed	Aperture	ExpCompensation	ISO	NoiseReduction	WhiteBalance	DegreesKelvin	
ExposureMode	FlashFired	FocusMode	CreationDate	Location	GPSLatitude	OnboardFilter	GPSLongitude	
BitDepth	ImageWidth	ImageHeight


--------------------------------------------
Tally CSV
The tally CSV includes the following information:
DeviceSN	DeviceLocalID	LensSN	LocalLensID	Extension	ShutterSpeed	Aperture	ISO	BitDepth	Tally


The tally counts how many images in that set had the same of these settings.
The tally CSV can be updated once it is generated, just make sure the CSV file is in the desired output directory.