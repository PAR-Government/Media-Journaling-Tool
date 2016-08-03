Dependencies:
pip install pillow
pip install numpy
pyexiv2 (download and install from http://tilloy.net/dev/pyexiv2/download.html)

Run:
python jpegEasy.py <image_file> <camera_keywords_separated_by_underscores> --thumb <thumbnail_file>

ex.
python jpegEasy.py _DSC204.tiff Canon_5D_mark_III --thumb thumbnail.png



Converts an image to jpeg format using a custom quantization table found in QuantizationTables directory.

If user includes the optional --thumb argument, adds 128x128 (max, maintains aspect ratio) thumbnail to header based on specified thumbnail image file. 
Thumbnail can be built on custom thumbnail quantization tables. (if quantization table for image is named my_table.txt, 
name thumbnail table my_table_thumbnail.txt). If no thumbnail table found, it will just use the same table as the image.)


Custom quantization tables can be added via text file in 16 rows, 8 cols (Luminance table "stacked" on top of chrominance table)
ex.
1	 1	 1	 1	 1	 2	 3	 3
1	 1	 1	 1	 1	 3	 3	 3
1	 1	 1	 1	 2	 3	 4	 3
1	 1	 1	 1	 3	 5	 5	 3
1	 1	 2	 3	 4	 6	 6	 4
1	 2	 3	 4	 5	 6	 7	 5
3	 4	 4	 5	 6	 7	 7	 6
4	 5	 6	 6	 7	 6	 6	 6
1	 1	 1	 2	 6	 6	 6	 6
1	 1	 1	 4	 6	 6	 6	 6
1	 1	 3	 6	 6	 6	 6	 6
2	 4	 6	 6	 6	 6	 6	 6
6	 6	 6	 6	 6	 6	 6	 6
6	 6	 6	 6	 6	 6	 6	 6
6	 6	 6	 6	 6	 6	 6	 6
6	 6	 6	 6	 6	 6	 6	 6