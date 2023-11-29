import argparse
import os
import re
import subprocess
from timeit import default_timer as timer

scenarios = ["live", "upload", "platform", "vod", "popular"]

def get_psnr(ffmpeg, transcode, reference):
    cmd = f"{ffmpeg} -i {reference} -i {transcode} -lavfi \"[0:v] setpts=PTS-STARTPTS[out0]; [1:v] setpts=PTS-STARTPTS[out1]; [out0][out1] psnr=log.txt\" -f null -"

    start = timer()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()

    m = re.search(b"average:([0-9]+\.[0-9]+)", err)

    # cleanup
    try:
        os.remove("log.txt")
    except:
        pass

    if m is None:
        m = re.search(b"average:(inf)", err)
        assert m is not None
        return 100.0
    else:
        return float(m.group(1))

def get_bitrate(ffprobe, transcode):
    ''' Returns bitrate (bit/s) '''
    cmd = [ffprobe, "-i", transcode]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    m = re.search(b"bitrate: ([0-9]+) kb/s", err)
    assert m is not None
    return int(m.group(1)) * 1000  # report in b/s

def get_video_stats(ffprobe, video):
    ''' Returns resolution (pixels/frame), and framerate (fps) of a video '''
    # run ffprobe
    cmd = [ffprobe, "-show_entries", "stream=width,height", video]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    # grep resolution
    width = re.search(b"width=([0-9]+)", out)
    assert width is not None, f"Problem in fetching video width with {ffprobe} on {video}"
    height = re.search(b"height=([0-9]+)", out)
    assert height is not None, f"Problem in fetching video height with {ffprobe} on {video}"
    resolution = int(width.group(1)) * int(height.group(1))

    # grep framerate
    frame = re.search(b"([0-9\.]+) fps", err)
    assert frame is not None, f"Problem in fetching framerate with {ffprobe} on {video}"
    framerate = float(frame.group(1))

    return resolution, framerate

def encode(ffmpeg, video, settings, output):
    ''' perform the transcode operation using ffmpeg '''
    cmd = [ffmpeg, "-i", video, "-c:v", "libx264", "-threads", str(1)] + settings + ["-y", output]
    start = timer()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    elapsed = timer() - start

    return elapsed

def encode_2pass(ffmpeg, video, settings, output_file):
    ''' perform two pass transcoding '''
    time_to_encode1 = encode(ffmpeg, video, ["-pass", str(1), "-f", "null", "-an", "-sn"] + settings, "/dev/null")
    time_to_encode2 = encode(ffmpeg, video, ["-pass", str(2)] + settings, output_file)

    return time_to_encode1 + time_to_encode2

if __name__ == "__main__":
    vbench_root = os.getenv("VBENCH_ROOT")
    assert vbench_root is not None and os.path.isdir(vbench_root), "Please set VBENCH_ROOT env variable"

    ###############################################
    # parse arguments
    ###############################################
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", type=str, help="Transcoding scenario")
    parser.add_argument("--output_dir", type=str, default="/tmp", help="Where to save transcoded videos")
    parser.add_argument("--ffmpeg_dir", type=str, default=os.path.join(vbench_root, "code/bin"),
                        help="Path to ffmpeg installation folder")

    args = parser.parse_args()

    ###############################################
    # check arguments
    ###############################################
    assert args.scenario in scenarios, \
        f"args.scenario should be chosen in this list of supported scenarios: {scenarios}"

    if args.scenario == "upload":
        video_dir = os.path.join(os.getenv("VBENCH_ROOT"), "videos/crf0")
    else:
        video_dir = os.path.join(os.getenv("VBENCH_ROOT"), "videos/crf18")

    ffmpeg = os.path.join(args.ffmpeg_dir, "ffmpeg")
    ffprobe = os.path.join(args.ffmpeg_dir, "ffprobe")
    assert os.path.isfile(ffmpeg) and os.access(ffmpeg, os.X_OK), \
        f"Cannot find a ffmpeg executable in args.ffmpeg_dir: {args.ffmpeg_dir}"
    assert os.path.isfile(ffprobe) and os.access(ffprobe, os.X_OK), \
        f"Cannot find a ffprobe executable in args.ffmpeg_dir: {args.ffmpeg_dir}"

    assert os.path.isdir(video_dir) and os.access(video_dir, os.R_OK) and os.access(video_dir, os.X_OK), \
        f"video_dir: {video_dir} is not a valid video directory"
    assert os.path.isdir(args.output_dir) and os.access(args.output_dir, os.W_OK), \
        f"Output directory {args.output_dir} is non-writable"
    assert os.path.abspath(video_dir) != os.path.abspath(args.output_dir), \
        "Output and video input directory cannot be the same"

    input_files = [x for x in os.listdir(video_dir) if
                   re.search("mkv$", x) or re.search("y4m$", x) or re.search("mp4$", x)]

    assert len(input_files) > 0, f"Cannot find valid video files in args.video_dir: {args.video_dir}"

    ###############################################
    # perform transcoding
    ###############################################

    print("# video_name, transcoding time, psnr compared to original, transcode bitrate")
    for v_name in input_files:
        video = os.path.join(video_dir, v_name)

        # output file path
        output_video = os.path.join(args.output_dir, v_name)

        if args.scenario == "upload":
            settings = ["-crf", "18"]
            elapsed = encode(ffmpeg, video, settings, output_video)
        else:
            # get stats of the video and use to compute target_bitrate
            resolution, framerate = get_video_stats(ffprobe, video)

            # fixed number of bits per pixel as target bitrate
            if framerate > 30:
                target_bitrate = 3 * resolution
            else:
                target_bitrate = 2 * resolution

            bitrate = get_bitrate(ffprobe, video)
            # adjust for a minimum level of compression
            target_bitrate = bitrate / 2 if target_bitrate > bitrate / 2 else target_bitrate

            settings = ["-b:v", str(target_bitrate)]
            if args.scenario == "live":
                # adjust effort level depending on the video resolution
                if (resolution / 1000) > 4000:
                    settings += ["-preset", "ultrafast", "-tune", "zerolatency"]
                elif (resolution / 1000) > 1000:
                    settings += ["-preset", "superfast", "-tune", "zerolatency"]
                else:
                    settings += ["-preset", "veryfast", "-tune", "zerolatency"]

                elapsed = encode(ffmpeg, video, settings, output_video)
            elif args.scenario in ["vod", "platform"]:
                settings += ["-preset", "medium"]
                elapsed = encode_2pass(ffmpeg, video, settings, output_video)
            elif args.scenario == "popular":
                settings += ["-preset", "veryslow"]
                elapsed = encode_2pass(ffmpeg, video, settings, output_video)
            else:
                raise NotImplementedError

        # get PSNR and bitrate of the resulting transcode
        psnr = get_psnr(ffmpeg, output_video, video)
        transcode_bitrate = get_bitrate(ffprobe, output_video)

        print(f"{v_name},{elapsed},{psnr},{transcode_bitrate}")

    # cleanup
    try:
        os.remove("ffmpeg2pass-0.log")
        os.remove("ffmpeg2pass-0.log.mbtree")
    except:
        pass

