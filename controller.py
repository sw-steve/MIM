# TODO: custom config files, this is tricky because you have to relate the config file to the input file somehow.
# TODO: remove extra prints and verify python 3 compatibility


import sys
import os
import time
import json
from utilities import dir_watch
import multiprocessing
import shutil
import watchdog

import uuid
import threading
import tempfile
from ffmpy import FFmpeg

modified_events = [watchdog.events.FileModifiedEvent, watchdog.events.FileCreatedEvent]


def vp9_encode_starter(sem, safe_name, starting_name, config):
        out_file = ".".join(safe_name.split(".")[:-1]) + ".webm"
        finished_name = ".".join(starting_name.split(".")[:-1]) + ".webm"
        temp = tempfile.NamedTemporaryFile()
        try:
            # ./ffmpeg -i $1 -c:v libvpx-vp9 -pass 1 -passlogfile $PASSFILE -b:v 0 -crf 33 -threads 12 -speed 4 -tile-columns 6 -frame-parallel 1 -an -f webm /dev/null -y
            # ./ffmpeg -i $1 -c:v libvpx-vp9 -pass 2 -passlogfile $PASSFILE -b:v 0 -crf 33 -threads 12 -speed 2 -tile-columns 6 -frame-parallel 1 -auto-alt-ref 1 -lag-in-frames 25 -c:a libvorbis -q:a 3 -f webm $2 -y
            convert_part1 = FFmpeg(
                inputs={safe_name: '-hide_banner -loglevel panic'},
                outputs={"/dev/null": "-c:v libvpx-vp9 -pass 1 -passlogfile " + temp.name + " -b:v 0 -crf 33 \
                                    -threads 8 -speed 4 -tile-columns 6 -frame-parallel 1 -an -f webm -y"}
            )
            convert_part2 = FFmpeg(
                inputs={safe_name: '-hide_banner -loglevel panic'},
                outputs={out_file: "-c:v libvpx-vp9 -pass 2 -passlogfile " + temp.name + " -b:v 0 -crf 33 \
                                    -threads 8 -speed 1 -tile-columns 6 -frame-parallel 1 \
                                    -auto-alt-ref 1 -lag-in-frames 25 -c:a libvorbis -q:a 3 -y"}
            )

            part1 = multiprocessing.Process(target=convert_part1.run)
            part2 = multiprocessing.Process(target=convert_part2.run)

            print("Entering sem.\nWorking on: ", finished_name)
            # Limit encodes started by waiting for semaphore
            with sem:
                print("Starting Pass 1. Working on: ", finished_name)
                print("Temp file: ", temp.name)

                # part1.start()
                print("running...", finished_name)
                convert_part1.run()
                # part1.join()
                print("Starting Pass 2. Working on: ", finished_name)
                convert_part2.run()
                # part2.start()
                # part2.join()
            # print("Starting Pass 1. Working on: ", finished_name)
            # convert_part1.run()
            # print("Starting Pass 2. Working on: ", finished_name)
            # convert_part2.run()

            print("Finished Encoding.")
            print("Moving files...")
            shutil.move(out_file, os.path.join(config["output_dir"], finished_name))
            shutil.move(safe_name, os.path.join(config["output_dir"], "source", starting_name))
        finally:
            temp.close()


class ChangeManager(object):
    def __init__(self, watch_dir, config):
        self.working_dirs = []
        self.working_dirs.append(watch_dir)
        self.known_extensions = config["known_extensions"]  # Filled by dir watch setup
        self.name_map = {}
        self.encode_sem = threading.Semaphore(config["number_encodes"])
        self.log_sem = threading.Semaphore(1)
        self.config = config

    def dispatch(self, event):
        if type(event) in modified_events:
            
            # Check extension
            extension = event.src_path.split(".")[-1]
            if extension in self.known_extensions:
                print(event)
                # Check if config exists

                # Rename file
                old_name = event.src_path
                old_base_name = os.path.basename(old_name)
                new_name = os.path.join(os.path.dirname(old_name), str(uuid.uuid4()) + "." + extension)
                os.rename(old_name, new_name)
                self.name_map[new_name] = old_base_name

                # Start Convert
                print("Starting thread.")
                t = threading.Thread(target=vp9_encode_starter, args=(self.encode_sem, new_name, old_base_name, self.config))
                t.start()

                # Update names in case of crash
                with self.log_sem:
                    with open(self.config["name_log"], 'w') as f:
                        f.seek(0)
                        json.dump(self.name_map, f)
                        f.truncate()

        elif type(event) == watchdog.events.DirModifiedEvent:
            if event.src_path not in self.working_dirs:
                self.working_dirs.append(event)
        else:
            print(event)



def main():
    # Startup
    print("Starting controller...")
    if not os.path.isfile("./config.json"):
        print("No config file.")
        return
    with open("./config.json", "r") as f:
        config = json.load(f)

    # Make sure directories exist
    if not os.path.isdir(config["watch_dir"]):
        os.makedirs(config["watch_dir"])
    temp_path = os.path.join(config["output_dir"], "source")
    if not os.path.isdir(config["output_dir"]):
        os.makedirs(temp_path)
    elif not os.path.isdir(temp_path):
        os.makedirs(temp_path)

    # Start dir watcher
    watcher = dir_watch(config, ChangeManager)
    watcher.start_watch()
    print("Watching %s for changes." % config["watch_dir"])
    # Do stuff
    input()
    watcher.stop_watch()


if __name__ == "__main__":
    main()


