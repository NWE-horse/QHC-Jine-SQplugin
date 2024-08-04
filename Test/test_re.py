import urllib.request
from bs4 import BeautifulSoup
import re
import json
def request_steam(id):
        try:
            res = urllib.request.urlopen(f'http://103.185.248.130/{id}').read().decode('utf-8')
            soup = BeautifulSoup(res, 'html.parser')
            game_name_divs = soup.find_all('div', class_='game_info')
            user_title_divs = soup.find_all('div', class_='profile_header_bg_texture')
            player = []
            for element in user_title_divs:
                name = element.find_all('span', class_='actual_persona_name')[0].get_text(separator='', strip=True)
                player.append(name)
                level = element.find('span', class_='friendPlayerLevelNum')
                if level != None:
                    levelnum = level.get_text(separator='', strip=True)
                else:
                    levelnum = None
                player.append(levelnum)
            if game_name_divs != []:
                for div in game_name_divs:
                    name = div.find_all('a', class_='whiteLink')[0].get_text(separator='', strip=True)
                    if name == 'Squad':
                        time = \
                        div.find_all('div', class_='game_info_details')[0].get_text(separator='', strip=True).split('hrs')[
                            0].replace(',', '')
                        player.append(time)
                        break
                    else:
                        pass
                else:
                    player.append(None)
            else:
                player.append(None)
            return player
        except Exception as e:
            print('发生错误',e)
d = [{'steamid': '76561198192599254', 'kill': 20, 'wound': 16, 'death': 0}, {'steamid': '76561198272259619', 'kill': 7, 'wound': 6, 'death': 3},
 {'steamid': '76561198192599254', 'kill': 19, 'wound': 0, 'death': 0}, {'steamid': '76561199563762323', 'kill': 3, 'wound': 3, 'death': 4},]
def squad():
    d = r'\[([0-9.:-]+)\]\[([ 0-9]*)\]LogSquadGameEvents: Display: Team (\d), (.*?) has won the match with (\d*) Tickets on layer (.*v\d)'
    s = '[2024.07.17-14.06.00:014][692]LogSquadGameEvents: Display: Team 1, 3rd Division Battle Group ( 英国军队 ) has won the match with 249 Tickets on layer Narva RAAS v1 (level 纳尔瓦)!'
    m = re.match(d,s)
    if m:
        print(m[6])

if __name__ == '__main__':
    squad()