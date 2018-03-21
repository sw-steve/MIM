import multiprocessing
import os
from ffmpy import FFmpeg


def process_single_file(f, return_list):
    out_file = f.split(".")[:-1]
    out_file.append("filtered.opus")
    out_file = ".".join(out_file)
    converter = FFmpeg(
        inputs={f: None},
        outputs={out_file: '-af "highpass=f=200, lowpass=f=3000, dynaudnorm"'}
    )

    converter.run()
    return_list.append(out_file)

def main():
    working_dir_listing = []
    # work_folder = os.getcwd()
    work_folder = "/run/user/1000/gvfs/smb-share:server=freenas,share=generalshare/Media/Audiobooks/Raw/convert/filter"
    manager = multiprocessing.Manager()
    return_list = manager.list()
    jobs = []

    for dir in os.listdir(work_folder):
        working_dir_listing.append(os.path.join(work_folder, dir))

    for dir in working_dir_listing:
        if os.path.isfile(dir) and dir.lower().endswith(".opus"):
            # out_file = process_single_file(dir)
            p = multiprocessing.Process(target=process_single_file, args=(dir, return_list))
            jobs.append(p)
            p.start()

    # Finalize parallel jobs
    for proc in jobs:
        proc.join()

    print("Finished")

if __name__ == "__main__":
    main()