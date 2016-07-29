add_meta.py

Changes specified metadata tag to user input if allowed

dependencies:
pyexiv2: http://tilloy.net/dev/pyexiv2/download.html

run on command line using:
python add_meta.py <ImageFile> --tags <tag1> "new value" <tag2> "new value"...<tagN> "new value"
(no <>, but quotes are required if multiple words in new value)

ex.
python add_meta.py lenna.jpg --tags Exif.Image.Artist> "Bugs Bunny" Iptc.Envelope.ModelVersion "2"

NOTE:
tags must be spelled exactly according to Exiv2 documentation (http://exiv2.org/metadata.html)

TODO:
Iptc date & time type tags currently unsupported (need to figure out what format they actually need)
Exif rational type tags result in unexpected values, possibly due to pyexiv2 API