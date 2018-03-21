import sys
import os
import logging
import string

# from watchdog.observers import Observer
import watchdog
from watchdog.observers.polling import PollingObserverVFS as Observer
# from watchdog.events import LoggingEventHandler

class dir_watch:
    def __init__(self, config, change_manager, poll=1):
        self.watch_dir = config["watch_dir"]
        self.poll = poll
        self.event_handler = change_manager(self.watch_dir, config)
        self.observer = Observer(os.stat, os.listdir)

        try:
            os.stat("./logs")
        except:
            os.mkdir("./logs")

        logging.basicConfig(filename="./logs/dir_watch.log", level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

    def start_watch(self):
        self.observer.schedule(self.event_handler, self.watch_dir, recursive=True)
        self.observer.start()

    def stop_watch(self):
        self.observer.stop()
        self.observer.join()


class name_sanitization:
    def __init__(self, max_depth=4):
        self.max_depth = max_depth
        self.valid_chars = "-_.()\\/%s%s" % (string.ascii_letters, string.digits)


    def sanitize(self, dir):
        pass

    def sanitize_string(self, filename):
        #Replace spaces
        filename = filename.replace(" ", "_")
        #Drop bad characters
        filename = ''.join(char for char in filename if char in self.valid_chars)

        return filename