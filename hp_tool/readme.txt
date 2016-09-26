hpgui.py
Renames files, copies them into a new directory with new name, and changes select metadata fields. Outputs CSV files with
various data fields.

Requires install of Exiftool (http://www.sno.phy.queensu.ca/~phil/exiftool/)
Dependencies:
pandastable (pip install)
change_all_metadata.py (included)
hp_data.py (included

--------------------------------------------
Usage: Navigate to hp_tool directory and run with:

python hpgui.py
--------------------------------------------

On the main GUI, there are a number of boxes and fields:
Input Directory: Use to specify directory of images
Output Directory: This is where renamed images will be copied to, as well as the output CSVs
Metadata File: Use this to specify path to metadata text file
Preferences File: Use this to specify path to preferences text file
Additional Text...: This text will be entered at the end of filenames in the set
Preview Filename: Preview the first new filename that will be copied

Camera Information:
Enter as much as you can. These will be set for every image in the spreadsheet.

Load: Clicking this will process the data: copy the files, extract/change metadata, and open the output CSV
Enter Keywords: (Disabled until Load is clicked) Opens Keywords spreadsheet for editing
Cancel: Closes the program


In the spreadsheet that opens after clicking Load, cells are several different colors:
Red fields are mandatory. These must be entered.
Grey fields already have data. Only change these if you have a very good reason.
White fields should be entered if you have that information.

--------------------------------------------
Format of metadata text file:
TAG1=VALUE1
TAG2=VALUE2
...
Tags should be specified according to Exiftool documentation (http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/index.html)

As a standard, the following should be inserted:
CopyrightNotice=� 2016 PAR Government Systems - Under contract of MediFor
By-line=INITIALS HERE
Credit=ORGANIZATION HERE
UsageTerms=CC0 1.0 Universal. https://creativecommons.org/publicdomain/zero/1.0/legalcodes
Copyright=
Artist=

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
OUTPUTS
--------------------------------------------
RIT CSV:
The RIT CSV includes the following information for each image:
ImageFilename	HP-CollectionRequestID	HP-HDLocation	OriginalImageName	MD5	CameraModel	DeviceSN	HP-DeviceLocalID
LensModel	LensSN	HP-LensLocalId	FileType	HP-JpgQuality	ShutterSpeed	Aperture	ExpCompensation	ISO
NoiseReduction	WhiteBalance	HP-DegreesKelvin	ExposureMode	FlashFired	FocusMode	CreationDate	HP-Location
GPSLatitude	HP-OnboardFilter	GPSLongitude	BitDepth	ImageWidth	ImageHeight	HP-OBFilterType	HP-LensFilter	Type
Reflections	Shadows

--------------------------------------------
History CSV:
The history CSV includes the following information:
Original Name	New Name	MD5	Type