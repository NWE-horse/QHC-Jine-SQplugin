# -*- codeing = utf-8 -*-
# @Time : 2024/5/15 19:51
# @Author :Jnine
# @File : read_cfg.py
# @Software : PyCharm
import re
with open('../Data/Admins.cfg',encoding='utf-8') as f:
    d = f.read()
    group = re.findall(r'Group=(.+):',d)
    Admin = re.findall(r'Admin=(\d{17}):(.+)| ',d)
    Admin_list = []
    for i in Admin:
        if i[0] != '':
            data = {
                'steamid':i[0],
                'power':i[1].split(" ")[0],
                'name':i[1].split(" ")
            }
            Admin_list.append(data)
    print(Admin_list)