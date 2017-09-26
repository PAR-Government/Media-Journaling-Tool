sudo apt-get update && apt-get install -y \
	autoconf \
	automake \
	build-essential \
	checkinstall \
	cmake \
	git \
	graphviz \
	graphviz-dev \
	libass-dev  \
	libavcodec-dev \
	libavformat-dev \
	libbz2-dev \
	libblas-dev \
	libc6-dev \
	libdc1394-22-dev \
	libgdbm-dev \
	libgstreamer0.10-dev \
	libgstreamer-plugins-base0.10-dev  \
	libgtk2.0-dev \
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
	libopencv-dev \
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
	libswscale-dev \
	libtbb-dev \
	libtheora-dev \
	libtiff5-dev \
	libtool \
	libva-dev \
	libvpx-dev \
	libvdpau-dev \
	libvorbis-dev \
	libv4l-dev \
	libxcb1-dev \
	libxcb-shm0-dev \
	libxcb-xfixes0-dev \
        libx265-dev \
	libxine2 \
	libxvidcore-dev \
	libx264-dev \
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
	x264 \
	yasm \
	zip \
	zlib1g-dev
	
mkdir workdir
mkdir ffmpeg_sources
ffmpeg_sources
#hg clone https://bitbucket.org/multicoreware/x265
#cd x265/build/linux
#cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="/usr/local" -DENABLE_SHARED:bool=off ../../source && make
#sudo make install 

cd ../..
wget http://storage.googleapis.com/downloads.webmproject.org/releases/webm/libvpx-1.6.0.tar.bz2 && tar xjvf libvpx-1.6.0.tar.bz2
cd ./libvpx-1.6.0
./configure --prefix="/usr/local" --disable-examples --disable-unit-tests && make 
sudo make install &&  make clean

cd ..
wget http://ffmpeg.org/releases/ffmpeg-3.2.8.tar.bz2  && tar xjvf ffmpeg-3.2.8.tar.bz2 
cd ffmpeg
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
export CFLAGS=-fPIC
./configure \
  --prefix="/usr/local" \
  --pkg-config-flags="--static" \
  --extra-cflags="-I/usr/local/include" \
  --pkgconfigdir="/usr/local/lib/pkgconfig" \
  --extra-ldflags="-L/usr/local/lib" \
  --bindir="/usr/local/bin/bin" \
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
  --enable-nonfree
make 
sudo make install
make clean
hash -r

cd ..
# download opencv-2.4.13
wget http://downloads.sourceforge.net/project/opencvlibrary/opencv-unix/2.4.13/opencv-2.4.13.zip && unzip opencv-2.4.13.zip
cd opencv-2.4.13
mkdir release
cd release
cmake -G "Unix Makefiles" -DCMAKE_CXX_COMPILER=/usr/bin/g++ CMAKE_C_COMPILER=/usr/bin/gcc -DCMAKE_BUILD_TYPE=RELEASE -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_FFMPEG=ON -DWITH_TBB=ON -DBUILD_PYTHON_SUPPORT=ON -DWITH_V4L=ON -DINSTALL_C_EXAMPLES=ON -DINSTALL_PYTHON_EXAMPLES=ON -DBUILD_EXAMPLES=ON -DWITH_QT=ON -DWITH_OPENGL=ON -DBUILD_FAT_JAVA_LIB=ON -DINSTALL_TO_MANGLED_PATHS=ON -DINSTALL_CREATE_DISTRIB=ON -DINSTALL_TESTS=ON -DENABLE_FAST_MATH=ON -DWITH_IMAGEIO=ON -DBUILD_SHARED_LIBS=OFF -DPYTHON_NUMPY_INCLUDE_DIR=/usr/local/lib/python2.7/dist-packages/numpy/core/include  -DWITH_GSTREAMER=ON .. && make all -j2 
sudo make install 
/bin/bash -c 'echo "/usr/local/lib" > /etc/ld.so.conf.d/opencv.conf'
ldconfig
cd ../..

sudo pip install --upgrade pip
sudo pip install rawpy graphviz 
sudo pip install numpy --upgrade
sudo pip install PyPDF2 setuptools 

git clone https://github.com/rwgdrummer/maskgen.git
cd maskgen/setuptools-version
python setup.py sdist
sudo pip install -e .
cd ..
python setup.py sdist
sudo pip install -e .
cd ..
