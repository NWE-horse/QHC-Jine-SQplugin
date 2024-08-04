# -*- codeing = utf-8 -*-
# @Time : 2024/5/21 12:10
# @Author :Jnine
# @File : read_ini.py
# @Software : PyCharm
import configparser
import datetime
t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
steamid = '1'
# 读取配置文件
def writ():
    config = configparser.ConfigParser()
    config.read('../Data/KillWarncfg.ini', encoding='utf-8')
    try:
        rawtime = config[steamid]['time'].strip('"')

        rawtime = datetime.datetime.strptime(rawtime,"%Y-%m-%d %H:%M:%S")

        newtime = rawtime+datetime.timedelta(hours=1)

        config.set(steamid, 'time', str(newtime))
        with open('../Data/KillWarncfg.ini', 'w', encoding='utf-8') as f:
            config.write(f)
    except KeyError:
        config[steamid] = {
            'time':t
        }
        with open('../Data/KillWarncfg.ini','w' ,encoding='utf-8') as f:
            config.write(f)

def read():
    config = configparser.ConfigParser()
    config.read('../Data/KillWarncfg.ini', encoding='utf-8')
    try:
        t = config[steamid]['time']
        return t
    except KeyError:
        return 0
if __name__ == '__main__':
    a = read()
    print(datetime.datetime.strptime(a, "%Y-%m-%d %H:%M:%S")==datetime.datetime.now())