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
Additional Text...: This text will be appended at the end of filenames in the set
Preview Filename: Preview the first new filename that will be copied
Edit Preferences: Opens dialog to enter Preferences (initials and organization).
Camera Information: Enter as much as you can. These will be set for every image in the spreadsheet.
Run: Clicking this will process the data: copy the files, extract/change metadata, and open the output CSV in a custom spreadsheet editor. It will only process new images. If there are no new images, it will simply open the spreadsheet for editing.
(KNOWN BUG: If the run button is still disabled after setting username/organization, open the Edit Preferences dialog again and close.)
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
White fields should be entered if you have that information available.


If the user chooses to enter keywords (click the Enter Keywords button on the main gui window), another spreadsheet will open, with only a few columns: the first being the image name, 
followed by 3 columns for keywords. The keywords are validated against a list, which can be found in hp_tool/data. This list should not be edited - contact an administrator to add a word.
Not every image needs all three keywords. More keyword columns can be added by clicking the "Add Column" button under "Edit" in the menu. 


OUTPUTS
--------------------------------------------
RIT CSV:
The RIT CSV includes the following information for each image:
"ImageFilename", "HP-CollectionRequestID", "HP-HDLocation", "OriginalImageName", "MD5","CameraModel", "DeviceSN","HP-DeviceLocalID" ,"LensModel",
"LensSN", "HP-LensLocalID" ,"FileType" ,"HP-JpgQuality" ,"ShutterSpeed" ,"Aperture" ,"ExpCompensation" ,"ISO", "NoiseReduction", "WhiteBalance",
"HP-DegreesKelvin", "ExposureMode", "FlashFired", "FocusMode", "CreationDate", "HP-Location", "GPSLatitude", "GPSLongitude", "CustomRendered",
"HP-OnboardFilter", "HP-OBFilterType", "BitDepth", "ImageWidth", "ImageHeight", "HP-LensFilter", "Type", "HP-Reflections", "HP-Shadows",
"HP-HDR", "HP-CameraKinematics", "HP-App", "HP-Inside", "HP-Outside"

History CSV:
The history CSV includes the following information:
"Original Name", "New Name", "MD5", "Type"


EXAMPLE USE
--------------------------------------------
 - I have just done some HP image collection. I have 200 images that I want processed and ingested.
 - I put all of my images into a single folder, named IN. I also create another empty folder, named OUT.
 - I run the tool, python hpgui.py
 - I specify the input directory. I click the Input directory button and choose my IN folder.
 - I specify the output directory. I click the Output directory button and choose my OUT folder.
 - I click the Edit Preferences button, type in my initials and confirm my organization.
 - These were not part of any specific collection task, so I leave Coll. Request ID blank.
 - The camera I used was PAR-1043, so I enter that in Local Camera ID.
 - I didn't use a separate lens, and I don't care to specify a hard drive location other than where the images are located. I leave those boxes blank.
 - I hit the Run button (known bug: if this is disabled, open and close preferences again)
 - The command prompt window shows progress/status of the processing
 - A spreadsheet opens with a list of the newly renamed image copies, which have metadata information updated to include my initials and organization
 - I go through the spreadsheet, and fill out all RED cells. Valid values for each cell appear in the bottom right, while a thumbnail of the image appears in the top-right.
 - I save and close the spreadsheet.
 - I click the button on the main UI to open the keywords sheet
 - Another spreadsheet opens, again with a list of the new images, and three columns
 - I go through my images and supply keywords from the list shown in the bottom right as appropriate
 - I close the window.

 Images are now ready for upload!
