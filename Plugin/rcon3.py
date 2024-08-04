import socket
import sqlite3
import struct
import subprocess
import time
from threading import Thread, Event
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import random
import re
import datetime
import configparser
import threading
import yaml
import json
import os
import requests
import copy
import logging
import sys

# 配置全局日志记录
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y/%m/%d %H:%M:%S')

file_handler = logging.FileHandler('error.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
logger.addHandler(file_handler)

def log_uncaught_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常并写入日志"""
    if issubclass(exc_type, KeyboardInterrupt):
        # 允许 KeyboardInterrupt 中断程序
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        logger.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = log_uncaught_exception

# 记录玩家飞天开始时间
flight_start_times = {}
# 记录团队所有玩家
team_players = {}
Player_Lock = threading.Lock()
Player_Condition = threading.Condition(Player_Lock)
# 引入一个 Event 对象来指示删除操作
deletion_in_progress = threading.Event()
# 玩家开始空闲时间
outboard_start_time = {}
# 是否进行检查操作
outboard_check = 0
# 记录建队时间
squad_create = {}
# 记录士兵id
soldier_id = {}
# 记录kd
kill_death = []
# 记录游戏时长
game_time_stats = {}
# 读取线程锁对象
config_lock = threading.Lock()
# 等待连接完成的用户
pending_user_connected = {}

# 警告次数
warn_count = {}

def Readyaml(name):
    with open("../Data/server-rule.yaml", encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data[name]


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
        # threading.Timer(240, self.send_thanks).start()
        # threading.Timer(300, self.send_support).start()

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

    # def send_thanks(self):
    #     self.send('AdminBroadcast 服务器股东：单行、制霸、刘杵杵')
    #     threading.Timer(240, self.send_thanks).start()
    #
    # def send_support(self):
    #     self.send('AdminBroadcast 感谢技术支持：Wander_大杰')
    #     threading.Timer(300, self.send_support).start()

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


class re_str:
    def __init__(self):
        # 预编译正则表达式
        self.wound_pattern = re.compile(
            r'\[DedicatedServer\]ASQSoldier::Wound\(\): Player:(.+?) KillingDamage=(.+) from (.+) \(Online IDs: EOS: ([0-9a-f]{32}) steam: (\d{17})')
        self.kill_pattern = re.compile(
            r'\[DedicatedServer\]ASQSoldier::Die\(\): Player:(.+?) KillingDamage=(.+) from (.+) \(Online IDs: EOS: ([0-9a-f]{32}) steam: (\d{17})')
        self.connection_pattern = re.compile(
            r'\[([0-9.:-]+)\]\[([ 0-9]*)\]LogSquad: PostLogin: NewPlayer: BP_PlayerController_C (.*).(BP_PlayerController_C_\d+) \(IP: (\d+\.\d+\.\d+\.\d+) \| Online IDs: EOS: ([a-f0-9]{32}) steam: (\d+)')
        self.join_success_pattern = re.compile(r'\[([0-9.:-]+)\]\[([ 0-9]*)\]LogNet: Join succeeded: (.*)')
        self.disconnect_pattern = re.compile(
            r'\[([0-9.:-]+)\]\[([ 0-9]*)\]LogNet: UNetConnection::Close: \[UNetConnection\] RemoteAddr: ([\d.]+):[\d]+, Name: EOSIpNetConnection_[0-9]+, Driver: GameNetDriver EOSNetDriver_[0-9]+, IsServer: YES, PC: ([^ ]+PlayerController_C_[0-9]+|NULL), Owner: ([^ ]+PlayerController_C_[0-9]+|NULL), UniqueId: RedpointEOS:([\d\w]+)')
        self.errorlog_pattern = re.compile(
            r'LogNetPlayerMovement: Warning: ServerMove: TimeStamp expired: (.+), CurrentTimeStamp: (.+), Character: BP_Soldier_(.*)')
        self.soldier_pattern = re.compile(
            r'\[([0-9.:-]+)\]\[([ 0-9]*)\]LogSquadTrace: \[DedicatedServer\]ASQPlayerController::OnPossess\(\): PC=(.+?) \(Online IDs: EOS: ([0-9a-f]{32}) steam: (\d{17})\) Pawn=BP_Soldier_(.*) FullPath=BP_Soldier_(.*) (.*)')
        self.won_match_pattern = re.compile(
            r'\[([0-9.:-]+)\]\[([ 0-9]*)\]LogSquadGameEvents: Display: Team (\d), (.*?) has won the match with (\d*) Tickets on layer (.*v\d)')
    def chat(self, data):
        matchChat = re.match(
            r'\[(ChatAll|ChatTeam|ChatSquad|ChatAdmin)] \[Online IDs:EOS: ([0-9a-f]{32}) steam: (\d{17})] (.+?) : (.*)',
            data)
        if matchChat:
            CHAT_MESSAGE = {
                "chat": matchChat[1],
                "eosID": matchChat[2],
                "steamID": matchChat[3],
                "name": matchChat[4],
                "message": matchChat[5]
            }
            return CHAT_MESSAGE
        else:
            return 0

    def SqCreated(self, data):
        matchsqCreated = re.match(
            r"(.+) \(Online IDs: EOS: ([\da-f]{32})(?: steam: (\d{17}))?\) has created Squad (\d+) \(Squad Name: (.+)\) on (.+)",
            data)
        if matchsqCreated:
            CREATE_MESSAGE = {
                "name": matchsqCreated[1],
                "steamid": matchsqCreated[3],
                "id": matchsqCreated[4],
                "squad": matchsqCreated[5],
                "team": matchsqCreated[6]
            }
            return CREATE_MESSAGE
        else:
            return 0

    def plList(self, data):
        matchplrList = re.findall(
            r'ID: (\d*) \| Online IDs: EOS: ([\da-f]{32})(?: steam: (\d{17}))? \| Name: (.*?) \| Team ID: (\d) \| Squad ID: (.+) \| Is Leader: (.+) \| Role: (.+)',
            data)
        l = []
        # print(data)
        if matchplrList != []:
            for i in matchplrList:
                List = {
                    'eosid': i[1],
                    'id': i[2],
                    'name': i[3],
                    'team': i[4],
                    'squad': i[5]
                }
                l.append(List)
            return l
        else:
            return 0

    def SqList(self, data):
        Sqmatch = r'ID: (\d*) \| Name: (.+) \| Size: (\d) \| Locked: (\w+) \| Creator Name:(.+) \| Creator Online IDs: EOS: ([\da-f]{32}) steam: (\d{17})'
        ls = re.findall(Sqmatch, data)
        return ls

    def TeamKill(self, data):
        Tkmatch = r'\[ChatAdmin] ASQKillDeathRuleset : Player (.+)Team Killed Player (.+)'
        ls = re.match(Tkmatch, data)
        if ls:
            TK_MESSAGE = {
                'player1': ls[1],
                'player2': ls[2]
            }
            return TK_MESSAGE
        else:
            return 0

    def AdminPlayer(self):
        with open(Readyaml('AdminCfgPath'), encoding='utf-8') as f:
            Ad = f.read()
            Admin = re.findall(r'Admin=(\d{17}):(.+)| ', Ad)
            Admin_list = []
            for i in Admin:
                if i[0] != '':
                    data = {
                        'steamid': i[0],
                        'power': i[1].split(" ")[0]
                    }
                    Admin_list.append(data)
            return Admin_list

    def Wound_(self, data):
        match = self.wound_pattern.findall(data)
        if match:
            Wound_message = {
                'death': match[0][0],
                'actor': match[0][4],
                'wound': match[0][4]
            }
            return Wound_message
        else:
            return 0

    def Kill_(self, data):
        match = self.kill_pattern.findall(data)
        if match:
            Kill_message = {
                'death': match[0][0],
                'actor': match[0][4]
            }
            return Kill_message
        else:
            return 0

    def connection(self, data):
        loginmatch = self.connection_pattern.match(data)
        if loginmatch:
            data = {
                'soldierid': loginmatch[4],
                'ip': loginmatch[5],
                'eosid': loginmatch[6],
                'steamid': loginmatch[7]
            }
            return data
        else:
            return None

    def join_success(self, data):
        match = self.join_success_pattern.match(data)
        if match:
            JOIN_SUCCESS = {
                'name': match[3]
            }
            return JOIN_SUCCESS
        else:
            return None

    def Disconnect(self, data):
        match = self.disconnect_pattern.match(data)
        if match:
            DISCONNECT_DATA = {
                'time': match[1],
                'chainID': match[2],
                'ip': match[3],
                'playerController': match[4],
                'eosid': match[6]
            }
            return DISCONNECT_DATA
        else:
            return 0

    def errorlog(self, data):
        match = self.errorlog_pattern.findall(data)
        if match:
            er = {
                'expiredtime': match[0][0],
                'currenttime': match[0][1],
                'soldierid': match[0][2]
            }
            return er
        else:
            return 0

    def soldier_(self, data):
        soldier_match = self.soldier_pattern.match(data)
        if soldier_match:
            data = {
                'name': soldier_match[3],
                'steamid': soldier_match[5],
                'soldierid': soldier_match[6]
            }
            return data
        else:
            return None

    def won_match(self, data):
        win = self.won_match_pattern.match(data)
        if win:
            data = {
                'team': win[3],
                'team_name': win[4],
                'tickets': win[5],
                'map': win[6]
            }
            return data
        else:
            return None

class Base:
    def __init__(self):
        self.path = Readyaml('ServerPath')
        self.UndisclosedPlyaerJoinCheckWarn = Readyaml('UndisclosedPlyaerJoinCheckWarn')  # 玩家加入检查
        self.UndisclosedPlyaerJoinHandle = Readyaml('UndisclosedPlyaerJoinHandle')  # 异常玩家加入处理
        self.re_ = re_str()
        self.AdminPlyerJoin = Readyaml('AdminPlyerJoin')
        self.DataPath = Readyaml('DataPath')
        self.RandomTeamTicks = Readyaml('RandomTeamTicks')  # 打乱票数
        self.executor = ThreadPoolExecutor(max_workers=100)
        self.handle = ThreadPoolExecutor(max_workers=100)
        self.log_queue = Queue()  # 使用类变量来存储日志队列
        self.process = None  # 存储子进程的引用
        self.thread = None  # 存储读取日志的线程引用

    def get_server_player(self, rcon):
        rcon.send('ListPlayers')
        decoded_data = rcon.response_queue.get()
        return decoded_data

    def request_steam(self, id):
        try:
            playtime_response = requests.get(
                url=f'http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/?key=1B9BD1175C06924BFF4D3BABB5115407&steamid={id}').json()[
                'response']
            personaname = requests.get(
                url=f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=1B9BD1175C06924BFF4D3BABB5115407&steamids={id}').json()[
                'response']['players'][0]['personaname']
            steam_level = requests.get(
                url=f'http://api.steampowered.com/IPlayerService/GetSteamLevel/v1/?key=1B9BD1175C06924BFF4D3BABB5115407&steamid={id}').json()[
                'response']['player_level']
            playtimes = playtime_response.get('games', None)
            player = []
            player.append(personaname)
            player.append(steam_level)
            if playtimes:
                for i in playtimes:
                    # print(i)
                    if i['appid'] == 393380:
                        player.append(int(i['playtime_forever'] / 60))
                        break
            else:
                player.append(None)
            return player
        except Exception:
            return None

    def tail(self):
        """新版日志推送"""
        cmd = ["C:\\Program Files\\Git\\bin\\bash.exe"]  # 请确认bash.exe的实际路径

        # 启动子进程的函数
        def start_process():
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding='utf-8')
            tail_cmd = f"tail -f {self.path}\n"
            process.stdin.write(tail_cmd)
            process.stdin.flush()
            print(f"子进程已启动，执行命令: {tail_cmd}")
            return process

        # 如果之前有存储的进程，先终止它
        if self.process:
            self.process.kill()

        self.process = start_process()

        def reader():
            try:
                print("读取线程已启动")
                # 使用 iter 和 readline 读取所有行并缓存到队列中
                for line in iter(self.process.stdout.readline, ''):
                    if line:
                        if 'Vote_Faction' not in line and 'has physics bodies outside of MBP bounds' not in line:
                            # print(f"读取到日志行: {line.strip()}")
                            self.log_queue.put(line)
                        else:
                            pass
            except Exception as e:
                print(f"读取线程异常: {e}")
            finally:
                print("读取线程终止，结束进程")
                self.process.kill()

        # 启动日志读取线程
        self.thread = threading.Thread(target=reader, daemon=True)
        self.thread.start()

    def write(self, ls):

        ip, eosid, steamid, name = ls['ip'], ls['eosid'], ls['steamid'], ls['name']
        player = {steamid: {'ip': ip, 'eosid': eosid, 'name': name}}
        try:
            with open('../Data/JoinPlayers.json', "r", encoding='utf-8') as json_file:
                existing_data = json.load(json_file)
        except FileNotFoundError:
            # 如果文件不存在，则创建一个空的字典
            existing_data = {}
            # 更新字典数据
        for steamid, values in player.items():
            if steamid not in existing_data:
                existing_data[steamid] = values

                # 将更新后的字典写入 JSON 文件
        with open('../Data/JoinPlayers.json', "w", encoding='utf-8') as json_file:
            json.dump(existing_data, json_file, indent=4, ensure_ascii=False)  # indent 参数可选，用于指定缩进的空格数，使输出更易读

    def parse(self, rcon):
        global squad_create
        global outboard_start_time
        global kill_death
        mod = moudel()
        if self.path == None:
            print('未填写日志文件目录，取消跟踪日志')
            return 0
        else:
            self.tail()
            while True:
                line = self.log_queue.get()
                print(f"解析日志行: {line.strip()}")
                wound_json = self.re_.Wound_(line)
                kill_json = self.re_.Kill_(line)
                disconnect_json = self.re_.Disconnect(line)
                error_json = self.re_.errorlog(line)
                soldier_json = self.re_.soldier_(line)
                won_math_json = self.re_.won_match(line)
                connection_json = self.re_.connection(line)
                if connection_json:
                    player = self.request_steam(connection_json['steamid'])
                    if player:
                        connection_json['name'] = player[0]
                    else:
                        connection_json['name'] = '未知'
                    self.write(connection_json)
                    player = {'steamid': connection_json['steamid'], 'eosid': connection_json['eosid']}
                    self.handle.submit(self.pending_connectd, connection_json)
                    self.handle.submit(mod.connection_player, player)
                elif won_math_json:
                    kill_deaths_copy = copy.deepcopy(kill_death)
                    team_players_copy = copy.deepcopy(team_players)
                    mod.record_stats(won_math_json['map'], won_math_json['team'], won_math_json['tickets'],
                                     kill_deaths_copy, team_players_copy)
                    squad_create = {}
                    outboard_start_time = {}
                    kill_death = []
                    self.remove_teamchange_log()
                    ticks = won_math_json['tickets']
                    print('本次对局结束,票差', ticks)
                    if int(ticks) > self.RandomTeamTicks:
                        self.handle.submit(mod.random_player, rcon)
                elif wound_json != 0:
                    self.handle.submit(mod.killWarnHandle, wound_json, rcon)
                elif kill_json != 0:
                    self.handle.submit(self.rcords_player_kd, kill_json)
                elif disconnect_json != 0:
                    self.handle.submit(mod.disconnection_player, disconnect_json['eosid'])
                elif error_json != 0:
                    self.handle.submit(mod.passive_anti_cheating, error_json, rcon)
                elif soldier_json:
                    self.handle.submit(self.record_soldier_id, soldier_json)
                    self.handle.submit(mod.welcome_user, soldier_json, rcon)
                else:
                    pass
                # if connection_json:
                #     player = self.request_steam(connection_json['steamid'])
                #     if player:
                #         connection_json['name'] = player[0]
                #         self.write(connection_json)
                #     else:
                #         connection_json['name'] = '未知'
                #         self.write(connection_json)
                #     player = {
                #         'steamid': connection_json['steamid'],
                #         'eosid': connection_json['eosid']
                #     }
                #     threading.Thread(target=self.pending_connectd, args=(connection_json,)).start()
                #     threading.Thread(target=mod.connection_player, args=(player,)).start()
                # elif won_math_json:
                #     kill_deaths_copy = copy.deepcopy(kill_death)
                #     team_players_copy = copy.deepcopy(team_players)
                #     mod.record_stats(won_math_json['map'], won_math_json['team'], won_math_json['tickets'], kill_deaths_copy, team_players_copy)
                #     squad_create = {}
                #     outboard_start_time = {}
                #     kill_death = []
                #     self.remove_teamchange_log()
                #     ticks = won_math_json['tickets']
                #     print('本次对局结束,票差', ticks)
                #     if int(ticks) > self.RandomTeamTicks:
                #         threading.Thread(target=mod.random_player, args=(rcon,)).start()
                # elif wound_json != 0:
                #     threading.Thread(target=mod.killWarnHandle, args=(wound_json, rcon)).start()
                # elif kill_json != 0:
                #     threading.Thread(target=self.rcords_player_kd, args=(kill_json,)).start()
                # elif disconnect_json != 0:
                #     threading.Thread(target=mod.disconnection_player, args=(disconnect_json['eosid'],)).start()
                # elif error_json != 0:
                #     threading.Thread(target=mod.passive_anti_cheating, args=(error_json, rcon)).start()
                # elif soldier_json:
                #     threading.Thread(target=self.record_soldier_id, args=(soldier_json,)).start()
                #     threading.Thread(target=mod.welcome_user, args=(soldier_json, rcon)).start()
                # else:
                #     pass

    def WritKillWarncfg(self, data):
        steamid = data
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 读取配置文件
        config = configparser.ConfigParser()
        config.read('../Data/KillWarncfg.ini', encoding='utf-8')
        # 写入数据
        try:
            rawtime = config[steamid]['time']

            rawtime = datetime.datetime.strptime(rawtime, "%Y-%m-%d %H:%M:%S")
            if datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S") < rawtime:
                newtime = rawtime + datetime.timedelta(hours=1)
            else:
                newtime = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=1)
            # 设置新的值
            config.set(steamid, 'time', str(newtime))
            with config_lock:
                with open('../Data/KillWarncfg.ini', 'w', encoding='utf-8') as f:
                    config.write(f)
        except KeyError:
            t = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=1)
            # 写入新section
            config[steamid] = {
                'time': str(t)
            }
            with config_lock:
                with open('../Data/KillWarncfg.ini', 'w', encoding='utf-8') as f:
                    config.write(f)

    def read_killwarn_cfg(self, steamid):
        config = configparser.ConfigParser()
        config.read('../Data/KillWarncfg.ini', encoding='utf-8')
        try:
            t = config[steamid]['time']
            return t
        except KeyError:
            return 0

    def remove_killwarn_section(self, steamid):
        config = configparser.ConfigParser()
        try:
            config.read('../Data/KillWarncfg.ini', encoding='utf-8')
            config.remove_section(steamid)
            with config_lock:
                with open('../Data/KillWarncfg.ini', 'w', encoding='utf-8') as f:
                    config.write(f)
        except Exception as e:
            print('删除击杀提示记录报错', e)

    def read_teamchange_log(self, data):
        config = configparser.ConfigParser()
        try:
            config.read('../Data/teamchange.ini', encoding='utf-8')
            number = config[data]['number']
            return int(number)
        except:
            return 0

    def write_teamchange_log(self, data):
        config = configparser.ConfigParser()
        try:
            newnumber = self.read_teamchange_log(data) + 1

            config.read('../Data/teamchange.ini')

            # 检查给定的节是否存在，如果不存在，则创建一个新的节
            if not config.has_section(data):
                config.add_section(data)

            config.set(data, 'number', str(newnumber))

            with open('../Data/teamchange.ini', 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        except Exception as e:
            print(e)

    def remove_teamchange_log(self):
        file_path = '../Data/teamchange.ini'
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"删除 {file_path} 时出错: {e}")
        else:
            pass

    def read_sign(self, steam_id):
        # 建立数据库连接
        if self.DataPath == 'None':
            path = '../Data/sign.db'
        else:
            path = self.DataPath
        connection = sqlite3.connect(path)
        # 获取游标
        cursor = connection.cursor()
        query = "SELECT number, sign_date FROM Sign WHERE steam_id = ?"
        cursor.execute(query, (steam_id,))
        result = cursor.fetchone()
        # print(result)
        if result:
            return result[1], result[0]
        else:
            return 0, 0

    def updatePoints(self, steamid, new_points):
        cursor = None
        connection = None
        try:
            # 建立数据库连接
            if self.DataPath == 'None':
                path = '../Data/sign.db'
            else:
                path = self.DataPath
            connection = sqlite3.connect(path)
            # 获取游标
            cursor = connection.cursor()

            # 执行更新数据库的操作
            update_query = "UPDATE Sign SET number = ? WHERE steam_id = ?"
            cursor.execute(update_query, (new_points, steamid))

            # 提交事务
            connection.commit()

        except sqlite3.Error as e:
            print("数据库更新出错:", e)

        finally:
            # 关闭游标和数据库连接
            cursor.close()
            connection.close()

    def rcords_squad_creat(self, data, steamid):
        global squad_create

        # 将队伍信息存储为一个包含 'message' 键的字典
        squad_info = {'message': data}

        # 直接将队伍信息存储到对应的steamid键中，覆盖之前的队伍信息
        squad_create[steamid] = squad_info

    def read_squad_creat(self, steamid):
        global squad_create
        try:
            message = squad_create[steamid]['message']
        except:
            message = None
        return message

    def rcords_player_kd(self, kill_json):
        global kill_death
        killer_steamid = kill_json['actor']
        victim_name = kill_json['death']
        wound = kill_json.get('wound', False)

        victim_steamid = 'nullptr'
        victim_team = 0
        killer_team = 0

        if victim_name != 'nullptr':
            for team_id, players in team_players.items():
                for player in players:
                    if player['name'] == victim_name:
                        victim_steamid = player['steamid']
                        victim_team = player['team']
                    if player['steamid'] == killer_steamid:
                        killer_team = player['team']
        killer_data = {
            'steamid': killer_steamid,
            'kill': 1,
            'wound': 1 if wound else 0,
            'death': 0
        }

        victim_data = {
            'steamid': victim_steamid,
            'kill': 0,
            'wound': 0,
            'death': 1
        }

        if wound is False:  # 检查是否是受伤，不是受伤则是死亡
            for i in kill_death:
                if i['steamid'] == killer_steamid and victim_team != killer_team:
                    i['kill'] += 1
                    i['wound'] += 1 if wound else 0
                elif i['steamid'] == victim_steamid:
                    i['death'] += 1
                    break
            else:
                kill_death.append(killer_data)
                if victim_name != 'nullptr':
                    kill_death.append(victim_data)
        else:
            # 受伤时记录受伤
            for i in kill_death:
                if i['steamid'] == killer_steamid:
                    i['wound'] += 1
                    break
            else:
                kill_death.append(killer_data)

    def read_player_kd(self, steamid):
        for i in kill_death:
            if i['steamid'] == steamid:
                data = {
                    'kill': i['kill'],
                    'wound': i['wound'],
                    'death': i['death']
                }
                return data
        else:
            return None

    def record_soldier_id(self, soldier_json):
        global soldier_id
        soldier = soldier_json['soldierid']
        steamid = soldier_json['steamid']

        data = {'steamid': steamid}

        soldier_id[soldier] = data

    def read_soldier_steam(self, soldier):
        global soldier_id
        try:
            steamid = soldier_id[soldier]['steamid']
        except Exception as e:
            print('读取士兵steamid出错', e)
            steamid = None
        return steamid

    def pending_connectd(self,connection_json):
        name = connection_json['name']
        pending_user_connected[name] = connection_json['steamid']

class moudel:
    def __init__(self):
        self.base = Base()
        self.re_ = re_str()
        self.PointName = Readyaml('PointName')  # 积分名称
        self.CreateSquadMinHours = Readyaml('CreateSquadMinHours')  # 最低建队时长
        self.UndisclosedInformationHandle = Readyaml('UndisclosedInformationHandle')  # 未公开信息建队处理
        self.TeamChangeNum = Readyaml('TeamChange')  # 跳边消耗积分
        self.GameHoursGetNum = Readyaml('GameHoursGetNum')  # 游戏时长查询消耗积分
        self.PrizeDrawPoint = Readyaml('PrizeDrawPoint')  # 抽奖花费
        self.DataPath = Readyaml('DataPath')  # 数据目录
        self.TeamChangeNumber = Readyaml('TeamChangeNumber')  # 跳边花费
        self.KillWarnNumber = Readyaml('KillWarnNumber')  # 击杀提示花费
        self.ConstraintCount = Readyaml('ConstraintCount')  # 平很人数
        self.kdNumber = Readyaml('kdNumber')

    def draw_prize(self, chat_json, rcon):
        steamID = chat_json['steamID']
        name = chat_json['name']
        sign_data = self.base.read_sign(steamID)

        if sign_data != 0 and sign_data[1] != 0:
            if int(sign_data[1]) < self.PrizeDrawPoint:
                threading.Thread(target=rcon.send,
                                 args=(f'AdminBroadcast {name} 您的{self.PointName}不足，嘎嘎哭',)).start()
            else:
                random_number = 1

                raw_number = int(sign_data[1]) - self.PrizeDrawPoint
                new_number = raw_number + random_number
                threading.Thread(target=rcon.send, args=(
                f'AdminBroadcast 嘎噶噶，{name} 本次消耗{self.PrizeDrawPoint}{self.PointName}，获得 {random_number}{self.PointName}，剩余{self.PointName}: {new_number}',)).start()
                self.base.updatePoints(steamID, new_number)
        elif sign_data[1] == 0:
            threading.Thread(target=rcon.send,
                             args=(f'AdminBroadcast {name} 你还未拥有{self.PointName}，请先签到后再噶',)).start()

    def sign(self, chat_json, rcon):
        # 建立数据库连接
        if self.DataPath == 'None':
            path = '../Data/sign.db'
        else:
            path = self.DataPath
        connection = sqlite3.connect(path)
        # 获取游标
        cursor = connection.cursor()
        name = chat_json['name']
        steam_id = chat_json['steamID']

        current_time = datetime.datetime.now().time()
        early_morning_start = datetime.datetime.strptime('23:00', '%H:%M').time()
        early_morning_end = datetime.datetime.strptime('02:00', '%H:%M').time()

        morning_start = datetime.datetime.strptime('8:00', '%H:%M').time()
        morning_end = datetime.datetime.strptime('10:00', '%H:%M').time()

        night_start = datetime.datetime.strptime('21:00', '%H:%M').time()
        night_end = datetime.datetime.strptime('23:00', '%H:%M').time()

        # 判断当前时间是否在指定的时间段内
        if early_morning_end < early_morning_start:
            # 跨越午夜的情况，结束时间小于开始时间
            early_morning = (early_morning_start <= current_time <= datetime.time(23, 59, 59) or
                             datetime.time(0, 0, 0) <= current_time <= early_morning_end)
        else:
            # 不跨越午夜的情况
            early_morning = early_morning_start <= current_time <= early_morning_end
        morning = morning_start <= current_time <= morning_end
        night = night_start <= current_time <= night_end

        number = random.randint(5, 15)

        today = datetime.datetime.now().strftime('%m/%d')

        day, raw_num = self.base.read_sign(steam_id)

        if day == today:
            threading.Thread(target=rcon.send, args=(f'AdminWarn {steam_id} 今日已签到，请勿重复签到',)).start()
        else:
            if day == 0:  # 没有记录
                insert_query = "INSERT INTO Sign (steam_id, name, number, sign_date) VALUES (?, ?, ?, ?)"
                if early_morning is True:
                    number = number * 2
                    message = f'AdminBroadcast 凌晨了，恭喜玩家{name}签到成功，获得200%凌晨签到加成，{self.PointName}+{number} 剩余{self.PointName}: {number}'
                elif morning is True:
                    number = number * 1.5
                    message = f'AdminBroadcast 早上好{name}，恭喜你签到成功，获得150%早间签到加成，{self.PointName}+{number} 剩余{self.PointName}: {number}'
                elif night is True:
                    number = number * 1.5
                    message = f'AdminBroadcast 晚上好{name}，恭喜你签到成功，获得150%夜间签到加成，{self.PointName}+{number} 剩余{self.PointName}: {number}'
                else:
                    message = f'AdminBroadcast 恭喜玩家{name}签到成功，{self.PointName}+{number} 剩余{self.PointName}: {number}'
                cursor.execute(insert_query, (steam_id, name, number, today))
                connection.commit()
                threading.Thread(target=rcon.send, args=(message,)).start()
            else:  # 今日未签到
                if early_morning is True:
                    sum_number = (raw_num + number * 2)
                    message = f'AdminBroadcast 凌晨了，新的一天开始了！恭喜玩家{name}签到成功，获得200%凌晨签到加成，{self.PointName}+{number * 2} 剩余{self.PointName}: {sum_number}'
                elif morning is True:
                    sum_number = (raw_num + number * 1.5)
                    message = f'AdminBroadcast 早上好{name}，恭喜你签到成功，获得150%早间签到加成，{self.PointName}+{number * 1.5} 剩余{self.PointName}: {sum_number}'
                elif night is True:
                    sum_number = (raw_num + number * 1.5)
                    message = f'AdminBroadcast 晚上好{name}，恭喜你签到成功，获得150%夜间签到加成，{self.PointName}+{number * 1.5} 剩余{self.PointName}: {sum_number}'
                else:
                    sum_number = (raw_num + number)
                    message = f'AdminBroadcast 恭喜玩家{name}签到成功，{self.PointName}+{number} 剩余{self.PointName}: {sum_number}'
                # 更新用户点数和签到日期
                update_query = "UPDATE Sign SET number = ?, sign_date = ? WHERE steam_id = ?"
                cursor.execute(update_query, (sum_number, today, steam_id))
                connection.commit()
                threading.Thread(target=rcon.send, args=(message,)).start()

    def gamehours(self, chat_json, rcon):
        steamid = chat_json['steamID']
        name = chat_json['name']
        sign_data = self.base.read_sign(steamid)
        hours = self.base.request_steam(steamid)
        if hours:
            res = hours[2]
            if sign_data != 0 and sign_data[1] != 0:
                if sign_data[1] < self.GameHoursGetNum:
                    threading.Thread(target=rcon.send, args=(
                    f'AdminBroadcast {name} {self.PointName}不足，无法使用游戏时长查询功能',)).start()
                else:

                    number = sign_data[1] - self.GameHoursGetNum
                    if res != None:
                        rcon.send(
                            f'AdminBroadcast {name} Squad游玩时长 {res} 小时，查询消耗 {self.GameHoursGetNum}{self.PointName}，剩余:{number}{self.PointName}')
                    else:
                        rcon.send(
                            f'AdminBroadcast {name} 未公开资料，查询消耗 {self.GameHoursGetNum}{self.PointName}，剩余:{number}{self.PointName}')
                    self.base.updatePoints(steamid, number)
            elif sign_data[1] == 0:
                rcon.send(f'AdminBroadcast {name} 你还未拥有{self.PointName}，请先签到后再使用游戏时长查询功能')
        else:
            rcon.send(f'AdminBroadcast {name} 服务器出错，查询失败，{self.PointName}已返还')

    def Sqcreate(self, SqCreated_json, rcon):
        Ruls = Readyaml('Ruls')
        name = SqCreated_json['name']
        team = SqCreated_json['team']
        id = SqCreated_json['id']
        steamid = SqCreated_json['steamid']
        squad = SqCreated_json['squad']
        t = datetime.datetime.now().strftime('%m/%d %H:%M:%S.%f"')[:-3]
        hour = self.base.request_steam(steamid)
        if hour:
            hours = hour[2]
            if hours is None:
                hours = None
            else:
                hours = hours

            if hours is None:
                if self.UndisclosedInformationHandle == True:
                    threading.Thread(target=rcon.send, args=(
                    f'AdminWarn {steamid} 服务器禁止未公开资料玩家建队，自动移除小队',)).start()
                    threading.Thread(target=rcon.send, args=(f'AdminRemovePlayerFromSquad {steamid}',)).start()
                else:
                    threading.Thread(target=rcon.send, args=(
                    f'AdminBroadcast {t} {team} | {name} 创建{id}队 {squad} | 资料未公开',)).start()
                    threading.Thread(target=rcon.send, args=(
                    f'AdminWarn {steamid} 请公开游戏资料，如因未公开资料造成的误封，后果请自行承担',)).start()
            elif int(float(hours)) < self.CreateSquadMinHours:
                if steamid == '76561198191782061' or steamid == '76561199438014006' or steamid == '76561199536279564' or steamid =='76561199034977102':  # 白名单
                    pass
                else:
                    rcon.send(f'AdminRemovePlayerFromSquad {name}')
                    threading.Thread(target=rcon.send, args=(
                    f'AdminWarn {steamid} 你的游戏时长不满足服务器最低 {self.CreateSquadMinHours} 小时建队时长，自动移除小队',)).start()
            else:
                if steamid == '76561198191782061' or steamid == '76561199438014006' or steamid == '76561199536279564' or steamid=='76561199034977102':  # 白名单
                    pass
                else:
                    for rule in Ruls:
                        for sqname in Ruls[rule]['name'].split(' '):
                            if sqname in squad.lower():
                                if int(Ruls[rule]['minhours']) > int(float(hours)):
                                    threading.Thread(target=rcon.send,
                                                     args=(f'AdminRemovePlayerFromSquad {steamid}',)).start()
                                    threading.Thread(target=rcon.send, args=(
                                    f'AdminWarn {steamid} 你的游戏时长不满足 {squad} 最低建队时长，自动移除小队',)).start()
                                    return 0
                    message = f'AdminBroadcast {t} {team} | {name} 创建{id}队 {squad} | 游戏时长: {hours}小时'
                    threading.Thread(target=rcon.send, args=(message,)).start()
                    threading.Thread(target=self.base.rcords_squad_creat, args=(message, steamid,)).start()
        else:
            message = f'AdminBroadcast {t} {team} | {name} 创建{id}队 {squad}'
            threading.Thread(target=rcon.send, args=(message,)).start()
            threading.Thread(target=self.base.rcords_squad_creat, args=(message, steamid,)).start()

    def ChangeTeam(self, chat_json, rcon):
        global team_players
        name = chat_json['name']
        steamID = chat_json['steamID']
        sign_data = self.base.read_sign(steamID)
        count = self.base.read_teamchange_log(steamID)
        if steamID == '76561199476003954':
            print(team_players)
        if sign_data != 0 and sign_data[1] != 0:
            if sign_data[1] < self.TeamChangeNum:
                threading.Thread(target=rcon.send,
                                 args=(f'AdminWarn {steamID} {self.PointName}不足，无法使用跳边功能',)).start()
            else:
                if count < self.TeamChangeNumber:
                    # 计算每个队伍的人数
                    team_size = {}
                    for team_id, players in team_players.items():
                        team_size[team_id] = len(players)
                    team_ids = list(team_size.keys())
                    difference = 0
                    if len(team_ids) == 2:
                        team1_id, team2_id = team_ids
                        difference = abs(team_size[team1_id] - team_size[team2_id])
                    else:
                        pass
                    print('双方人数差距', difference)
                    if difference > self.ConstraintCount:
                        rcon.send(f'AdminWarn {steamID} 双方人数不平衡，无法跳边')
                    else:
                        rcon.send(f'AdminForceTeamChange {steamID}')
                        number = int(sign_data[1]) - self.TeamChangeNum
                        rcon.send(
                            f'AdminWarn {steamID} 跳边成功，消耗{self.TeamChangeNum}{self.PointName}，剩余{self.PointName}: {number}')
                        self.base.write_teamchange_log(steamID)
                        self.base.updatePoints(steamID, number)
                else:
                    threading.Thread(target=rcon.send,
                                     args=(f'AdminWarn {steamID} 跳边次数已用尽，无法使用跳边功能',)).start()
        elif sign_data[1] == 0:
            rcon.send(f'AdminWarn {steamID} 你还未拥有{self.PointName}，请先签到后再使用跳边功能')

    def SqLegal(self, data, rcon):
        Ruls = Readyaml('Ruls')
        try:
            if data:
                for i in data:
                    name, size, locked, ctorname, steamid = i[1], i[2], i[3], i[4], i[6]
                    if re.findall(r'(小队 \d)', name) != []:
                        if locked == 'True':

                            threading.Thread(target=rcon.send, args=(
                            f'AdminWarn {steamid} 步兵队不支持锁队，请打开队锁，否则自动解散小队。',)).start()
                        else:
                            pass
                    else:
                        for rule in Ruls:
                            for sqname in Ruls[rule]['name'].split(' '):
                                if sqname in name.lower():
                                    if Ruls[rule]['lock'] != 'None':
                                        threading.Thread(target=rcon.send, args=(
                                            f'AdminWarn {steamid} 检测到你的队伍 {name} 已锁队，请打开队锁，否则将解散小队。',)).start()
                                    if int(Ruls[rule]['size']) < int(size):
                                        threading.Thread(target=rcon.send, args=(
                                            f'AdminWarn {steamid} 检测到你的队伍 {name} 已超员，请立即减员，否则将解散小队。',)).start()
            else:
                pass
        except Exception as e:
            print(e)

    def QuIntegral(self, chat_json, rcon):
        name = chat_json['name']
        steamID = chat_json['steamID']
        day, rawnum = self.base.read_sign(steamID)
        if day != 0:
            threading.Thread(target=rcon.send, args=(f'AdminBroadcast {name} 剩余{self.PointName}: {rawnum}',)).start()
        else:
            threading.Thread(target=rcon.send,
                             args=(f'AdminBroadcast {name} 还未拥有{self.PointName}，请先签到获取',)).start()

    def WarmUp(self, rcon):
        threading.Thread(target=rcon.send, args=(f'AdminBroadcast 服务器已更改为暖服模式',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminDisableVehicleClaiming 1',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminNoRespawnTimer 1',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminForceAllRoleAvailability 1',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminDisableVehicleKitRequirement 1',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminDisableVehicleTeamRequiremen 1',)).start()

    def unWarnUp(self, rcon):
        threading.Thread(target=rcon.send, args=(f'AdminBroadcast 服务器结束暖服',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminDisableVehicleClaiming 0',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminNoRespawnTimer 0',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminForceAllRoleAvailability 0',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminDisableVehicleKitRequirement 0',)).start()
        threading.Thread(target=rcon.send, args=(f'AdminDisableVehicleTeamRequiremen 0',)).start()

    def TkAdminBroadcast(self, tk_json, rcon):
        tk_message = Readyaml('TeamKillMessage')
        player1 = tk_json['player1']
        player2 = tk_json['player2']
        replaced_string = re.sub(r'player1', player1, tk_message)
        replaced_string = re.sub(r'player2', player2, replaced_string)
        threading.Thread(target=rcon.send, args=(f'AdminBroadcast {replaced_string}',)).start()

    def KillWarn(self, chat_json, rcon):
        steamid = chat_json['steamID']
        day, rawnum = self.base.read_sign(steamid)
        if day != 0:
            if int(rawnum) >= self.KillWarnNumber:
                number = int(rawnum) - self.KillWarnNumber
                threading.Thread(target=rcon.send, args=(
                    f'AdminWarn {steamid} 兑换击杀提示成功，剩余{number}{self.PointName}',)).start()
                self.base.WritKillWarncfg(steamid)
                self.base.updatePoints(steamid, number)
            else:
                threading.Thread(target=rcon.send, args=(
                f'AdminWarn {steamid} 兑换失败，{self.PointName}不足{self.KillWarnNumber}，请先获取{self.PointName}后再兑换',)).start()
        else:
            threading.Thread(target=rcon.send,
                             args=(f'AdminWarn {steamid} 兑换失败，{self.PointName}不足，请先获取{self.PointName}后再兑换',)).start()

    def killWarnHandle(self, wound_json, rcon):
        actor = wound_json['actor']
        death = wound_json['death']
        rawt = self.base.read_killwarn_cfg(actor)
        t = datetime.datetime.now()
        # 获取击杀者和死者的队伍信息
        actor_team = None
        death_team = None
        death_steamid = None
        actor_name = None
        for team_id, players in team_players.items():
            for player in players:
                if player['steamid'] == actor:
                    actor_team = player['team']
                    actor_name = player['name'].replace(' ','')
                if player['name'] == death:
                    death_team = player['team']
                    death_steamid = player['steamid']
        if actor_team != death_team:
            threading.Thread(target=self.base.rcords_player_kd, args=(wound_json,)).start()
            if death != 'nullptr':
                # 被击倒提示
                # threading.Thread(target=rcon.send, args=(f'AdminWarn {death_steamid} 被玩家 {actor_name} 击倒',)).start()
                if rawt != 0 and datetime.datetime.strptime(rawt, "%Y-%m-%d %H:%M:%S") >= t:
                    threading.Thread(target=rcon.send, args=(f'AdminWarn {actor} 击倒敌人{death}',)).start()
                elif rawt != 0 and datetime.datetime.strptime(rawt, "%Y-%m-%d %H:%M:%S") <= t:
                    threading.Thread(target=rcon.send, args=(f'AdminWarn {actor} 击杀提示已失效',)).start()
                    self.base.remove_killwarn_section(actor)
            else:
                pass
        else:
            pass

    def ClearPlayer(self, playerlist, send):
        current_time = time.time()
        lock = threading.Lock()
        if playerlist != 0:
            if outboard_check == 1:
                for player in playerlist:
                    player_id = player['id']
                    if player['squad'] == 'N/A':
                        if player_id not in outboard_start_time:
                            with lock:
                                outboard_start_time[player_id] = {
                                    'current_time': current_time,
                                    'eosid': player['eosid']
                                }
                        else:
                            with lock:
                                idle_time = current_time - outboard_start_time[player_id]['current_time']
                                # 如果挂机时长超过了10分钟，清理玩家
                                if idle_time > 10 * 60:  # 10分钟 = 10 * 60 秒
                                    # 清理玩家的逻辑
                                    print('清除玩家', player_id)
                                    del outboard_start_time[player_id]
                                    threading.Thread(target=send,
                                                     args=(f'AdminKick {player_id} 空闲时间过长，自动踢出',)).start()
                    else:
                        # 玩家已经加入小队
                        with lock:
                            if player_id in outboard_start_time:
                                del outboard_start_time[player_id]

    def TeamPlayerCountStat(self, list_):
        global team_players

        if list_:
            # 创建一个集合用于存储当前传入的玩家的 steamid
            current_steamids = {player['id'] for player in list_}

            # 使用一个临时字典来构建新的 team_players
            new_team_players = {}

            # 遍历 list_ 并更新玩家数据
            for player in list_:
                steamid = player['id']
                playername = player['name']
                team = player['team']
                eosid = player['eosid']
                squad = player['squad']
                player_data = {
                    'steamid': steamid,
                    'eosid': eosid,
                    'team': team,
                    'squad': squad,
                    'name': playername
                }
                team_id = team

                # 如果 team_id 不在 new_team_players 中，则用一个空列表初始化它
                if team_id not in new_team_players:
                    new_team_players[team_id] = []

                new_team_players[team_id].append(player_data)

            # 检查并删除不在当前传入列表中的玩家
            for team_id, existing_players in team_players.items():
                team_players[team_id] = [p for p in existing_players if p['steamid'] in current_steamids]

            # 更新全局的 team_players
            team_players = new_team_players


    def remove_player(self, disconnect_json):
        global team_players
        eosid = disconnect_json['eosid']
        print('玩家退出', eosid)
        deletion_in_progress.set()  # 标志删除操作开始
        with Player_Lock:
            try:
                # 遍历 team_players 中的所有队伍
                for team_id, players in team_players.items():
                    # 使用列表推导式过滤出不包含该玩家的新列表
                    updated_players = [player for player in players if player['eosid'] != eosid]
                    # 更新 team_players 中的队伍数据
                    team_players[team_id] = updated_players

                # 在玩家退出后，调用 TeamPlayerCountStat 函数更新玩家人数
                # threading.Thread(target=self.TeamPlayerCountStat,args=([],)).start()
            except Exception as e:
                print('删除玩家出错:', e)
            finally:
                deletion_in_progress.clear()  # 标志删除操作结束
                Player_Condition.notify_all()  # 通知所有等待的线程
                remaining_player = len(team_players['1']) + len(team_players['2'])
                print('剩余玩家', remaining_player)

    def squadcreate_Broadcast(self, chat_json, rcon):
        steamid = chat_json['steamID']
        message = self.base.read_squad_creat(steamid)
        if message:
            threading.Thread(target=rcon.send, args=(message,)).start()
        else:
            threading.Thread(target=rcon.send,
                             args=(f'AdminWarn {steamid} 你还未拥有小队！\n先创建队伍后再查询建队信息！',)).start()

    def kill_death_warn(self, chat_json, rcon):
        steamid = chat_json['steamID']
        data = self.base.read_player_kd(steamid)
        sign_data = self.base.read_sign(steamid)
        if sign_data != 0 and sign_data[1] != 0:
            if sign_data[1] < self.TeamChangeNum:
                threading.Thread(target=rcon.send,
                                 args=(f'AdminWarn {steamid} {self.PointName}不足，无法查询KD，要获取{self.PointName}请添加QQ群',)).start()
            else:
                if data:
                    kill = data['kill']
                    wound = data['wound']
                    death = data['death']
                    threading.Thread(target=rcon.send,
                                     args=(f'AdminWarn {steamid} 击倒:{wound}人 击杀:{kill}人 死亡{death}次',)).start()
                else:
                    threading.Thread(target=rcon.send, args=(f'AdminWarn {steamid} 击倒:0人 击杀:0人 死亡:0次',)).start()
                number = sign_data[1] - self.kdNumber
                self.base.updatePoints(steamid, number)

    def passive_anti_cheating(self, error_json, rcon):
        soldier = error_json['soldierid']
        currenttime = float(error_json['currenttime'])
        expiredtime = float(error_json['expiredtime'])
        difference = abs(currenttime - expiredtime)
        if difference > 10:
            steamid = self.base.read_soldier_steam(soldier)
            if steamid:
                # 获取当前时间
                now = datetime.datetime.now()

                # 加上2个小时
                end = now + datetime.timedelta(minutes=30)

                # 格式化新时间
                now_time = now.strftime('%m/%d %H:%M:%S')
                end_time = end.strftime('%m/%d %H:%M:%S')
                threading.Thread(target=rcon.send, args=(f'AdminBan {steamid} 0 [青花盾-Anti-Cheat]检测封禁，处理时间:{now_time}，申诉QQ群：834334294，申述截止时间{end_time}，Steamid64:{steamid}',)).start()
        else:
            pass

    def Custom_random(self, chat_json, rcon):
        name = chat_json['name']
        with open('../Data/random_list.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            num_lines = len(lines)
            number = random.randint(0, num_lines - 1)
        threading.Thread(target=rcon.send, args=(f'AdminBroadcast {name}你的老婆是 {lines[number]}',)).start()

    def extract_op(self, rcon):
        power = Readyaml('AdminPower').split(' ')
        admin_list = self.re_.AdminPlayer()
        # 用于存储管理员玩家的信息
        admin_info = []
        # 读取管理员信息的列表
        admin_info_list = []
        for team_id, players in team_players.items():
            # 遍历当前队伍的所有玩家
            for player in players:
                # 获取玩家的 steamid 属性
                steamid = player['steamid']

                # 检查当前玩家的 steamid 是否在 admin_list 中
                for admin_player in admin_list:
                    if steamid == admin_player['steamid'] and admin_player['power'] in power:
                        # 如果是管理员玩家，则将其权限信息存储在 admin_teams 字典中
                        admin_info.append({
                            'name': player['name'],
                            'team': player['team'],
                            'squad': player.get('squad')  # 获取玩家的小队信息，如果不存在则为 None
                        })
                        threading.Thread(target=rcon.send,
                                         args=(f'AdminWarn {steamid} 有玩家正在呼叫OP，请及时处理',)).start()
                        break
            # 遍历管理员信息列表，并限制只取前5个管理员信息
        if not admin_info:
            rcon.send("AdminBroadcast 当前无OP在线")
            return
        for i, admin in enumerate(admin_info):
            if i >= 3:
                break
            # 将管理员信息格式化为字符串，例如：steamid:team:squad
            # chardet.detect(admin['name'].encode('utf-8'))
            admin_info_str = f"阵营：{admin['team']} 队伍：{admin['squad']} 名称:{admin['name']}"
            admin_info_list.append(admin_info_str)

            # 将多个管理员信息拼接成一个字符串，以逗号分隔
            admin_info_combined = "\n".join(admin_info_list)
        threading.Thread(target=rcon.send,
                         args=(f'AdminBroadcast 当前共计{len(admin_info)}位OP在线\n{admin_info_combined}',)).start()

    def random_player(self, rcon):
        for team_id, players in team_players.items():
            # 从每个团队中选取前20个玩家
            selected_players = players[-20:] if len(players) >= 20 else players
            if len(selected_players) < 20:
                break
            for player in selected_players:
                # 启动一个新的线程来执行AdminForceTeamChange命令
                threading.Thread(target=rcon.send, args=(f'AdminForceTeamChange {player["steamid"]}',)).start()

    def record_stats(self, map, team, tickets, kill_deaths_copy, team_players_copy):
        # team_name = team_name.replace('中国人民解放军','PLA')
        timestamp = time.time()
        url = 'http://150.138.84.157:3000/sqlite/write'
        for player in kill_deaths_copy:
            for team_id, players in team_players_copy.items():
                for i in players:
                    win = False
                    if player['steamid'] == i['steamid']:
                        if i['team'] == str(team):
                            win = True
                        player['history'] = {
                            'timestamp':timestamp,
                            'wound':player['wound'],
                            'kills': player['kill'],
                            'deaths': player['death'],
                            'map':map,
                            'win':win,
                            'tickets':tickets
                        }
        # print(kill_deaths_copy)
        requests.post(url=url,json=kill_deaths_copy)

    # 玩家加入
    def connection_player(self,player):
        star_time = time.time()
        eosid = player['eosid']
        steamid = player['steamid']
        game_time_stats[eosid] = {
            'steamid':steamid,
            'startTime':star_time
        }
        # print(game_time_stats)

    # 玩家退出
    def disconnection_player(self,eosid):
        try:
            end_time = time.time()
            steamid = None
            for player in game_time_stats:
                if player == eosid:
                    steamid = game_time_stats[eosid]['steamid']

            start_time = game_time_stats[eosid]['startTime']
            time_difference = end_time - start_time

            min = time_difference // 60
            # print('玩家退出')
            if min < 1:
                pass
            else:
                end_json = {
                    'steamid':steamid,
                    'timeStats':min
                }
                del game_time_stats[eosid]
                url = 'http://150.138.84.157:3000/sqlite/gameTime'
                requests.post(url=url, json=end_json)
        except KeyError:
            print('玩家退出错误，未找到加入记录')
        except Exception as e:
            print('玩家退出错误',e)

    def send_stats(self,chat_json,rcon):
        steamid = chat_json['steamID']
        name = chat_json['name']
        try:
            data = requests.get(f'http://150.138.84.157:3000/player/{steamid}').json()
            # 将history字段从字符串转换为数组
            data['history'] = json.loads(data['history'])
            wins = 0
            count = 0
            for i in data['history']:
                count += 1
                if i['win']:
                    wins += 1
            message = f"AdminBroadcast {name}在青花瓷游玩 {data['playTime']}分钟 总击杀：{data['kills']} 总场次：{count} 胜场：{wins} ，获取更详细的记录请前往青花瓷生涯信息查询网站 http://api.squadqhc.cn/"
            threading.Thread(target=rcon.send, args=(message,)).start()
        except KeyError:
            threading.Thread(target=rcon.send, args=(f'AdminWarn {steamid} 无有效游戏记录，请前往api.squadqhc.cn查看详细',)).start()

    def welcome_user(self,soldier_json,rcon):
        name = soldier_json['name']
        steamid = pending_user_connected.get(name,None)
        if steamid:
            del pending_user_connected[name]
            message = f'AdminWarn {steamid} {name} 欢迎游玩青花瓷服务器！\n天青色等烟雨，而我在青花瓷等你'
            rcon.send(message)
        else:
            pass


def ServerMessageHandle(rcon):
    t = time.time()
    global flight_start_times
    match = re_str()
    mod = moudel()
    t = str(time.time() - t)
    print(f'服务器Rcon监控线程自检完成 耗时 {t[:4]}ms')
    while True:
        decoded_data = rcon.response_queue.get()
        chat_json = match.chat(decoded_data)
        TeamKill_json = match.TeamKill(decoded_data)
        SqCreated_json = match.SqCreated(decoded_data)
        # 聊天事件
        if chat_json != 0:
            if chat_json['message'] == '签到' or chat_json['message'] == 'qd' or chat_json['message'] == 'QD':
                threading.Thread(target=mod.sign, args=(chat_json, rcon)).start()
            elif chat_json['chat'] == 'ChatAdmin':
                if chat_json['message'] == '@开始暖服':
                    threading.Thread(target=mod.WarmUp, args=(rcon,)).start()
                if chat_json['message'] == '@停止暖服':
                    threading.Thread(target=mod.unWarnUp, args=(rcon,)).start()
                if chat_json['message'] == '@random':
                    threading.Thread(target=mod.random_player, args=(rcon,)).start()
            elif chat_json['message'] == '游戏时长' or chat_json['message'] == 'yxsc':
                threading.Thread(target=mod.gamehours, args=(chat_json, rcon)).start()
            elif chat_json['message'].lower() == 'tb':
                threading.Thread(target=mod.ChangeTeam, args=(chat_json, rcon)).start()
            elif chat_json['message'] == '嘎嘎乐':
                pass
                # threading.Thread(target=mod.ggl, args=(chat_json, rcon)).start()
            elif chat_json['message'] == mod.PointName:
                threading.Thread(target=mod.QuIntegral, args=(chat_json, rcon)).start()
            elif chat_json['message'] == '击杀提示':
                threading.Thread(target=mod.KillWarn, args=(chat_json, rcon)).start()
            elif chat_json['message'] == '建队时间' or chat_json['message'] == 'jd' or chat_json['message'] == 'JD':
                threading.Thread(target=mod.squadcreate_Broadcast, args=(chat_json, rcon)).start()
            elif chat_json['message'].lower() == 'kd':
                threading.Thread(target=mod.kill_death_warn, args=(chat_json, rcon)).start()
            elif chat_json['message'] == '我的老婆':
                threading.Thread(target=mod.Custom_random, args=(chat_json, rcon)).start()
            elif chat_json['message'].lower() == 'op':
                threading.Thread(target=mod.extract_op, args=(rcon,)).start()
            elif chat_json['message'].lower() == 'sy' or chat_json['message'] == '生涯':
                threading.Thread(target=mod.send_stats, args=(chat_json,rcon,)).start()
            else:
                pass
        # 建队事件
        elif SqCreated_json != 0:
            threading.Thread(target=mod.Sqcreate, args=(SqCreated_json, rcon)).start()
        elif TeamKill_json != 0:
            threading.Thread(target=mod.TkAdminBroadcast, args=(TeamKill_json, rcon)).start()
        if 'has possessed' in decoded_data:
            name = decoded_data.split('has')[0].split(']')[1]
            flight_start_times[name] = time.time()
            rcon.send(f'AdminWarn {name} 飞天开始，执法过程中建议录屏留存证据')
        if 'unpossessed' in decoded_data:
            name = decoded_data.split('has')[0].split(']')[1]
            if name in flight_start_times:
                flight_duration = time.time() - flight_start_times[name]
                del flight_start_times[name]  # 删除记录的飞天开始时间
                if flight_duration < 60:
                    rcon.send(f'AdminWarn {name} 飞天结束，本次飞天时长：{flight_duration:.0f} 秒')
                else:
                    minutes = int(flight_duration / 60)
                    seconds = int(flight_duration % 60)
                    rcon.send(f'AdminWarn {name} 飞天结束，本次飞天时长：{minutes} 分 {seconds} 秒')
        # 在这里可以对解码后的数据进行处理


def SquadLegalCheck(rcon):
    t = time.time()

    match = re_str()
    mod = moudel()
    t = str(time.time() - t)
    print(f'队伍监控线程自检完成 耗时 {t[:4]}ms')
    while True:
        server_data = rcon.response_server.get()
        squad_list = match.SqList(server_data)
        if squad_list != []:
            mod.SqLegal(squad_list, rcon)


def AutoClearPlayer(rcon):
    mod = moudel()
    match = re_str()
    while True:
        server_data = rcon.response_server.get()
        playerlist = match.plList(server_data)
        threading.Thread(target=mod.TeamPlayerCountStat, args=(playerlist,)).start()
        threading.Thread(target=mod.ClearPlayer, args=(playerlist, rcon.send)).start()


def PlayerCountCheck():
    t = time.time()
    AutoClearCount = Readyaml('AutoClearCount')
    global outboard_check
    global outboard_start_time
    t = str(time.time() - t)
    print(f'服务器人数监控线程自检完成 耗时 {t[:4]}ms')
    while True:
        try:
            server_player_count = len(team_players['2']) + len(team_players['1'])
        except:
            server_player_count = 0
        if server_player_count < AutoClearCount:
            outboard_start_time = {}
            # print('当前服务器人数',server_player_count,'不执行挂机检测')
            outboard_check = 0
        else:
            outboard_check = 1
        time.sleep(10)


def squad_rcon():
    rcon = RconConnection()
    base = Base()
    ip = Readyaml('ServerIp')
    port = Readyaml('RconPort')
    password = Readyaml('RconPassword')
    rcon.connect(port=port, host=ip, token=password)
    # 服务器信息监控线程
    threading.Thread(target=ServerMessageHandle, args=(rcon,),daemon=True).start()
    # 小队检测线程
    threading.Thread(target=SquadLegalCheck, args=(rcon,),daemon=True).start()
    # 人数检测线程
    threading.Thread(target=PlayerCountCheck).start()

    threading.Thread(target=AutoClearPlayer, args=(rcon,),daemon=True).start()

    # 日志监控线程
    base.parse(rcon)


if __name__ == '__main__':
    print(f'-----程序启动成功-----')
    try:
        squad_rcon()
    except Exception as e:
        print('程序出错：', e)
