#!/bin/bash 

if [ -f maskgen/tool_set.py ]
then
   echo "You will be prompted for the your password to support sudo.  You must have sudo privilegs"
else
   echo "Run from the maskgen top level directory: ./scripts/install_mac.sh"
   exit 1
fi

VERSION=$((python --version) 2>&1)
check=".*2.7.1[234].*"
if [[ $VERSION =~ $check ]]
then
   echo "Python version $VERSION"
else
   echo "Unexpected python version $VERSION. Installing upgrade."
   brew install readline sqlite gdbm
   brew install python
fi

VERSION=$((python --version) 2>&1)
check=".*2.7.1[234].*"
if [[ ! $VERSION =~ $check ]]
then
   echo "Uncorrected python version $VERSION.  Check for an older python in your search PATH.  Mac OS places an older python in /usr/bin."
   exit 1
fi

piploc=`which pip`
pythonloc=`which python`
if [ "${piploc%/*/*}" != "${pythonloc%/*/*}" ]
then
  echo "pip does match the installed python"
  exit 1
fi

easyloc=`which easy_install`
if [ "${easyloc%/*/*}" != "${pythonloc%/*/*}" ]
then
  echo "easy_install does match the installed python. Trying to correct."
  pip install --upgrade setuptools pip
fi

easyloc=`which easy_install`
if [ "${easyloc%/*/*}" != "${pythonloc%/*/*}" ]
then
  echo "easy_install does match the installed python"
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
export PATH=/usr/local/bin:$PATH
pip install nose
pip install pyparsing
pip install pep8
brew install graphviz
brew install libraw
brew install homebrew/science/hdf5
brew tap homebrew/science
brew install matplotlib
brew install scipy
cd /usr/local/Homebrew/Library/Taps/homebrew/homebrew-core
git -C "$(brew --repo homebrew/core)" fetch --unshallow
brew unlink ffmpeg
git checkout e1b6557c45bdbf85060f35c3ed8e34e3d1b0248 Formula/ffmpeg.rb 
brew install ffmpeg --with-fdk-aac --with-sdl2 --with-freetype --with-libass --with-libvorbis --with-libvpx --with-opus --with-x265 --with-xvid --with-openh264
brew install opencv --with-ffmpeg --with-gstreamer --with-tbb --with-vtk --with-ximea --without-test --with-contrib
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
cd setuptools-version
python setup.py sdist
pip install -e .
cd ..
python setup.py sdist
pip install -e .
cd wrapper_plugins/rawphoto_wrapper
python setup.py sdist
pip install -e .

echo "Make sure your path variable includes /usr/local/bin prior to /usr/bin"

