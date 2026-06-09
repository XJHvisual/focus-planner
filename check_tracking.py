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

# 白名单：只允许已知的表名
ALLOWED_TABLES = {"usage_records", "activity_log", "tracking_data"}

# 查找第一个在白名单中的表，否则回退到第一个表并校验
table_name = None
for t in tables:
    if t[0] in ALLOWED_TABLES:
        table_name = t[0]
        break

if table_name is None:
    # 没找到白名单表，用第一个表但校验表名格式（仅允许字母数字下划线）
    raw_name = tables[0][0]
    if raw_name.isidentifier():
        table_name = raw_name
    else:
        print(f"❌ 表名 '{raw_name}' 包含非法字符，拒绝使用！")
        conn.close()
        exit(1)

print(f"使用表: {table_name}\n")

# 通过 PRAGMA table_info 探测字段名，避免字段名硬编码假设
cursor.execute(f"PRAGMA table_info({table_name});")
columns = {row[1] for row in cursor.fetchall()}
print(f"表字段: {columns}\n")

# 确定日期字段和时长字段
if "start_time" in columns:
    date_field = "DATE(start_time)"
elif "date" in columns:
    date_field = "date"
elif "created_at" in columns:
    date_field = "DATE(created_at)"
else:
    print("❌ 找不到日期字段 (start_time / date / created_at)")
    conn.close()
    exit(1)

if "duration_seconds" in columns:
    duration_field = "duration_seconds"
elif "duration" in columns:
    duration_field = "duration"
else:
    print("❌ 找不到时长字段 (duration_seconds / duration)")
    conn.close()
    exit(1)

# 检查今天的记录
print(f"=== {today} 使用记录 (TOP 20) ===")
try:
    cursor.execute(f"""
        SELECT app_name, SUM({duration_field}) as total 
        FROM {table_name} 
        WHERE {date_field} = ? 
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
    # 选取一个合适的排序字段
    if "id" in columns:
        order_field = "id"
    elif "start_time" in columns:
        order_field = "start_time"
    elif "timestamp" in columns:
        order_field = "timestamp"
    else:
        order_field = None

    if order_field:
        cursor.execute(f"""
            SELECT {date_field} as record_date, app_name, {duration_field}, 
                   COALESCE(start_time, timestamp, '') as ts
            FROM {table_name} 
            ORDER BY {order_field} DESC 
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]} {row[1]}: {row[2]}秒 ({row[3]})")
    else:
        print("  （找不到合适的排序字段）")
except Exception as e:
    print(f"❌ 查询失败: {e}")

conn.close()
print("\n✅ 检查完成")
