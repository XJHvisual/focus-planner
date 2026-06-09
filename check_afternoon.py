import sqlite3

db_path = r'D:\QClawWorkspace\all_in_one\data\tracker_v2.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== 下午时段（14:00-20:00）的所有记录 ===\n")

cursor.execute("""
    SELECT start_time, end_time, app_name, window_title, duration_seconds
    FROM usage_records
    WHERE DATE(start_time) = '2026-06-05'
      AND time(start_time) >= '14:00:00'
      AND time(start_time) <= '20:00:00'
    ORDER BY start_time
""")

records = cursor.fetchall()
for start, end, app, title, duration in records:
    mins = duration // 60
    secs = duration % 60
    time_str = f"{mins}m{secs}s"
    print(f"[{start}] {app}")
    print(f"    标题: {title}")
    print(f"    时长: {time_str}")
    print()

print(f"\n=== 汇总：下午时段的应用使用时长 ===")
cursor.execute("""
    SELECT app_name, SUM(duration_seconds) as total
    FROM usage_records
    WHERE DATE(start_time) = '2026-06-05'
      AND time(start_time) >= '14:00:00'
      AND time(start_time) <= '20:00:00'
    GROUP BY app_name
    ORDER BY total DESC
""")
for app, total in cursor.fetchall():
    hours = total // 3600
    mins = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        print(f"  {app}: {hours}h{mins}m{secs}s")
    else:
        print(f"  {app}: {mins}m{secs}s")

conn.close()