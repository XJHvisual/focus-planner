import sqlite3
from datetime import datetime

db_path = r'D:\QClawWorkspace\all_in_one\data\tracker_v2.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# CS2 对战记录（从截图提取）
cs2_matches = [
    ("2026-06-05 13:49:00", "2026-06-05 14:26:00", "cs2", "CS2", 37*60),   # 13:49-14:26, 37分钟
    ("2026-06-05 14:26:00", "2026-06-05 14:59:00", "cs2", "CS2", 33*60),   # 14:26-14:59, 33分钟
    ("2026-06-05 14:59:00", "2026-06-05 15:31:00", "cs2", "CS2", 32*60),   # 14:59-15:31, 32分钟
]

# 插入 CS2 记录
for start, end, app, title, duration in cs2_matches:
    cursor.execute("""
        INSERT INTO usage_records (app_name, window_title, start_time, end_time, duration_seconds)
        VALUES (?, ?, ?, ?, ?)
    """, (app, title, start, end, duration))
    print(f"[OK] Insert: {start} ~ {end} | CS2 | {duration//60}m{duration%60}s")

# 验证插入结果
print(f"\n=== 今日 CS2 记录 ===")
cursor.execute("""
    SELECT start_time, end_time, duration_seconds FROM usage_records
    WHERE DATE(start_time) = '2026-06-05' AND app_name = 'cs2'
    ORDER BY start_time
""")
total = 0
for row in cursor.fetchall():
    total += row[2]
    print(f"  {row[0]} ~ {row[1]} | {row[2]//60}m{row[2]%60}s")

print(f"\n总计 CS2: {total//60}h{(total%3600)//60}m")

conn.commit()
conn.close()
print("\n完成！")