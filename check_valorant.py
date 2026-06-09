import sqlite3
from datetime import datetime

db_path = r'D:\QClawWorkspace\all_in_one\data\tracker_v2.db'

print("=== 检查 Valorant 记录的详细内容 ===\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查今天所有 Valorant 相关记录
print("今天 Valorant 相关记录:")
cursor.execute("""
    SELECT start_time, end_time, app_name, window_title, duration_seconds
    FROM usage_records
    WHERE DATE(start_time) = '2026-06-05'
      AND (app_name LIKE '%valor%' OR app_name LIKE '%无畏%')
    ORDER BY start_time DESC
""")

total_seconds = 0
for row in cursor.fetchall():
    start, end, app, title, duration = row
    total_seconds += duration
    hours = duration // 3600
    mins = (duration % 3600) // 60
    secs = duration % 60
    time_str = f"{hours}h{mins}m{secs}s" if hours > 0 else f"{mins}m{secs}s"
    print(f"  {start} | {app} | {duration}秒 ({time_str})")
    print(f"    窗口标题: {title}")

hours = total_seconds // 3600
mins = (total_seconds % 3600) // 60
print(f"\n总计: {total_seconds}秒 ≈ {hours}小时{mins}分钟")

# 检查是否有 CS2 相关记录
print(f"\n=== 检查 CS2 相关记录 ===")
cursor.execute("""
    SELECT start_time, end_time, app_name, window_title, duration_seconds
    FROM usage_records
    WHERE DATE(start_time) = '2026-06-05'
      AND (app_name LIKE '%cs2%' OR window_title LIKE '%CS2%' OR window_title LIKE '%Counter-Strike%')
    ORDER BY start_time DESC
""")
cs2_records = cursor.fetchall()
if cs2_records:
    print("找到 CS2 记录:")
    for row in cs2_records:
        print(f"  {row}")
else:
    print("❌ 今天没有 CS2 相关记录")

conn.close()
print("\n检查完成")