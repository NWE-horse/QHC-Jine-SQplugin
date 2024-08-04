# -*- coding: utf-8 -*-
# @Time : 2024/8/1 3:05
# @Author : Jnine
# @File : monitor.py
# @Software : PyCharm

import os
import time
import shutil
import datetime
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 要监控的文件路径列表
files_to_watch = [
    "D:\\SquadServer\\server1\\SquadGame\\ServerConfig\\Bans.cfg",
    "D:\\SquadServer\\server2\\SquadGame\\ServerConfig\\Bans.cfg",
    "D:\\SquadServer\\server3\\SquadGame\\ServerConfig\\Bans.cfg",
    "D:\\SquadServer\\server4\\SquadGame\\ServerConfig\\Bans.cfg"
]

# 目标文件路径
target_file = "D:\\Cfg\\Bans.cfg"

# 正则表达式模式
admin_pattern = r'(.*?)\[EOSID ([0-9a-f]{32})\] Banned:(.*):(\d) //(.*)'
system_pattern = r'(.*?) Banned:([0-9a-f]{32}):(\d*) //(.*)'

def match_line(data):
    admin_match = re.match(admin_pattern, data)
    system_match = re.match(system_pattern, data)

    if admin_match:
        line = f'{admin_match.group(1)} Banned:{admin_match.group(3)}:{admin_match.group(4)} //{admin_match.group(5)}'
    elif system_match:
        if system_match.group(4) != 'Automatic Teamkill Kick':
            line = f'服务器 Banned:{system_match.group(2)}:{system_match.group(3)} //{system_match.group(4)}'
        else:
            line = None
    else:
        print('不规范的ban', data)
        line = data

    return line

def read_file(file_path):
    """读取文件内容并返回去除多余空白行的内容"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return set(match_line(line.strip()) for line in file if match_line(line.strip()))

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, target_file):
        self.target_file = target_file

    def on_modified(self, event):
        if event.src_path in files_to_watch:
            t = datetime.datetime.now().strftime('%m/%d %H:%M:%S')
            print(f"[{t}] 文件 '{event.src_path}' 被修改，将处理文件内容...")
            unique_lines = set()
            for file_path in files_to_watch:
                unique_lines.update(read_file(file_path))

            with open(self.target_file, 'w', encoding='utf-8') as file:
                for line in unique_lines:
                    if line:  # 跳过 None
                        file.write(line + '\n')
            print(f"[{t}] 已更新目标文件 '{self.target_file}'")

def main():
    event_handler = FileChangeHandler(target_file)
    observer = Observer()

    # 监控每个文件所在的目录
    for file_path in files_to_watch:
        directory = os.path.dirname(file_path)
        observer.schedule(event_handler, directory, recursive=False)

    observer.start()
    print("开始监控文件变更...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("停止监控...")
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
