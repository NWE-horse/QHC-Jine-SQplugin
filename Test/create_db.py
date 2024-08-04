import sqlite3

# 建立数据库连接
connection = sqlite3.connect('../Data/sign.db')

# 获取游标
cursor = connection.cursor()

# 执行创建表的 SQL 语句
create_table_sql = """
CREATE TABLE IF NOT EXISTS Sign (
    steam_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    number FLOAT(6,2),
    sign_date DATE
);
"""
cursor.execute(create_table_sql)

# 提交事务
connection.commit()

# 关闭游标
cursor.close()

# 关闭数据库连接
connection.close()
