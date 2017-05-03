#!/bin/bash 

echo "You will be prompted for the your password to support sudo.  You must have sudo privilegs"

which gcc
if [ "$?" == "1" ]
then
   echo "Some Items may not install if XCode is not installed"
fi

which brew
if [ "$?" == "1" ]
then
   /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
fi
brew update
which git
if [ "$?" == "1" ]
then
   brew install git
   brew link git
fi
brew install python --with-tcl-tk
brew install graphviz
brew install libraw
brew install homebrew/science/hdf5
brew install ffmpeg --with-fdk-aac --with-ffplay --with-freetype --with-libass --with-libquvi --with-libvorbis --with-libvpx --with-opus --with-x265 --with-x264 --with-gpl --with-xvid --with-libmp3lame
brew tap homebrew/science
brew install opencv --universal --with-ffmpeg --with-gstreamer --with-jasper --with-java --with-libdc1394 --with-opengl --with-openni --with-tbb --with-vtk --with-ximea --without-eigen --without-numpy --without-opencl --without-openexr --without-python --without-test --HEAD
brew install hdf5

wget http://www.sno.phy.queensu.ca/~phil/exiftool/ExifTool-10.50.dmg
hdiutil mount ExifTool-10.50.dmg
sudo installer -pkg /Volumes/ExifTool-10.50/ExifTool-10.50.pkg -target /

pip install tifffile
pip install graphviz
sudo pip install numpy --upgrade
pip install PyPDF2

git clone https://github.com/rwgdrummer/maskgen.git
pip install setuptools
cd maskgen
sudo python setup.py install

echo "Make sure your path variable includes /usr/local/bin"

