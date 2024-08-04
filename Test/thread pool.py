# -*- codeing = utf-8 -*-
# @Time : 2024/8/1 1:43
# @Author :Jnine
# @File : thread pool.py
# @Software : PyCharm
import threading
import time
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=10)
def log():
    a = 0
    for i in range(0,200):
        a+=1
        executor.submit(pt,a)
def pt(data):
    print(data)
if __name__ == '__main__':
    log()