#!/bin/bash 

if [ -f maskgen/tool_set.py ]
then
   echo "You will be prompted for the your password to support sudo.  You must have sudo privilegs"
else
   echo "Run from the maskgen top level directory: ./scripts/install_mac.sh"
   exit 1
fi

VERSION=$((python --version) 2>&1)
check=".*2.7.1[123].*"
if [[ $VERSION =~ $check ]]
then
   echo "Python version $VERSION"
else
   echo "Unexpected python version $VERSION"
   exit 1
fi

which cc
if [ "$?" == "1" ]
then
   xcode-select --install
   echo "Some Items may not install if XCode is not installed" 
   echo "Restart once Xcode is installed"
   exit  0
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

which wget
if [ "$?" == "1" ]
then
   brew install wget
fi

brew install python --with-tcl-tk
pip install nose
pip install pyparsing
pip install pep8
brew install graphviz
brew install libraw
brew install homebrew/science/hdf5
brew tap homebrew/science
brew install matplotlib
brew install scipy
brew install ffmpeg --with-fdk-aac --with-sdl2 --with-freetype --with-libass --with-libvorbis --with-libvpx --with-opus --with-x265 --with-xvid --with-openh264
brew install homebew/science/opencv --with-ffmpeg --with-gstreamer --with-tbb --with-vtk --with-ximea --without-test --HEAD
brew install hdf5

wget http://www.sno.phy.queensu.ca/~phil/exiftool/ExifTool-10.50.dmg
hdiutil mount ExifTool-10.50.dmg
sudo installer -pkg /Volumes/ExifTool-10.50/ExifTool-10.50.pkg -target /

pip install tifffile
pip install graphviz
pip install pygraphviz
sudo pip install numpy --upgrade
pip install PyPDF2
pip install awscli
pip install boto
pip install boto3
pip install rawpy
pip install scikit-image
pip install awscli --force-reinstall --upgrade

#git clone https://github.com/rwgdrummer/maskgen.git
pip install setuptools
python setup.py sdist
pip install -e .

echo "Make sure your path variable includes /usr/local/bin"

