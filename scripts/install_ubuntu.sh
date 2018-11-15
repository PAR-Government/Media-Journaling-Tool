#!/bin/bash

sudo apt-get update 
sudo apt-get install -y \
	autoconf \
	automake \
	build-essential \
	checkinstall \
	cmake \
	curl \
	g++ \
	git \
	git-core \
	bzip2 \
	libass-dev  \
	libbz2-dev \
	libblas-dev \
	libc6-dev \
	libgdbm-dev \
	libgstreamer1.0-dev \
	libgstreamer-plugins-base1.0-dev  \
	libgphoto2-dev \
	libhdf5-serial-dev \
	libimage-exiftool-perl \
	libfdk-aac-dev \
	libfreetype6-dev \
	libjasper-dev \
	libjpeg-dev \
	liblapack-dev \
	libmp3lame-dev \
	libopencore-amrnb-dev \
	libopencore-amrwb-dev \
	libopus-dev \
	libncursesw5-dev \
	libnuma-dev \
	libpng12-dev \
	libqt4-dev \
	libraw-dev \
	libreadline-gplv2-dev \
	libsdl1.2-dev \
	libssl-dev \
	libsqlite3-dev \
	libtbb-dev \
	libtheora-dev \
	libtiff5-dev \
	libtool \
	libva-dev \
	libvdpau-dev \
	libvorbis-dev \
	libv4l-dev \
	libxcb1-dev \
	libxcb-shm0-dev \
	libxcb-xfixes0-dev \
	libxvidcore-dev \
	make \
	mercurial \
	pkg-config \
	python \
	python-numpy \
	python-dev \
	python-tk \
	python-pip \
	texinfo \
	tk-dev \
	v4l-utils \
	wget \
	yasm \
	unzip \
	zlib1g-dev \
	libgpac-dev


mkdir workdir
cd workdir

wget https://www.nasm.us/pub/nasm/releasebuilds/2.13.03/nasm-2.13.03.tar.bz2
tar xf nasm-2.13.03.tar.bz2
cd nasm-2.13.03
./autogen.sh
./configure --prefix="/usr/local" --bindir="/usr/local/bin"
make
sudo make install
cd ..

git -C x264 pull 2> /dev/null || git clone --depth 1 https://git.videolan.org/git/x264
cd x264
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
./configure --prefix="/usr/local" --bindir="/usr/local/bin" --enable-static --enable-pic
make
sudo make install
cd ..

hg clone https://bitbucket.org/multicoreware/x265
cd x265/build/linux
cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="/usr/local" -DENABLE_SHARED=off ../../source
make
sudo make install
cd ../../..

git clone --depth 1 https://chromium.googlesource.com/webm/libvpx.git
cd libvpx
CFLAGS=-fPIC ./configure --prefix="/usr/local" --disable-examples --disable-unit-tests --enable-vp9-highbitdepth --as=yasm
make
sudo make install

which ffmpeg
if [ $? -ne 0 ]; then
  wget http://ffmpeg.org/releases/ffmpeg-3.4.2.tar.bz2  && tar xjvf ffmpeg-3.4.2.tar.bz2 
  cd ffmpeg-3.4.2
  export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
  export CFLAGS=-fPIC
  ./configure \
  --prefix="/usr/local" \
  --extra-cflags="-I/usr/local/include" \
  --pkgconfigdir="/usr/local/lib/pkgconfig" \
  --extra-ldflags="-L/usr/local/lib" \
  --pkg-config-flags="--static" \
  --enable-gpl \
  --enable-libass \
  --enable-libfdk-aac \
  --enable-libfreetype \
  --enable-libmp3lame \
  --enable-libopus \
  --enable-libtheora \
  --enable-libvorbis \
  --enable-libvpx \
  --enable-libx264 \
  --enable-libx265 \
  --enable-nonfree \
  --enable-shared \
  --enable-avresample 
  make 
  sudo make install
  make clean
  hash -r
  cd ..
fi

CV2V=`python -c 'import cv2; print cv2.__version__[0]'`

if [ $CV2V != '3' ]; then
# download opencv-3.4.1
  wget http://downloads.sourceforge.net/project/opencvlibrary/opencv-unix/3.4.1/opencv-3.4.1.zip && unzip opencv-3.4.1.zip
  wget -O opencv_contrib.zip https://github.com/opencv/opencv_contrib/archive/3.4.1.zip && unzip opencv_contrib.zip
  cd opencv-3.4.1
  mkdir release
  cd release
  cmake -G "Unix Makefiles" -DCMAKE_CXX_COMPILER=/usr/bin/g++ CMAKE_C_COMPILER=/usr/bin/gcc -DCMAKE_BUILD_TYPE=RELEASE -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_FFMPEG=ON -DWITH_TBB=ON -DBUILD_PYTHON_SUPPORT=ON -DWITH_V4L=ON -DINSTALL_C_EXAMPLES=ON -DINSTALL_PYTHON_EXAMPLES=ON -DBUILD_EXAMPLES=ON -DWITH_QT=ON -DWITH_OPENGL=ON -DBUILD_FAT_JAVA_LIB=ON -DINSTALL_TO_MANGLED_PATHS=ON -DINSTALL_CREATE_DISTRIB=ON -DINSTALL_TESTS=ON -DENABLE_FAST_MATH=ON -DWITH_IMAGEIO=ON -DBUILD_SHARED_LIBS=OFF -DPYTHON_NUMPY_INCLUDE_DIR=/usr/local/lib/python2.7/dist-packages/numpy/core/include  -DWITH_GSTREAMER=OFF -DOPENCV_EXTRA_MODULES_PATH=../../opencv_contrib-3.4.1/modules -DOpenCV_SHARED=ON -DBUILD_WITH_DYNAMIC_IPP=OFF -DWITH_IPP=OFF .. && make all -j2
  sudo make install 
  sudo /bin/bash -c 'echo "/usr/local/lib" > /etc/ld.so.conf.d/opencv.conf'
  sudo ldconfig
  cd ../..
  sudo cp /usr/local/python/2.7/cv2.so /usr/local/lib/python2.7/dist-packages/
fi

sudo apt-get install -y libgtk2.0-dev graphviz graphviz-dev

sudo pip install --upgrade pip
sudo pip install rawpy graphviz 
sudo pip install numpy --upgrade
sudo pip install PyPDF2 setuptools 
sudo pip install shapely
sudo pip install boto3==1.7.16
sudo pip install awscli==1.15.16
sudo pip install httplib2
sudo pip install numba

if [ -f "maskgen" ]; then
  git pull
  git checkout master
else
  git clone https://github.com/rwgdrummer/maskgen.git
  cd maskgen
fi

cd setuptools-version
python setup.py sdist
sudo pip install -e .
sudo pip install --upgrade awscli
cd ..
python setup.py sdist
sudo pip install -e .
cd ./wrapper_plugins/jpeg2000_wrapper
python setup.py sdist
sudo pip install -e .
cd ../../..
