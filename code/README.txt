# vbench

vbench is a benchmark for the growing video as a service
workload. vbench was presented at ASPLOS 2018, and the full paper can
be found at https://dl.acm.org/citation.cfm?id=3173207.  Please cite
this summary paper when publishing results using vbench.

## Stay updated

You can find the latest project updates at vbench.net and on the
mailing list at https://lists.cs.columbia.edu/mailman/listinfo/vbench

## Usage

The scripts contained here allow the user to (1) run reference
transcode pipelines, and (2) compare an alternate transcoder to the
reference for a transcoding scenario (e.g., live streaming).

### Setting up the environment

First set the VBENCH_ROOT environment variable to point to the base
vbench folder (the folder containing the code and videos folders):

    export VBENCH_ROOT=$(pwd)

### Computing a vbench score

To compare a transcoder to the vbench reference, one must provide the
data in the same csv structure as the reference data, with each line
reporting the transcoding time, PSNR, and bitrate of the transcoded
video:

    # video_name, transcoding time, psnr compared to original, transcode bitrate
    bike_1280x720_29.mkv,2.41728210449,43.253833,368000
    cat_854x480_29.mkv,3.03347206116,40.51266,836000
    ...

To compare and score this data relative to the reference, invoke the
compare.py script:

	python code/compare.py <path to the csv containing your results> <scenario = vod, popular, upload, live, platform>

For each video, this script will report "speedups" relative to the
scenario reference in each dimension (time, PSNR, and bitrate) as well
as the overall scenario score.  If the scenario constraints are not
met, the reported score for that video will be zero.

### Computing platform scores

The platform scenario isolates hardware improvements.  For such
experiments, one must run precisely the same software used in the reference
measurements.  We have provided a script to install the specific commits of
FFmpeg and x264 in a local subfolder (./bin):

    ./code/install-reference-ffmpeg.sh

This script will take a few minutes to complete and has some
dependencies which must be installed beforehand:

    # CentOs
    yum install autoconf automake bzip2 cmake freetype-devel gcc gcc-c++ git libtool make nasm pkgconfig zlib-devel yasm
    # Ubuntu
    apt-get update -qq && apt-get -y install autoconf automake build-essential cmake git libass-dev libtool pkg-config texinfo wget zlib1g-dev yasm

Alternately, one can follow the guide from which the script has been derived:
https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu.  The provided
installation script has been tested with Ubuntu 16.04, CentOs 7 and MacOS 10.

To run any of the reference transcode pipelines, invoke the reference.py script:

   python code/reference.py <scenario = vod, upload, platform, and popular>

This script will report runtime, PSNR, and bitrate to stdout in the usual csv format.

WARNING: Do not overwrite or modify the files in the provided reference
directory.  Those files contain measurements from the reference machine and are
needed by compare.py to produce vbench scores.

## Additional components

The FFmpeg installation guide at
https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu contain
additional information on how to add support for x265 and libvpx-vp9
which were used in some experiments in the paper.  Similarly,
https://trac.ffmpeg.org/wiki/HWAccelIntro will contain the latest
instructions to add support for the Nvidia NVENC and Intel QSV
hardware encoders, also used in the paper experiments.
