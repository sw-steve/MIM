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
* `sudo pip3 install watchdog`
* Install ffmpeg, make sure it has the config specified encoders

Config file setup:

This file is a json that needs to be in the directory controller is running from. Change any of these values to change the configuration.

{
    "watch_dir" : "/Media/Test/TestProcess",
    "output_dir" : "/Media/Test/TestDone",
    "name_log" : "/Media/Test/Process/name_log.json",
    "number_encodes" : 8,
    "known_extensions" : ["avi", "mp4", "VOB", "mkv"],
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
Launch with python3 controller.py

