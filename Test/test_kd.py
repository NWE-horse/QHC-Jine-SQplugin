# -*- codeing = utf-8 -*-
# @Time : 2024/5/26 12:26
# @Author :Jnine
# @File : test_kd.py
# @Software : PyCharm
import time
kd = []
while True:
    actor = '55'
    death = '51'
    data = {
        'name':actor,
        'kill':0,
        'wound':0,
        'death':0
    }
    data1 = {
        'name': death,
        'kill': 0,
        'wound': 0,
        'death': 0
    }
    for i in kd:
        if i['name'] == actor:
            i['kill'] +=1
        elif i['name'] == death:
            i['death'] +=1
            break
    else:
        kd.append(data)
        kd.append(data1)
    print(kd)
    time.sleep(5)