# Table of Contents
- [Introduction](#introduction)
- [Setup](#setup)
- [Usage](#usage)



# Introduction
This is some code that watches a directory and automatically encodes based on a config file.


# Setup

This has been tested on an Ubuntu 16.04 machine. Should work on other linux platforms.

First, clone this repository
Install the following dependencies.
ffmpy
watchdog

* `sudo pip3 install ffmpy watchdog`
* Install ffmpeg, make sure it has the config specified encoders

Config file setup:

Currently this code uses a json file for configuration. This configuration is also configured for vp9 encoding. Change any of these values to change the configuration.

{
    "watch_dir" : "/Media/Test/TestProcess",
    "output_dir" : "/Media/Test/TestDone",
    "name_log" : "/Media/Test/Process/name_log.json",
    "number_encodes" : 8,
    "known_extensions" : ["avi", "mp4", "VOB", "mkv"],
    "target_extension" : "webm",    
    "video_encode_options" : {
        "c:v" : "libvpx-vp9",
        "threads" : "16",
        "b:v" : "0",
        "crf" : "33",
        "tile-columns" : "6",
        "frame-parallel" : "1",
        "f" : "webm"
    },
    "p1_opts" : {
        "pass" : "1",
        "an" : "",
        "speed" : "4"
    },
    "p2_opts" : {
        "pass" : "2",
        "auto-alt-ref" : "1",
        "lag-in-frames" : "25",
        "c:a" : "libvorbis",
        "q:a" : "3"
    }
}

# Usage
This package was written for python3. There are no options passed in. All configuration comes from the config.json file.
Run `python3 controller.py`

