import argparse
import os

legend = {"live":"live score",
          "upload": "upload score",
          "platform": "platform score",
          "vod": "vod score",
          "popular":"popular_score"}

def parse_data(dataset):
    ''' Parse the transcoding results

    Args:
        dataset: filename of the dataset to parse

    Returns:
    	dictionary [file_name] -> [ (time_to_encode, PSNR, transcode bitrate)]
    '''
    data = {}
    with open(dataset) as file:
        for line in file:
            if line[0] == "#":
                continue
            row = line.strip().split(',')
            assert len(row) == 4
            try:
                data[row[0]] = [float(x) for x in row[1:]]
            except:
                print "Problem parsing line: {}".format(line)
                raise

    return data

if __name__=="__main__":
    ###############################################
    # parse arguments
    ###############################################

    parser = argparse.ArgumentParser()
    parser.add_argument("data",type=str, help="Datasets - dataset 0 is the reference point")
    parser.add_argument("scenario", type=str, help="Transcoding scenario")
    args = parser.parse_args()

    ###############################################
    # check arguments
    ###############################################

    assert os.path.isfile(args.data), "Please provide a valid file path for your data"
    assert args.scenario in legend, "{} is not a valid scenario name. Valid scenario names are {}".format(args.scenario, legend.keys())
    vbench_root = os.getenv("VBENCH_ROOT")
    assert vbench_root is not None and os.path.isdir(vbench_root), "Please set VBENCH_ROOT env variable"
    reference_file = os.path.join(vbench_root,"code/reference/{}.csv".format(args.scenario))
    assert os.path.isfile(reference_file), "Can't find reference measurements file {}".format(reference_file)

    reference_data = parse_data(reference_file)
    new_data       = parse_data(args.data)

    print "#video, psnr_ratio, bitrate_ratio, speed_ratio, " + legend[args.scenario]

    ###############################################
    # perform comparison
    ###############################################

    for vname,ref in reference_data.items():
        if vname in new_data:
            new = new_data[vname]
            ref_time, ref_psnr, ref_bitrate = ref
            new_time, new_psnr, new_bitrate = new

            psnr_ratio    = new_psnr/ref_psnr
            speed_ratio   = ref_time/new_time
            bitrate_ratio = ref_bitrate/new_bitrate

            # check quality limit as it does not make sense to improve quality over a certain point
            if new_psnr > 50 and psnr_ratio < 1:
                psnr_ratio = 1.0

            score = 0
            # check conditions for the scenario selected
            # and output a score if condition is satisfied
            if args.scenario == "live" and new_time <= 5:
                score = bitrate_ratio * psnr_ratio
            elif args.scenario == "platform" and bitrate_ratio >= 0.995 and psnr_ratio >= 0.995: # account for very small variations in FFmpeg results
                score = speed_ratio
            elif args.scenario == "upload" and bitrate_ratio >= 0.2:
                score = speed_ratio * psnr_ratio
            elif args.scenario == "popular" and speed_ratio >= 0.1 and bitrate_ratio >= 1 and psnr_ratio >= 1:
                score = bitrate_ratio * psnr_ratio
            elif args.scenario == "vod" and psnr_ratio >= 1:
                score = bitrate_ratio*speed_ratio
            print "{},{},{},{},{}".format( vname, psnr_ratio, bitrate_ratio, speed_ratio, score)
