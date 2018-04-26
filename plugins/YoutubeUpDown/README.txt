README - YouTube_UpDown
 Developed by National Center for Media Forensics
 University of Colorado Denver
 youtube_updown.py v.6 9/23/2017

REQUIREMENTS:
- Python 2.x
- Tested on Mac 0SX 10.12, Linux Ubuntu 16.4, Windows 10
- Registered Google account
- youtube-dl installed.  Available from youtube-dl.org or if Python pip is installed (recommended) execute the following:
% pip install youtube-dl

- install Google APIs Client Library for Python
% pip install --upgrade google-api-python-client

- properly set-up client_secrets.json file in maskgen\resources (See below for setup instructions)
- youtube-oauth2.json file in maskgen\resources (generated upon completing authorization 1st time plugin is run)

Enable YouTube API by visiting 
	- https://console.developers.google.com/
	- https://console.developers.google.com/apis/api/youtube.googleapis.com

SETTING UP client_secrets.json FILE
To set up this file, perform the following steps:

1. navigate to https://console.developers.google.com/ (log in if necessary)
2. select your project from the dropdown next to the Google APIs logo or create a new one.  A description of this file, and other google requirements, are described here: https://developers.google.com/youtube/v3/guides/uploading_a_video
3. from within the project click credentials from the left sidebar menu. Additional instructions here: https://developers.google.com/youtube/registering_an_application
4. click on the project name in the Oauth 2.0 Client IDs section
5. click "Download JSON" tab at the top of the page.  Rename file to simply "client_secrets.json" and place in maskgen/resources.

Upon the first use of the plugin, the default browser will open a prompt for log-in/authorization- the resulting oauth token will be kept in maskgen/resources.