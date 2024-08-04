# -*- codeing = utf-8 -*-
# @Time : 2024/5/28 11:25
# @Author :Jnine
# @File : test_log2.py
# @Software : PyCharm
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def tail_log_file(log_file_path):
    class LogFileHandler(FileSystemEventHandler):
        def __init__(self, log_file):
            super().__init__()
            self.log_file = log_file

        def on_modified(self, event):
            if event.src_path == self.log_file:
                with open(self.log_file, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                    if lines:
                        print(lines[-1])

    class LogTailMonitor:
        def __init__(self, log_file):
            self.log_file = log_file

        def tail(self):
            event_handler = LogFileHandler(self.log_file)
            observer = Observer()
            observer.schedule(event_handler, os.path.dirname(self.log_file), recursive=False)
            observer.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                print("Stopped by user.")
            observer.join()

    tail_monitor = LogTailMonitor(log_file_path)
    try:
        tail_monitor.tail()
    except Exception as e:
        print(f"Error occurred: {e}")

# Example usage:
log_file_path = r'D:\squad1\SquadGame\Saved\Logs\SquadGame.log'
tail_log_file(log_file_path)
