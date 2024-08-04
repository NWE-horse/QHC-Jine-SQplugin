# -*- codeing = utf-8 -*-
# @Time : 2024/4/29 18:03
# @Author :Jnine
# @File : test_yaml.py
# @Software : PyCharm
import yaml
import re
# content = {
#     'SERVER_IP':'180.188.21.144', # 服务器ip
#     'SERVER_PATH': None, # 服务器文件目录
#     'RCON_PORT': 'programming languages', # RCON端口
#     'RCON_PASSWD':1, # RCON密码
#     'POINT_NAME':'青花豆', # 积分名称
#     'MIN_HOURS':200, # 最低建队时长
# }
# with open('server-rule.yaml', 'w', encoding='utf-8') as y:
#     yaml.dump(content, y, default_flow_style=False, encoding='utf-8', allow_unicode=True)

with open("../Data/server-rule.yaml", encoding='utf-8') as f:
    data = yaml.safe_load(f)
    d=data['TeamKillMessage']
    replaced_string = re.sub(r'player1', 'A', d)
    replaced_string = re.sub(r'player2', 'B', replaced_string)
    print(replaced_string)