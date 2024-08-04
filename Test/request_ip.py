# -*- codeing = utf-8 -*-
# @Time : 2024/5/21 22:07
# @Author :Jnine
# @File : request_ip.py
# @Software : PyCharm
import requests

def request_steam(id):
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
if __name__ == '__main__':
    print(request_steam('76561199158032290'))