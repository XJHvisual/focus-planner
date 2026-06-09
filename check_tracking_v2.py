import sqlite3
import os

db_path = r'D:\QClawWorkspace\all_in_one\data\tracker_v2.db'

print(f"数据库路径: {db_path}\n")

if not os.path.exists(db_path):
    print("❌ 数据库文件不存在！")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查表结构
print("=== 数据表结构 ===")
cursor.execute("PRAGMA table_info(usage_records);")
columns = cursor.fetchall()
print("列信息:")
for col in columns:
    print(f"  {col[0]}: {col[1]} ({col[2]})")

# 检查今天的记录（使用正确的列名）
print(f"\n=== 检查今天是否有记录 ===")
today = '2026-06-05'

# 先尝试不同的可能列名组合
possible_queries = [
    ("app_name, SUM(duration_seconds)", "duration_seconds"),
    ("app_name, SUM(duration)", "duration"),
    ("app_name, SUM(total_seconds)", "total_seconds"),
    ("app_name, COUNT(*)", "记录数"),
]

for select_part, desc in possible_queries:
    try:
        query = f"SELECT {select_part} FROM usage_records WHERE date = ? GROUP BY app_name"
        cursor.execute(query, (today,))
        results = cursor.fetchall()
        if results:
            print(f"\n✅ 使用列名: {desc}")
            print(f"=== {today} 使用记录 ===")
            for row in results[:20]:
                print(f"  {row[0]}: {row[1]}")
            break
    except Exception as e:
        continue

# 检查是否有CS2相关记录
print(f"\n=== 检查CS2相关记录 ===")
try:
    cursor.execute("""
        SELECT DISTINCT app_name 
        FROM usage_records 
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
    cursor.execute("""
        SELECT date, app_name, duration_seconds, start_time 
        FROM usage_records 
        ORDER BY rowid DESC 
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]}: {row[2]}秒 ({row[3]})")
except Exception as e:
    print(f"❌ 查询失败: {e}")

conn.close()
print("\n✅ 检查完成")
