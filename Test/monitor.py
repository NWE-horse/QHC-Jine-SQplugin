# -*- codeing = utf-8 -*-
# @Time : 2024/6/4 12:06
# @Author :Jnine
# @File : monitor.py
# @Software : PyCharm
import os
import time
import shutil

# 要监控的文件夹路径
folder_to_watch = "D:\squad9-monitor"
# 目标文件夹路径，用于替换文件
target_folder = "D:\squad9\SquadGame\ServerConfig"

# 获取初始文件修改时间
file_modification_times = {}
for filename in os.listdir(folder_to_watch):
    file_path = os.path.join(folder_to_watch, filename)
    file_modification_times[file_path] = os.path.getmtime(file_path)

while True:
    time.sleep(1)  # 每秒检查一次

    # 检查文件是否被修改
    for filename in os.listdir(folder_to_watch):
        file_path = os.path.join(folder_to_watch, filename)
        current_modification_time = os.path.getmtime(file_path)

        # 如果文件被修改
        if current_modification_time != file_modification_times.get(file_path, None):
            print(f"文件 '{filename}' 被修改，将替换目标文件夹内的相同文件...")
            # 替换目标文件夹内的相同文件
            target_file_path = os.path.join(target_folder, filename)
            shutil.copyfile(file_path, target_file_path)
            print(f"已替换目标文件夹内的 '{filename}' 文件")
            # 更新文件修改时间
            file_modification_times[file_path] = current_modification_time
