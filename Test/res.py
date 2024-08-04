def passive_anti_cheating():
    currenttime = float(50)
    expiredtime = float(10)
    difference = abs(currenttime - expiredtime)
    if difference > 10:
        print(True)
    else:
        print(False)
if __name__ == '__main__':
    passive_anti_cheating()
