import json
import re
import subprocess
def tail():
    # 构建 PowerShell 调用命令
    cmd = [
        "powershell.exe",
        "-Command",
        "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Content -Path 'D:\squad1\SquadGame\Saved\Logs\SquadGame.log' -Tail 1 -Wait"
    ]

    # 启动子进程
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    # 实时打印 PowerShell 脚本的输出
    try:
        while True:
            output = process.stdout.readline()
            if output:
                print(output)
                yield output
            else:
                break
    except KeyboardInterrupt:
        print("Stopped by user.")
        process.kill()
def base():
    data = tail()
    if 'PostLogin' in data:
        write(data)
def write(data):
    Sqmatch = r'PostLogin: (.*) \(IP: (\d+\.\d+\.\d+\.\d+) \| Online IDs: EOS: ([\da-f]{32}) steam: (\d{17})'
    ls = re.findall(Sqmatch, data)[0]
    ip,eosid,steamid = ls[1],ls[2],ls[3]
    player = {steamid:{'ip':ip,'eosid':eosid}}
    try:
        with open('JoinPlayers.json', "r") as json_file:
            existing_data = json.load(json_file)
    except FileNotFoundError:
        # 如果文件不存在，则创建一个空的字典
        existing_data = {}
        # 更新字典数据
    for steamid, values in player.items():
        if steamid not in existing_data:
            existing_data[steamid] = values

            # 将更新后的字典写入 JSON 文件
    with open('JoinPlayers.json', "w") as json_file:
        json.dump(existing_data, json_file, indent=4)  # indent 参数可选，用于指定缩进的空格数，使输出更易读

if __name__ == '__main__':
    print('日志分析启动成功')
    base()