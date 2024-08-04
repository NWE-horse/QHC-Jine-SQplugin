import requests
import json

try:
    data = requests.get(f'http://150.138.84.157:3000/player/7656119947600395').json()
    # 将history字段从字符串转换为数组
    data['history'] = json.loads(data['history'])
    wins = 0
    count = 0
    for i in data['history']:
        count += 1
        if i['win']:
            wins += 1
    print(data['kills'], data['deaths'], data['playTime'], wins, count)
except KeyError:
    print('没有用户')
