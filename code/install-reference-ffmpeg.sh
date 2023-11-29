#!/bin/bash

set -e

mkdir -p ./ffmpeg_sources
mkdir -p ./ffmpeg_build
mkdir -p ./bin

base=$(pwd)

function die(){
	printf "$1\n"
	exit 1
}

if ! [ -f $base/bin/x264 ]; then
	rm -f $base/x264.log
    cd $base/ffmpeg_sources
	if [ -d ./x264 ]; then
		echo "x264 already downloaded"
	else
		printf "DOWNLOADING X264..."
		git clone https://code.videolan.org/videolan/x264.git x264 > $base/x264.log 2>&1 || die "Failed to download x264 - check x264.log"
		printf "DONE\n"
	fi
    cd x264
    git checkout 90a61ec76424778c050524f682a33f115024be96 >> $base/x264.log 2>&1 || die "Failed to checkout x264 correct commit - check x264.log"
    export PKG_CONFIG_PATH="$base/ffmpeg_build/lib/pkgconfig"
	printf "INSTALLING X264..."
    ./configure --prefix="$base/ffmpeg_build" --bindir="$base/bin" --enable-static >> $base/x264.log || die "Failed to configure x264 - check x264.log"
    make -j 8 >> $base/x264.log || die "Failed to compile x264 - check x264.log"
    make install >> $base/x264.log || die "Failed to install x264 - check x264.log"
	printf "DONE\n"
else
	echo "x264 already installed"
fi

if ! [ -f $base/bin/ffmpeg ]; then
	rm -f $base/ffmpeg.log
    cd $base/ffmpeg_sources
	if [ -d $base/ffmpeg_sources/ffmpeg ]; then
		echo "FFMPEG already downloaded"
	else
		printf "DOWNLOADING FFMPEG..."		
		git clone https://git.ffmpeg.org/ffmpeg.git ffmpeg > $base/ffmpeg.log 2>&1 || die "Failed to download ffmpeg - check ffmpeg.log"
		printf "DONE\n"
	fi
    cd ffmpeg
	git checkout 940b8908b94404a65f9f55e33efb4ccc6c81383c >> $base/ffmpeg.log 2>&1 || die "Failed to checkout ffmpeg correct commit - check ffmpeg.log"
	printf "INSTALLING FFMPEG..."
    PKG_CONFIG_PATH="$base/ffmpeg_build/lib/pkgconfig" ./configure --prefix="base/ffmpeg_build" --extra-cflags="-I$base/ffmpeg_build/include" --extra-ldflags="-L$base/ffmpeg_build/lib -ldl" --bindir="$base/bin" --pkg-config-flags="--static" --enable-gpl --enable-libx264 | tee /tmp/ffmpeg.configure >> $base/ffmpeg.log || die "Failed to configure ffmpeg - check ffmpeg.log"
    make -j 8 >> $base/ffmpeg.log 2>&1 || die "Failed to compile ffmpeg - check ffmpeg.log"
    make install >> $base/ffmpeg.log || die "Failed to install ffmpeg - check ffmpeg.log"
	printf "DONE\n"
else
	echo "FFmpeg already installed"
fi
