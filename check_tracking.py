import sqlite3
from datetime import date
import os

db_path = r'D:\QClawWorkspace\all_in_one\data\tracker_v2.db'
today = date.today().isoformat()

print(f"数据库路径: {db_path}")
print(f"今天日期: {today}\n")

if not os.path.exists(db_path):
    print("❌ 数据库文件不存在！")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查表结构
print("=== 数据库表结构 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"数据表: {tables}\n")

if not tables:
    print("❌ 数据库中没有表！")
    conn.close()
    exit(1)

# 获取第一个表名
table_name = tables[0][0]
print(f"使用表: {table_name}\n")

# 检查今天的记录
print(f"=== {today} 使用记录 (TOP 20) ===")
try:
    cursor.execute(f"""
        SELECT app_name, SUM(duration) as total 
        FROM {table_name} 
        WHERE date = ? 
        GROUP BY app_name 
        ORDER BY total DESC 
        LIMIT 20
    """, (today,))
    
    results = cursor.fetchall()
    if results:
        for row in results:
            app, seconds = row
            mins = seconds // 60
            secs = seconds % 60
            print(f"  {app}: {mins}分{secs}秒")
    else:
        print("  （无记录）")
except Exception as e:
    print(f"❌ 查询失败: {e}")

# 检查是否有CS2相关记录
print(f"\n=== 检查CS2相关记录 ===")
try:
    cursor.execute(f"""
        SELECT DISTINCT app_name 
        FROM {table_name} 
        WHERE app_name LIKE '%cs%' 
           OR app_name LIKE '%counter%' 
           OR app_name LIKE '%strike%'
    """)
    cs_results = cursor.fetchall()
    if cs_results:
        print("找到CS相关记录:")
        for row in cs_results:
            print(f"  {row[0]}")
    else:
        print("❌ 没有找到CS2相关记录")
except Exception as e:
    print(f"❌ 查询失败: {e}")

# 检查最近的记录
print(f"\n=== 最近10条记录 ===")
try:
    cursor.execute(f"""
        SELECT date, app_name, duration, timestamp 
        FROM {table_name} 
        ORDER BY id DESC 
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]}: {row[2]}秒 ({row[3]})")
except Exception as e:
    print(f"❌ 查询失败: {e}")

conn.close()
print("\n✅ 检查完成")
