import datetime
import socket
import struct
import threading
import time


class RconConnection:
    def __init__(self):
        self.events = {
            'auth': [],
            'response': [],
            'server': [],
            'end': []
        }
        self.net_connection = None
        self.stream = b''
        self.response_string = ""
        self.type = {'auth': 0x03, 'command': 0x02, 'response': 0x00, 'server': 0x01}
        self.soh = {'size': 7, 'id': 0, 'type': self.type['response'], 'body': "\x01"}
        threading.Timer(20, self.send_heartbeat).start()
        threading.Timer(1, self.send_player_list).start()
    def send_heartbeat(self):
        self.send("ListSquads")
        # 重新启动定时器，继续定时发送心跳包
        threading.Timer(20, self.send_heartbeat).start()

    def send_player_list(self):
        self.send("ListPlayers")
        # 重新启动定时器，继续定时发送心跳包
        threading.Timer(1, self.send_player_list).start()

    def connect(self, host, port, token):
        self.net_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.net_connection.connect((host, port))
        threading.Thread(target=self._receive_data, daemon=True).start()
        self._write(self.type['auth'], 2147483647, token)

    def send(self, body, id=99):
        self._write(self.type['command'], id, body)
        self._write(self.type['command'], id + 2)

    def _write(self, type, id, body=""):
        packet = self._encode(type, id, body)
        self.net_connection.sendall(packet)

    def _encode(self, type, id, body=""):
        size = len(body) + 14
        buffer = struct.pack('<iii', size - 4, id, type)
        buffer += body.encode('utf-8') + b'\x00\x00'
        return buffer

    def _receive_data(self):
        try:
            while True:
                data = self.net_connection.recv(4096)
                if not data:
                    break
                self.stream += data
                while len(self.stream) >= 4:
                    packet = self._decode()
                    if not packet:
                        break
                    elif packet['type'] == self.type['response']:
                        self._on_response(packet)
                    elif packet['type'] == self.type['server']:
                        self._emit_event('server', packet['body'])
                    elif packet['type'] == self.type['command']:
                        self._emit_event('auth')
        finally:
            self._emit_event('end')

    def _decode(self):
        if self.stream[:7] == b'\x00\x01\x00\x00\x00\x00\x00':
            self.stream = self.stream[7:]
            return self.soh
        if len(self.stream) < 4:
            return None
        buf_size = struct.unpack('<i', self.stream[:4])[0]
        if buf_size <= len(self.stream) - 4:
            response = {
                'size': buf_size,
                'id': struct.unpack('<i', self.stream[4:8])[0],
                'type': struct.unpack('<i', self.stream[8:12])[0],
                'body': self.stream[12:buf_size + 2].decode('utf-8')
            }
            self.stream = self.stream[buf_size + 4:]
            return response
        return None

    def _on_response(self, packet):
        if packet['body'] != "\x01":
            self.response_string += packet['body']
        else:
            self._emit_event('response', self.response_string)
            self.response_string = ""

    def _emit_event(self, event, *args):
        for callback in self.events[event]:
            callback(*args)

    def on(self, event, callback):
        if event in self.events:
            self.events[event].append(callback)

def squad_rcon():
    rcon = RconConnection()

    def on_server(message):
        rcon.send('AdminDisableVehicleClaiming 1')
        return 0

    def on_response(response):
        pass
        # print(response)

    def on_end():
        rcon.net_connection.close()

    rcon.on('server', on_server)
    rcon.on('response', on_response)
    rcon.on('end', on_end)

    rcon.connect('180.188.21.67', 25005, 'asdfghjklpo')

    # Keep the script running to maintain the connection and handle events
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping RCON connection")

# Execute the function to start the RCON connection
squad_rcon()
