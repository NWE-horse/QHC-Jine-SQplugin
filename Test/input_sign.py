import configparser
import sqlite3
import datetime

def import_ini_to_sqlite():
    # 读取INI文件
    config = configparser.ConfigParser()
    config.read(r'D:\UserSignData\sign.ini', encoding='utf-8')

    # 建立数据库连接
    connection = sqlite3.connect(r'D:\UserSignData\sign.db')
    cursor = connection.cursor()

    # 遍历每个节，并将数据插入数据库
    for section in config.sections():
        steam_id = section
        name = config[section].get('name', '')  # 使用get方法来获取name配置项，如果不存在则返回空字符串
        number = int(config[section].get('number', "0"))  # 使用get方法来获取number配置项，如果不存在则返回0
        sign_date = config[section].get('time', '')  # 使用get方法来获取time配置项，如果不存在则返回空字符串

        # 如果时间为空，则使用当前日期作为签到日期
        if not sign_date:
            sign_date = datetime.datetime.now().strftime('%m/%d')

        # 执行插入数据的 SQL 语句
        insert_query = "INSERT INTO Sign (steam_id, name, number, sign_date) VALUES (?, ?, ?, ?)"
        cursor.execute(insert_query, (steam_id, name, number, sign_date))

    # 提交事务
    connection.commit()

    # 关闭游标和数据库连接
    cursor.close()
    connection.close()

# 调用函数将INI文件数据导入到SQLite数据库中
import_ini_to_sqlite()