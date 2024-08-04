import subprocess
def tail():
    # 构建 PowerShell 调用命令
    cmd = [
        "powershell.exe",
        "-Command",
        "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Content -Path 'D:\squad6\SquadGame\Saved\Logs\SquadGame.log' -Tail 1 -Wait"
    ]

    # 启动子进程
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    # 实时打印 PowerShell 脚本的输出
    try:
        while True:
            output = process.stdout.readline()
            if output:
                yield output
            else:
                break
    except KeyboardInterrupt:
        print("Stopped by user.")
        process.kill()
