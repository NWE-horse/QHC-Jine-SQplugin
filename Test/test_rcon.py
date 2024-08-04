import socket
import struct
import time
import json
import threading
import requests

class RconConnection:
    def __init__(self):
        self.stream = b""
        self.response_string = ""
        self.type = {"auth": 0x03, "command": 0x02, "response": 0x00, "server": 0x01}
        self.soh = {"size": 7, "id": 0, "type": self.type["response"], "body": "\x01"}
        self.socket = None
        self.interval = None

    def connect(self, host, port, token):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, int(port)))
        self._write(self.type["auth"], 2147483647, token)
        threading.Thread(target=self._receive_data).start()

    def send(self, body, id=99):
        self._write(self.type["command"], id, body)
        self._write(self.type["command"], id + 2)

    def _write(self, type_, id, body=""):
        packet = self._encode(type_, id, body)
        self.socket.sendall(packet)

    def _encode(self, type_, id, body=""):
        size = len(body) + 14
        buffer = struct.pack("<iii", size - 4, id, type_)
        buffer += body.encode("utf-8")
        buffer += b"\x00\x00"
        return buffer

    def _receive_data(self):
        while True:
            data = self.socket.recv(4096)
            if not data:
                break
            self.stream += data
            while len(self.stream) >= 4:
                packet = self._decode()
                if not packet:
                    break
                elif packet["type"] == self.type["response"]:
                    self._on_response(packet)
                elif packet["type"] == self.type["server"]:
                    pass
                    # print("服务器信息:", packet["body"])
                elif packet["type"] == self.type["command"]:
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
            self.response_string+=packet['body']
        else:
            print("完整响应:", self.response_string)
            self.response_string = ""


def send_data_to_server(data):
    url = "http://localhost:5004/server-data"
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"请求遇到问题: {e}")


def squad_rcon(servers):
    for server in servers:
        rcon = RconConnection()

        def connect_and_setup():
            try:
                rcon.connect(server["host"], server["port"], server["token"])

                rcon.interval = threading.Event()
                def send_command():
                    while not rcon.interval.is_set():
                        rcon.send("ListPlayers")
                        time.sleep(10)  # 10 seconds

                threading.Thread(target=send_command).start()

            except Exception as err:
                print(f"服务器 {server['serverId']} 初始化连接失败:", err)
                time.sleep(60)  # Reconnect after 1 minute
                connect_and_setup()

        connect_and_setup()


servers = [
    {"serverId": "mxxy", "port": "25001", "host": "180.188.21.82", "token": "9UneFErmhxU6Knmreo9QSbgVQiRXyLrt"},
    {"serverId": "mxth", "port": "25009", "host": "180.188.21.82", "token": "GJUs0fx6G8jtrRtY"},
    {"serverId": "qgxy", "port": "25003", "host": "180.188.21.82", "token": "3$wnSazw%qZ3bVAsmN"},
    {"serverId": "qgth", "port": "25004", "host": "180.188.21.82", "token": "4#6ecS2p%Gp9Gms2B2"},
    {"serverId": "wzll", "port": "25007", "host": "180.188.21.82", "token": "886adf"}
]

squad_rcon(servers)

def on_uncaught_exception(exctype, value, traceback):
    print('未捕获的异常:', value)

import sys
sys.excepthook = on_uncaught_exception
