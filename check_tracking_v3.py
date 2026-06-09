import sqlite3
from datetime import datetime, timedelta
import os

db_path = r'D:\QClawWorkspace\all_in_one\data\tracker_v2.db'

print(f"数据库路径: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查最近3天的记录
print("=== 最近3天的记录统计 ===")
for days_ago in range(0, 3):
    target_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*), SUM(duration_seconds)
        FROM usage_records
        WHERE DATE(start_time) = ?
    """, (target_date,))
    count, total_seconds = cursor.fetchone()
    if count > 0:
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        print(f"  {target_date}: {count} 条记录, 总计 {hours}小时{mins}分钟")
    else:
        print(f"  {target_date}: ❌ 无记录")

# 检查最近的10条记录（看看最后记录是什么时候）
print(f"\n=== 最近10条记录 ===")
cursor.execute("""
    SELECT app_name, start_time, duration_seconds
    FROM usage_records
    ORDER BY rowid DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    app, start, duration = row
    print(f"  {app}: {start} (持续 {duration}秒)")

# 检查CS2的所有记录
print(f"\n=== CS2 的所有记录 ===")
cursor.execute("""
    SELECT DATE(start_time) as date, COUNT(*), SUM(duration_seconds)
    FROM usage_records
    WHERE app_name LIKE '%cs%'
    GROUP BY DATE(start_time)
    ORDER BY date DESC
""")
cs_records = cursor.fetchall()
if cs_records:
    for row in cs_records:
        date, count, total = row
        mins = total // 60
        print(f"  {date}: {count} 条记录, 总计 {mins}分钟")
else:
    print("  ❌ 没有找到CS2相关记录")

# 检查数据库文件大小变化
db_size = os.path.getsize(db_path)
print(f"\n数据库文件大小: {db_size / 1024:.1f} KB")
print(f"最后修改时间: {datetime.fromtimestamp(os.path.getmtime(db_path))}")

conn.close()
print("\n✅ 检查完成")
