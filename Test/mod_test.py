# -*- codeing = utf-8 -*-
# @Time : 2024/4/29 21:50
# @Author :Jnine
# @File : mod_test.py
# @Software : PyCharm
import socket
import struct
from threading import Thread
import time
from queue import Queue
import random
import re
import datetime
import configparser
import urllib.request
from bs4 import BeautifulSoup
import threading
import numpy as np
import yaml

class RconConnection:
    def __init__(self):
        self.net_connection = None
        self.stream = bytearray()
        self.response_string = ""
        self.types = {'auth': 0x03, 'command': 0x02, 'response': 0x00, 'server': 0x01}
        self.response_queue = Queue()
        self.response_server = Queue()# 创建一个队列用于主线程和子线程之间通信
        # 设置定时器，每隔一段时间发送一次心跳包
        self.timer = threading.Timer(120, self.send_heartbeat)
        self.timer.start()

    def connect(self, port, host, token):
        self.net_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.net_connection.connect((host, port))
        self._write(self.types['auth'], 2147483647, token.encode('utf-8'))
        Thread(target=self._receive_data).start()

    def send(self, body, id=99):
        self._write(self.types['command'], id, body.encode('utf-8'))

    def send_heartbeat(self):
        # 发送心跳包

        # 重新启动定时器，继续定时发送心跳包
        self.timer = threading.Timer(120, self.send_heartbeat)
        self.timer.start()

    def _write(self, type, id, body=b''):
        size = 10 + len(body)
        packet = struct.pack('<iii', size, id, type) + body + b'\x00\x00'
        self.net_connection.sendall(packet)

    def _receive_data(self):
        try:
            while True:
                data = self.net_connection.recv(4026)
                if not data:
                    pass
                self.stream.extend(data)
                self._process_stream()
        except Exception as e:
            print("接收数据时发生异常:", e)
        finally:
            print("连接结束。")
            self.net_connection.close()

    def _process_stream(self):
        while len(self.stream) >= 4:
            size = struct.unpack_from('<i', self.stream)[0]
            if len(self.stream) >= size + 4:
                self._decode_packet(size)
            else:
                break

    def _decode_packet(self, size):
        id, type = struct.unpack_from('<ii', self.stream, 4)
        body = self.stream[12:size + 4 - 2].decode('utf-8')
        self.stream = self.stream[size + 4:]
        if body != '':
            self.response_queue.put(body)  # 将解码后的内容放入队列中

        if type == self.types['response']:
            if body != '\x01':
                self.response_string += body
                print('dd',body)
            else:
                print("最终响应:", self.response_string)
                self.response_string = ''
        elif type == self.types['server']:
            self.response_server.put(self.response_string)
        elif type == self.types['command']:
            pass

if __name__ == '__main__':
    rcon = RconConnection()
    ip = '180.188.21.144'
    port = 25001
    pasword = '9UneFErmhxU6Knmreo9QSbgVQiRXyLrt'
    rcon.connect(port, ip, pasword)
    Sqmatch = r'ID: (\d*) \| Name: (.+) \| Size: (\d) \| Locked: (\w+) \| Creator Name:(.+) \| Creator Online IDs: EOS: ([\da-f]{32}) steam: (\d{17})'
    rcon.send('ListSquads')
    decoded_data = rcon.response_server.get()
    # print(decoded_data)
    # ls = re.findall(Sqmatch, decoded_data)
    # for i in ls:
    #     size = i[2]
    #     name = i[1]
    #     locked = i[3]
    #     ctorname = i[4]
    #     if re.findall(r'(小队 \d)',name) != [] or name=='指挥小队':
    #         if locked =='True':
    #             rcon.send(f'AdminWarn {ctorname} 插件检测到您已锁队，步兵队禁止锁队，请打开队锁,Infantry squad are prohibited from locking. Please open the lock')
    #     else:
    #         if name =='TANK' or name =='tank':
    #             if int(size) > 3:
    #                 rcon.send(f'AdminWarn {ctorname} 插件检测到您已超员，请减少成员人数,Members are out of range. Please reduce the number of members.')
    #             else:
    #                 pass


