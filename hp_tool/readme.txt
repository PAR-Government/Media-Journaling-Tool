hpgui.py
Renames files, copies them into a new directory with new name, and changes select metadata fields. Outputs CSV files with
various data fields.

Requires install of Exiftool (http://www.sno.phy.queensu.ca/~phil/exiftool/)
Support: Python 2.7
Dependencies (pip install):
pandastable
pandas
numpy
pillow

--------------------------------------------
Usage: Navigate to hp_tool directory and run with:

python hpgui.py
--------------------------------------------

On the main GUI, there are a number of boxes and fields:
Input Directory: Use to specify directory of images
Output Directory: This is where renamed images will be copied to, as well as the output CSVs
Metadata File: Use this to specify path to metadata text file. By default, this is stored in hp_tool/data
Preferences File: Use this to specify path to preferences text file. By default, this is stored in hp_tool/data
Additional Text...: This text will be entered at the end of filenames in the set
Preview Filename: Preview the first new filename that will be copied

Camera Information:
Enter as much as you can. These will be set for every image in the spreadsheet.

Run: Clicking this will process the data: copy the files, extract/change metadata, and open the output CSV
Enter Keywords: (Disabled until Load is clicked) Opens Keywords spreadsheet of current run for editing
Cancel: Closes the program

File menu:
The file menu has options for opening hp data and keywords spreadsheets for editing, without running the copy/rename/metadataupdate process.

--------------------------------------------
The CSV Window:
The CSV window shows the csv data as a spreadsheet, with common spreadsheet editing controls. It will show the data itself, along with the image corresponding to the currently
selected cell. Ctrl-T (Edit->Fill True) and Ctrl-F (Edit->Fill False) can be used to auto-fill the current selection with True or False, respectively. Ctrl-D (Edit->Fill Down) will fill the selection with the first
cell selected.

Cells are several different colors:
Red fields are mandatory. These must be entered.
Grey fields already have data. Only change these if you have a very good reason.
White fields should be entered if you have that information.


If the user chooses to enter keywords (click the Enter Keywords button on the main gui window), another spreadsheet will open, with only a few columns: the first being the image name, 
followed by 3 columns for keywords. The keywords are validated against a list, which can be found in hp_tool/data. This list should not be edited - contact an administrator to add a word.
Not every image needs all three keywords. More keyword columns can be added by clicking the "Add Column" button under "Edit" in the menu. 

--------------------------------------------
Format of metadata text file:
TAG1=VALUE1
TAG2=VALUE2
...
Tags should be specified according to Exiftool documentation (http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/index.html)

As a standard, the following should be inserted:
CopyrightNotice=� 2016 YOUR ORGANIZATION HERE - Under contract of MediFor
(If the images were originally taken for another purpose, remove the "Under contract of MediFor" bit)
By-line=INITIALS HERE
Credit=ORGANIZATION HERE
UsageTerms=CC0 1.0 Universal. https://creativecommons.org/publicdomain/zero/1.0/legalcodes
Copyright=
Artist=
(These last two fields should be left blank in order to wipe them. This clears up discrepancies when viewing image metadata)

--------------------------------------------
Preferences text file:
These two lines must be in the file:
username=USERNAME
organization=ORG

Valid organization names:
R, RIT,
M, U of M,
D, Drexel,
P, PAR,
C, CU Denver
--------------------------------------------
OUTPUTS
--------------------------------------------
RIT CSV:
The RIT CSV includes the following information for each image:
ImageFilename	HP-CollectionRequestID	HP-HDLocation	OriginalImageName	MD5	CameraModel	DeviceSN	HP-DeviceLocalID
LensModel	LensSN	HP-LensLocalId	FileType	HP-JpgQuality	ShutterSpeed	Aperture	ExpCompensation	ISO
NoiseReduction	WhiteBalance	HP-DegreesKelvin	ExposureMode	FlashFired	FocusMode	CreationDate	HP-Location
GPSLatitude	HP-OnboardFilter	GPSLongitude	BitDepth	ImageWidth	ImageHeight	HP-OBFilterType	HP-LensFilter	Type
HP-Reflections	HP-Shadows HP-App

--------------------------------------------
History CSV:
The history CSV includes the following information:
Original Name	New Name	MD5	Type