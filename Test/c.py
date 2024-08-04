import datetime,time
game_time_stats = {}

def connection_player(eosid):
    star_time = time.time()
    game_time_stats[eosid] = {
        'startTime': star_time
    }


# 玩家退出
def disconnection_player(eosid):
    end_time = time.time()
    start_time = game_time_stats[eosid]['startTime']

    time_difference = end_time - start_time
    min = time_difference // 60
    if min < 1:
        print('不足一分钟',min)
    else:
        print(min)