hpgui.py

Copies files to prepare them for browser ingest. Copied files will have their metadata changed (originals remain intact).
Once files are copied, allows for annotating and upload of files through a simple spreadsheet interface.

Also allows for the processing and upload of PRNU data.

Requires install of Exiftool (http://www.sno.phy.queensu.ca/~phil/exiftool/)
Support: Python 2.7

------------------------------------------
INSTALLATION

On the command line, navigate (cd) into the hp_tool directory, and enter:

        python setup.py install

This will verify the installation of the following dependencies:
requests
pandastable
pandas
pillow
boto3 (for s3 export)
botocore (for s3 export)

--------------------------------------------
Usage: After installing, you will be able to run from anywhere on the command line simply with:

        hpgui
--------------------------------------------

Instructions: HP Data

The main UI you see upon starting is fairly self explanatory. A few notes:
- Output directory is not required. If left blank, the processsed data will be placed in the input directory/hp-output
- Initials and organization are required in Settings (you will not be able to process data unless you enter these)
- Local Camera ID is required, and is case-sensitive. If you enter an invalid ID and click "Run," you will be prompted to create a new camera (see below).
- It is STRONGLY recommended that on first run, you enter your browser & trello tokens in settings (see below). Just click the corresponding button in settings to log in and access this.
        - restart the program after entering your browser token to load the updated camera information.
- You can open any previously-processed hp data by going to File->Open HP Spreadsheet for editing.

After successfully running, the Spreadsheet editor will open.

--------------------------------------------
The Spreadsheet Editor:
The HP spreadsheet editor has many common spreadsheet editing controls. It will show the data itself, along with the image corresponding to the currently
selected cell. Ctrl-T (Edit->Fill True) and Ctrl-F (Edit->Fill False) can be used to auto-fill the current selection with True or False, respectively. Ctrl-D (Edit->Fill Down) will fill the selection with the first
cell selected.

Cells are several different colors:
-Yellow fields are mandatory. These must be entered. There are different mandatory fields for image, video, and audio files.
-Gray fields are disabled. This is typically because they already have data, and it shouldn't be changed.
-White fields can be entered if you have that information available.
-Red fields indicate a database mismatch error. This will generally appear if you specified a particular Camera ID, but our database has some different data than was found in your image.
    -Because some cameras can contain multiple exif entries, this may occasionally happen incorrectly. If it does, please contact your supervisor.

There are several tabs set with groups of related fields that are commonly edited together. Feel free to make use of them.

If the user chooses to enter keywords (click the Enter Keywords button on the main gui window), another spreadsheet will open, with only a few columns: the first being the image name, 
followed by 3 columns for keywords. The keywords are validated against a list, which can be found in hp_tool/data. This list should not be edited - contact an administrator to add a word.
Not every image needs all three keywords. More keyword columns can be added by clicking the "Add Column" button under "Edit" in the menu. 

From the spreadsheet window, you can upload your data to an S3 location directly. This can be accessed at File -> Export to S3...
To use this feature, you must have aws configured. On the command line, type

        aws configure

Receive your aws credentials from your supervisor.

--------------------------------------------
New Device Form
- You will be prompted to add a new device if you attempt to Run with an invalid camera ID. You can also manually add a new device via File -> Add a New Device.
- A form will open. It is STRONGLY recommended to attempt to pre-populate fields with the Select Image button near the top of the form. After that, fill out as much as you can.
- Fields marked with an asterisk (*) are mandatory. You will also be required to insert your Trello and Browser tokens.
- Clicking complete will check your responses, and then add the camera to the browser immediately and you'll be able to use it in processing. A trello card will also be posted with the new info.
- If you realize you made an error after the post is complete, just reach out to us on Trello.



--------------------------------------------
Instructions: PRNU Uploader
- To access, click on the "Export PRNU Data" tab on the main UI window
- The root directory should be named with the device local ID. See the HP Data/PRNU guide on Trello for more details on PRNU folder structure.
- Specify the root PRNU directory. If you are using a new camera and you haven't completed a form for it yet, check the "I'm using a new camera" box and you will go to the form.
- Click on the "Verify Directory Structure" to auto-check that everything is in the proper structure.
- If successfully verified, you will be able to click "Start Upload" and upload to the specified S3 directory.


If you have any questions, don't hesitate to reach out on Trello! There is also a more detailed guide (in pptx and pdf formats) there.

