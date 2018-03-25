# TODO: custom config files, this is tricky because you have to relate the config file to the input file somehow.
# TODO: Add distributed support
# TODO: Actually use the configuration information to drive the encodes
# TODO: Add the ability to continue from a crash (remove files from names_file.json)


import os
import json
from utilities import dir_watch
import shutil
import watchdog

import uuid
import threading
import tempfile
from ffmpy import FFmpeg
import datetime

trigger_events = [watchdog.events.FileModifiedEvent, watchdog.events.FileCreatedEvent]


# class EncodeRestarter:
#     def __init__(self, config):
    # watcher.event_handler.dispatch(watchdog.events.FileModifiedEvent)
        # Rename non-webm files back to original name
        # Read in config, move non-.webm files to a temp folder
        # Delete orphaned .webm files
        # start watcher, move files out of temp folder into process folder



def vp9_encode_starter(sem, safe_name, starting_name, config):
        out_file = ".".join(safe_name.split(".")[:-1]) + ".webm"
        finished_name = ".".join(starting_name.split(".")[:-1]) + ".webm"
        # Video encode options
        ve = config["video_encode_options"]
        p1 = config["p1_opts"]
        p2 = config["p2_opts"]
        temp = tempfile.NamedTemporaryFile()

        # Create base command
        cmd = ["-{} {}".format(key, ve[key]) for key in ve.keys()]
        # Add pass log file to base command
        cmd.insert(-3, "-passlogfile " + temp.name)
        cmd.append("-y")
        # print("cmd: ", cmd)
        # Create first pass command with part1 options
        part1_specific_options = ["-{} {}".format(key, p1[key]) for key in p1.keys()]
        # print("part1_so: ", part1_specific_options)
        part1_cmd = cmd[:-2] + part1_specific_options + cmd[-2:]
        # Join list to create cmd string
        part1_cmd = " ".join(part1_cmd)

        # Create second pass command with part2 options
        part2_specific_options = ["-{} {}".format(key, p2[key]) for key in p2.keys()]
        part2_cmd = cmd[:-2] + part2_specific_options + cmd[-2:]
        # Join list to create cmd string
        part2_cmd = " ".join(part2_cmd)


        # Command format:
        # part1_cmd ="-c:v libvpx-vp9 -pass 1 -passlogfile " + temp.name + " -b:v 0 -crf 33 \
                #                         -threads 8 -speed 4 -tile-columns 6 -frame-parallel 1 -an -f webm -y"
        # part2_cmd = "-c:v libvpx-vp9 -pass 2 -passlogfile " + temp.name + " -b:v 0 -crf 33 \
        #                             -threads 8 -speed 1 -tile-columns 6 -frame-parallel 1 \
        #                             -auto-alt-ref 1 -lag-in-frames 25 -c:a libvorbis -q:a 3 -y"
        try:
            # print("part1: ", part1_cmd)
            convert_part1 = FFmpeg(
                inputs={safe_name: '-hide_banner -loglevel panic'},
                outputs={"/dev/null": part1_cmd}
            )
            # print("part2: ", part2_cmd)
            convert_part2 = FFmpeg(
                inputs={safe_name: '-hide_banner -loglevel panic'},
                outputs={out_file: part2_cmd}
            )

            print("Entering sem.\nWorking on: ", finished_name)
            # Limit encodes started by waiting for semaphore
            with sem:
                # print("Temp file:1 ", temp.name)
                print("Starting Pass 1. Working on: ", finished_name)
                start_time = datetime.datetime.now()
                convert_part1.run()

                print("Starting Pass 2. Working on: ", finished_name)
                convert_part2.run()

            finish_time = datetime.datetime.now() - start_time
            print("Finished Encoding {}, encode duration: {}".format(finished_name, finish_time))
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
        if type(event) in trigger_events:
            
            # Check extension
            extension = event.src_path.split(".")[-1]
            if extension.lower() in self.known_extensions:
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
                # Single thread for testing
                # vp9_encode_starter(self.encode_sem, new_name, old_base_name, self.config)

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



    # Configure directory watcher
    watcher = dir_watch(config, ChangeManager)

    # Restart orphaned encodes
    # ToDo: instatiate class, call methods for rename and move operations

    # Start directory watcher
    watcher.start_watch()
    print("Watching %s for changes." % config["watch_dir"])
    # Do stuff
    input()
    watcher.stop_watch()


if __name__ == "__main__":
    main()


