#!/usr/bin/env python3
"""
检查时间追踪数据库，验证改进1是否正常工作
"""
import os
import sqlite3
from datetime import datetime, timedelta

TRACKER_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tracker_v2.db")

def check_recent_records():
    """检查最近的时间记录"""
    if not os.path.exists(TRACKER_DB):
        print("[INFO] Database not found: %s" % TRACKER_DB)
        return
    
    conn = sqlite3.connect(TRACKER_DB)
    cursor = conn.execute("""
        SELECT app_name, window_title, start_time, duration_seconds 
        FROM usage_records 
        WHERE start_time > datetime('now', '-1 hour')
        ORDER BY start_time DESC
        LIMIT 10
    """)
    
    records = cursor.fetchall()
    conn.close()
    
    if not records:
        print("[INFO] No recent records found in the last hour")
        return
    
    print("=" * 80)
    print("Recent time tracking records (last hour):")
    print("=" * 80)
    for app_name, window_title, start_time, duration in records:
        print("[%s] %s - %s (%.1f seconds)" % (start_time, app_name, window_title[:50], duration))
    print("=" * 80)

def check_app_name_mapping():
    """检查应用名称映射是否正确"""
    if not os.path.exists(TRACKER_DB):
        return
    
    conn = sqlite3.connect(TRACKER_DB)
    cursor = conn.execute("""
        SELECT DISTINCT app_name, COUNT(*) as count
        FROM usage_records
        GROUP BY app_name
        ORDER BY count DESC
        LIMIT 20
    """)
    
    records = cursor.fetchall()
    conn.close()
    
    print("\n" + "=" * 80)
    print("App name distribution in database:")
    print("=" * 80)
    for app_name, count in records:
        print("  %s: %d records" % (app_name, count))
    print("=" * 80)

if __name__ == "__main__":
    print("Checking time tracking database...")
    check_recent_records()
    check_app_name_mapping()
