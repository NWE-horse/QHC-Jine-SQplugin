# -*- codeing = utf-8 -*-
# @Time : 2024/5/31 12:45
# @Author :Jnine
# @File : read_lines.py
# @Software : PyCharm
import random
def Custom_random():
    with open('../Data/random_list.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        num_lines = len(lines)
        number = random.randint(0, num_lines-1)
        print(lines[number])
Custom_random()