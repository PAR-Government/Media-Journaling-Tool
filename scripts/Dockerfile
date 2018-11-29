FROM ubuntu:16.04

RUN apt-get update && apt-get install -y \
	autoconf \
	automake \
	build-essential \
	checkinstall \
	curl \
	cmake \
	g++ \
	git \
	git-core \
	bzip2 \
	libass-dev  \
	libbz2-dev \
	libblas-dev \
	libc6-dev \
	libgdbm-dev \
	libgstreamer0.10-dev \
	libgstreamer-plugins-base0.10-dev  \
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
	libfaac-dev \
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
	unzip \
	zlib1g-dev  \
	yasm \ 
  	libgpac-dev

CMD mkdir workdir
WORKDIR workdir

RUN wget https://www.nasm.us/pub/nasm/releasebuilds/2.13.03/nasm-2.13.03.tar.bz2
RUN tar xf nasm-2.13.03.tar.bz2
WORKDIR nasm-2.13.03 
RUN ./autogen.sh
RUN ./configure --prefix="/usr/local" --bindir="/usr/local/bin"
RUN make 
RUN make install
WORKDIR ..

RUN git -C x264 pull 2> /dev/null || git clone --depth 1 https://git.videolan.org/git/x264 
WORKDIR x264 
ENV PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
RUN ./configure --prefix="/usr/local" --bindir="/usr/local/bin" --enable-static --enable-pic
RUN make 
RUN make install
WORKDIR ..

RUN hg clone https://bitbucket.org/multicoreware/x265
WORKDIR x265/build/linux 
RUN cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="/usr/local" -DENABLE_SHARED=off ../../source
RUN make
RUN make install
WORKDIR ../../..

RUN git clone --depth 1 https://chromium.googlesource.com/webm/libvpx.git
WORKDIR libvpx
RUN CFLAGS=-fPIC ./configure --prefix="/usr/local" --disable-examples --disable-unit-tests --enable-vp9-highbitdepth --as=yasm 
RUN make
RUN make install
WORKDIR ..

RUN  wget http://ffmpeg.org/releases/ffmpeg-3.4.2.tar.bz2  && tar xjvf ffmpeg-3.4.2.tar.bz2 
WORKDIR ffmpeg-3.4.2
ENV PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
RUN CFLAGS=-fPIC ./configure \
  --prefix=/usr/local \
  --extra-cflags=-I/usr/local/include \
  --pkgconfigdir=/usr/local/lib/pkgconfig \
  --extra-ldflags=-L/usr/local/lib \
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
  --enable-shared \
  --enable-nonfree
RUN make 
RUN make install && make clean && hash -r
WORKDIR ..

#RUN rm lib/python2.7/lib-dynload/cv2.so
RUN  wget http://downloads.sourceforge.net/project/opencvlibrary/opencv-unix/3.4.1/opencv-3.4.1.zip && unzip opencv-3.4.1.zip
RUN  wget -O opencv_contrib.zip https://github.com/opencv/opencv_contrib/archive/3.4.1.zip && unzip opencv_contrib.zip
WORKDIR opencv-3.4.1
CMD  mkdir release
WORKDIR release
RUN  cmake -G "Unix Makefiles" -DCMAKE_CXX_COMPILER=/usr/bin/g++ CMAKE_C_COMPILER=/usr/bin/gcc -DCMAKE_BUILD_TYPE=RELEASE -DCMAKE_INSTALL_PREFIX=/usr/local -DWITH_FFMPEG=ON -DWITH_TBB=ON -DBUILD_PYTHON_SUPPORT=ON -DWITH_V4L=ON -DINSTALL_C_EXAMPLES=ON -DINSTALL_PYTHON_EXAMPLES=ON -DBUILD_EXAMPLES=ON -DWITH_QT=ON -DWITH_OPENGL=ON -DBUILD_FAT_JAVA_LIB=ON -DINSTALL_TO_MANGLED_PATHS=ON -DINSTALL_CREATE_DISTRIB=ON -DINSTALL_TESTS=ON -DENABLE_FAST_MATH=ON -DWITH_IMAGEIO=ON -DBUILD_SHARED_LIBS=OFF -DPYTHON_NUMPY_INCLUDE_DIR=/usr/local/lib/python2.7/dist-packages/numpy/core/include  -DWITH_GSTREAMER=OFF -DOPENCV_EXTRA_MODULES_PATH=../../opencv_contrib-3.4.1/modules -DOpenCV_SHARED=ON -DBUILD_WITH_DYNAMIC_IPP=OFF -DWITH_IPP=OFF .. && make all -j2 
RUN make install 
RUN /bin/bash -c 'echo "/usr/local/lib" > /etc/ld.so.conf.d/opencv.conf'
RUN ldconfig
WORKDIR ../..

RUN cp /usr/local/python/2.7/cv2.so /usr/local/lib/python2.7/dist-packages/

RUN apt-get install -y libgtk2.0-dev  \
        graphviz \
        graphviz-dev 

RUN pip install --upgrade pip
RUN pip install rawpy graphviz 
RUN pip install numpy --upgrade
RUN pip install PyPDF2 setuptools 
RUN pip install boto3==1.7.16 
RUN pip install awscli==1.15.16
RUN pip install httplib2
RUN pip install numba

RUN git clone https://github.com/rwgdrummer/maskgen.git
WORKDIR maskgen/setuptools-version
RUN python setup.py sdist
RUN pip install -e .
RUN pip install --upgrade awscli
WORKDIR ..
RUN python setup.py sdist
RUN pip install -e .
WORKDIR ../../wrapper_plugins/jpeg2000_wrapper
RUN python setup.py sdist
RUN pip install -e .
WORKDIR ../../..

CMD ["bash"]
