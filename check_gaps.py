import sqlite3
from datetime import datetime
import os

db_path = r'D:\QClawWorkspace\all_in_one\data\tracker_v2.db'

print(f"=== 检查今天（2026-06-05）的追踪记录时间分布 ===\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 获取今天的记录，按小时统计
print("按小时统计记录数:")
cursor.execute("""
    SELECT 
        strftime('%H', start_time) as hour,
        COUNT(*) as count,
        SUM(duration_seconds) as total_sec
    FROM usage_records
    WHERE DATE(start_time) = '2026-06-05'
    GROUP BY hour
    ORDER BY hour
""")
for row in cursor.fetchall():
    hour, count, total = row
    mins = total // 60
    print(f"  {hour}:00-{hour}:59: {count}条记录, 总计 {mins}分钟")

# 检查记录的时间间隔（找出断层）
print(f"\n=== 检查记录时间连续性 ===")
cursor.execute("""
    SELECT start_time, end_time, app_name, duration_seconds
    FROM usage_records
    WHERE DATE(start_time) = '2026-06-05'
    ORDER BY start_time DESC
    LIMIT 30
""")

records = cursor.fetchall()
print("最近30条记录（从新到旧）:")
for row in records:
    start, end, app, duration = row
    print(f"  {start} ~ {end} | {app} | {duration}秒")

# 检查是否有超过30分钟的时间断层
print(f"\n=== 检查时间断层（超过30分钟无记录）===")
cursor.execute("""
    SELECT 
        LAG(end_time) OVER (ORDER BY start_time) as prev_end,
        start_time,
        app_name,
        duration_seconds
    FROM usage_records
    WHERE DATE(start_time) = '2026-06-05'
    ORDER BY start_time
""")

prev_end = None
gaps = []
for row in cursor.fetchall():
    prev_end_str, start_str, app, duration = row
    if prev_end_str and start_str:
        prev_dt = datetime.fromisoformat(prev_end_str.replace(' ', 'T'))
        curr_dt = datetime.fromisoformat(start_str.replace(' ', 'T'))
        gap_minutes = (curr_dt - prev_dt).total_seconds() / 60
        if gap_minutes > 30:
            gaps.append((prev_end_str, start_str, gap_minutes))

if gaps:
    print(f"发现 {len(gaps)} 个时间断层（超过30分钟）:")
    for prev, curr, gap in gaps:
        print(f"  {prev} -> {curr} (间隔 {gap:.0f}分钟)")
else:
    print("  未发现明显的时间断层")

conn.close()
print("\n检查完成")