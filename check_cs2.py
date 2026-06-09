import sqlite3
from datetime import datetime, timedelta
import os

# 动态获取数据库路径（基于脚本所在目录）
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'data', 'tracker_v2.db')

print(f"数据库路径: {db_path}\n")

# 自动使用当天日期
today = datetime.now().strftime('%Y-%m-%d')

conn = None
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 检查今天的所有应用
    print(f"=== {today} 所有应用统计 ===")
    cursor.execute("""
        SELECT app_name, COUNT(*), SUM(duration_seconds)
        FROM usage_records
        WHERE DATE(start_time) = ?
        GROUP BY app_name
        ORDER BY SUM(duration_seconds) DESC
    """, (today,))

    results = cursor.fetchall()
    if results:
        print(f"共 {len(results)} 个不同应用:\n")
        for row in results:
            app, count, total_seconds = row
            mins = total_seconds // 60
            secs = total_seconds % 60
            hours = mins // 60
            remain_mins = mins % 60
            if hours > 0:
                print(f"  {app}: {count}条, 总计 {hours}h{remain_mins}m")
            else:
                print(f"  {app}: {count}条, 总计 {mins}m{secs}s")
    else:
        print("  无记录")

    # 检查是否有CS2相关（模糊匹配）
    print(f"\n=== 检查CS2相关记录（模糊匹配）===")
    cursor.execute("""
        SELECT DISTINCT app_name
        FROM usage_records
        WHERE app_name LIKE '%cs%'
           OR app_name LIKE '%counter%'
           OR app_name LIKE '%strike%'
           OR window_title LIKE '%cs%'
           OR window_title LIKE '%Counter%'
           OR window_title LIKE '%Strike%'
    """)
    cs_related = cursor.fetchall()

    if cs_related:
        print("找到相关记录:")
        for row in cs_related:
            print(f"  {row[0]}")
    else:
        print("  未找到CS2相关记录")
        print("  可能原因:")
        print("  1. CS2的进程名不是 'cs2'")
        print("  2. CS2被反作弊软件屏蔽，无法获取窗口信息")
        print("  3. CS2在全屏模式下运行，追踪器无法捕捉")

    # 检查所有不重复的应用名（最近100个）
    print(f"\n=== 数据库中所有不重复的应用名（最近100个）===")
    cursor.execute("""
        SELECT DISTINCT app_name
        FROM usage_records
        ORDER BY rowid DESC
        LIMIT 100
    """)
    all_apps = cursor.fetchall()
    print(f"  (显示前50个)")
    for i, row in enumerate(all_apps[:50]):
        print(f"  {i+1}. {row[0]}")

except Exception as e:
    print(f"\n错误: {e}")
finally:
    if conn:
        conn.close()
        print("\n数据库连接已安全关闭")

print("检查完成")
