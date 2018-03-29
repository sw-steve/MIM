# TODO: custom config files, this is tricky because you have to relate the config file to the input file somehow.
# TODO: Add distributed support
# TODO: Add the ability to continue from a crash (remove files from names_file.json)


import os
import json
import time
from utilities import dir_watch
import shutil
import re
import watchdog

import uuid
import threading
import tempfile
from ffmpy import FFmpeg
import datetime

trigger_events = [watchdog.events.FileModifiedEvent, watchdog.events.FileCreatedEvent]
uuid_match = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


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
        # If there is an existing name map, import it
        if os.path.exists(self.config["name_log"]):
            with open(self.config["name_log"], 'r') as f:
                    self.name_map = json.load(f)


    def start_encode(self, encode_file):
        old_base_name = ""
        new_name = ""
        extension = encode_file.split(".")[-1]
        if extension.lower() in self.known_extensions:
            # print(event)
            if re.search(uuid_match, encode_file):
                try:
                    old_base_name = self.name_map[encode_file]
                except KeyError:
                    print("No known match for ", encode_file)
                    print("Skipping file...")
                    return
                new_name = encode_file
            else:
                # Rename file
                old_name = encode_file
                extension = encode_file.split(".")[-1]
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

    def dispatch(self, event):
        # If there is a uuid in the file name do not automatically
        filename = event.src_path
        if re.search(uuid_match, filename):
            return

        if type(event) in trigger_events:
            # Make sure the file isn't being copied in
            try:
                historicalSize = -1
                while (historicalSize != os.path.getsize(filename)):
                    time.sleep(2)
                    historicalSize = os.path.getsize(filename)
                self.start_encode(filename)
            except FileNotFoundError:
                # This can sometimes happen when the scanner runs and hits the same file twice
                # Once because a copy started and once because a copy finished.
                return

        elif type(event) == watchdog.events.DirModifiedEvent:
            if event.src_path not in self.working_dirs:
                self.working_dirs.append(event)
        else:
            print(event)



def main():
    # Startup
    print("Starting controller...")
    # Config load
    if not os.path.isfile("./config.json"):
        print("No config file.")
        return
    with open("./config.json", "r") as f:
        config = json.load(f)
    known_extensions = config["known_extensions"]

    # Sanity Checks
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
    # Scan through files, manually start orphaned encodes and existing files
    for root, dirs, files in os.walk(config["watch_dir"]):
        for f in files:
            extension = f.split(".")[-1].lower()
            encode_file = os.path.join(root, f)
            if re.search(uuid_match, f) and extension in known_extensions:
                watcher.event_handler.start_encode(encode_file)
            elif extension in known_extensions:
               watcher.event_handler.start_encode(encode_file) 
                # Commented out for now, might want to keep them, else ffmpeg should over write
                # elif extension == config["target_extension"]:
                #     # Clean up partial encode files
                #     os.remove(encode_file)

    # Start directory watcher
    watcher.start_watch()
    print("Watching %s for changes." % config["watch_dir"])
    # Do stuff
    try:
        input()
    except KeyboardInterrupt:
        print("Stopping controller...")
    finally:
        watcher.stop_watch()


if __name__ == "__main__":
    main()


