
import os
import shutil
import traceback
import re
from difflib import SequenceMatcher as sm
import tempfile
from ffmpy import FFmpeg
import multiprocessing

EXTENSIONS = (".flac", ".mp3", ".m4a", ".opus")


def copy_recursive(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def sort(in_list):
    # Detect variable numbering
    # ends_w_single_digit = re.compile("^.*\\d$")

    # Check for ends with digit
    single_digit = False
    double_digit = False
    # for item in in_list:
    #     if item.endswith(".opus"):
    #         if item[-6].isdigit():
    #             single_digit = True
    #         if item[-7:-5].isdigit():
    #             double_digit = True
    #         if single_digit and double_digit:
    #             return in_list.sort(key=lambda numb: int(re.split('_|-', numb)[-6]))
    #     else:
    #         if item[-1].isdigit():
    #             single_digit = True
    #         if item[-2:].isdigit():
    #             double_digit = True
    #         if single_digit and double_digit:
    #             return in_list.sort(key=lambda numb: int(re.split('_|-', numb)[-1]))

    # I've tried everything
    return sorted(in_list)




def similar(a, b):
    return sm(None, a, b).ratio()


def build_full_path_from_list(root, files):
    out_list = []
    for f in files:
        out_list.append(os.path.join(root, f))
    return out_list


def build_ffmpeg_file_list(folder, temp_file):
    # This subroutine creates a file that contains all of the files to be converted and concatenated

    if type(folder) is list:
        temp_list = folder
    else:
        for f in build_full_path_from_list(folder, os.listdir(folder)):
            os.rename(f, f.replace(' ', '_').replace("'", ""))
        temp_list = build_full_path_from_list(folder, os.listdir(folder))

    # Check file type
    temp_list = [f for f in temp_list if f.lower().endswith(EXTENSIONS)]

    # Try to put everything in order
    temp_list = sort(temp_list)
    # Write out to file
    for f in temp_list:
        temp_file.write("file '" + f + "'\n")
    temp_file.flush()
    # Nothing to return, we're using a tempfile passed in


def process_single_file(f, return_list):
    out_file = f.split(".")[:-1]
    out_file.append("opus")
    out_file = ".".join(out_file)
    converter = FFmpeg(
        inputs={f: '-hide_banner -loglevel panic'},
        outputs={out_file: '-ac 1 -c:a opus -b:a 55k -threads 4'}
    )

    converter.run()
    return_list.append(out_file)


def process_folder(folder):
    ffmpeg_file_list = tempfile.NamedTemporaryFile(mode='w+t')
    output_file = folder + ".opus"

    build_ffmpeg_file_list(folder, ffmpeg_file_list)


    converter = FFmpeg(
        inputs={ffmpeg_file_list.name: '-hide_banner -loglevel panic -f concat -safe 0'},
        outputs={output_file: '-ac 1 -c:a opus -b:a 55k -threads 4'}
    )

    converter.run()

    ffmpeg_file_list.close()
    return output_file


def process_book_with_sub_folders(root):
    # Assume we are good from here
    # process lower folders first
    dirs = build_full_path_from_list(root, os.listdir(root))
    source_dir = []
    # Remove everything that isn't a directory (doesn't support mixed setup)
    for dir in dirs:
        if os.path.isdir(dir):
            source_dir.append(dir)
    ffmpeg_file_list = tempfile.NamedTemporaryFile(mode='w+t')
    output_file = root + ".opus"
    files = []
    for dir in source_dir:
        files.append(process_folder(dir))
    build_ffmpeg_file_list(files, ffmpeg_file_list)

    converter = FFmpeg(
        inputs={ffmpeg_file_list.name: '-hide_banner -loglevel panic -f concat -safe 0'},
        outputs={output_file: '-c copy'}
    )
    converter.run()

    ffmpeg_file_list.close()

    return output_file


def process_dir(working_dir, return_list=0):
    print("Processing ", working_dir)
    output_files = []
    # Check folder composition (Does it have folders)
    for root, dirs, files in os.walk(working_dir):
        # Process Directories
        if dirs:
            root_name = root.split("/")[-1]
            multiple_books = True

            # Clean up names
            for dir in build_full_path_from_list(root, dirs):
                os.rename(dir, dir.replace(' ', '_').replace("'", ""))
            dirs = os.listdir(root)

            # Check similarity
            for dir in dirs:
                # if similar(root_name, dir) > 0.4:
                if True:
                    # These are sub folders
                    multiple_books = False
                    break
                else:
                    print(dir, "   ", similar(root_name, dir))

            if not multiple_books:
                out_file = process_book_with_sub_folders(root)
                output_files.append(out_file)

        # Process folders with only files
        elif files:
            out_file = process_folder(root)
            output_files.append(out_file)
        # Return values
        if return_list == 0:
            return output_files
        else:
            return_list += output_files


def main():
    work_folder = "/run/user/1000/gvfs/smb-share:server=freenas,share=generalshare/Media/Audiobooks/Raw/convert/Run1"
    # work_folder = os.getcwd()
    working_dir_listing = os.listdir(work_folder)
    failed_to_process = []
    output_files = []

    # Setup parallelism
    manager = multiprocessing.Manager()
    return_list = manager.list()
    jobs = []

    for idx, dir in enumerate(working_dir_listing):
        working_dir_listing[idx] = os.path.join(work_folder, dir)
    print(working_dir_listing)

    try:
        try:
            output_dir = os.path.join(work_folder, "done")
            os.mkdir(output_dir)
        except (FileExistsError, OSError):
            pass

        for dir in working_dir_listing:
            os.rename(dir, dir.replace(' ', '_').replace("'", ""))

            if os.path.isdir(dir):
                # output_files += process_dir(dir)
                p = multiprocessing.Process(target=process_dir, args=(dir, return_list))
                jobs.append([p, dir])
                p.start()
            else:
                if os.path.isfile(dir) and (dir.lower().endswith(".m4a") or dir.lower().endswith(".mp3") or dir.lower().endswith(".flac")):
                    # out_file = process_single_file(dir)
                    p = multiprocessing.Process(target=process_single_file, args=(dir, return_list))
                    jobs.append([p, dir])
                    p.start()
        # Finalize parallel jobs
        for proc, dir in jobs:
            proc.join()
            print("Finished: ", dir.split("/")[-1])
        output_files += return_list


    except Exception:
        print(traceback.format_exc())
    finally:
        # Cleanup
        # os.removedirs(temp_dir)
        print("Failed to process: ", failed_to_process)

if __name__ == "__main__":
    main()