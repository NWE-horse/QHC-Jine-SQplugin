import socket
import struct
from threading import Thread, Event
from queue import Queue
import datetime
import threading
class RconConnection:
    def __init__(self):
        self.net_connection = None
        self.response_string = ""
        self.stream = bytearray()
        self.types = {"auth": 0x03, "command": 0x02, "response": 0x00, "server": 0x01}
        self.soh = {"size": 7, "id": 0, "type": self.types["response"], "body": "\x01"}
        self.keep_running = Event()
        self.keep_running.set()
        self.response_queue = Queue()  # 创建一个队列用于主线程和子线程之间通信,整体响应
        self.response_server = Queue()  # 创建一个队列用于主线程和子线程之间通信,服务器响应
        # 设置定时器，每隔一段时间发送一次心跳包
        threading.Timer(20, self.send_squad).start()
        threading.Timer(1, self.send_playerlist).start()

    def connect(self, port, host, token):
        self.net_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.net_connection.connect((host, port))
        self._write(self.types['auth'], 2147483647, token.encode('utf-8'))
        Thread(target=self._receive_data).start()

    def send(self, body, id=99):
        try:
            self._write(self.types['command'], id, body.encode('utf-8', errors='ignore'))
            self._write(self.types["command"], id + 2)
            if body != 'ListSquads' and body != 'ListPlayers':
                t = datetime.datetime.now().strftime('%m/%d %H:%M:%S')
                print("[{time_}]客户端发送指令：{command}".format(time_=t, command=body))
        except OSError:
            print('服务器关闭或重启')

    def send_squad(self):
        self.send("ListSquads")
        # 重新启动定时器，继续定时发送心跳包
        threading.Timer(20, self.send_squad).start()

    def send_playerlist(self):
        self.send("ListPlayers")
        # 重新启动定时器，继续定时发送心跳包
        threading.Timer(1, self.send_playerlist).start()

    def _write(self, type, id, body=b''):
        size = 10 + len(body)
        packet = struct.pack('<iii', size, id, type) + body + b'\x00\x00'
        self.net_connection.sendall(packet)

    def _receive_data(self):
        while True:
            data = self.net_connection.recv(4096)
            if not data:
                break
            self.stream += data
            while len(self.stream) >= 4:
                packet = self._decode()
                if not packet:
                    break
                elif packet["type"] == self.types["response"]:
                    self._on_response(packet)
                elif packet["type"] == self.types["server"]:
                    self.response_queue.put(packet['body'])
                    # print("服务器信息:", packet["body"])
                elif packet["type"] == self.types["command"]:
                    pass

    def _decode(self):
        if self.stream[:7] == b"\x00\x01\x00\x00\x00\x00\x00":
            self.stream = self.stream[7:]
            return self.soh
        if len(self.stream) < 4:
            return None
        size = struct.unpack("<i", self.stream[:4])[0]
        if len(self.stream) < size + 4:
            return None
        response = {
            "size": size,
            "id": struct.unpack("<i", self.stream[4:8])[0],
            "type": struct.unpack("<i", self.stream[8:12])[0],
            "body": self.stream[12:size + 2].decode("utf-8")
        }
        self.stream = self.stream[size + 4:]
        return response

    def _on_response(self, packet):
        if packet["body"] != "\x01":
            self.response_string += packet['body']
        else:
            # print('完整数据',self.response_string)
            self.response_server.put(self.response_string)
            self.response_string = ""