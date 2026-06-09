#!/usr/bin/env python3
"""合并数据库中的旧应用名记录"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'tracker_v2.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 查找需要合并的记录
cur.execute("SELECT app_name, COUNT(*) FROM usage_records GROUP BY app_name ORDER BY COUNT(*) DESC")
print('Current app distribution:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]} records')

# 需要合并的映射
merge_map = {
    'cs2': 'CS2',
    'explorer': '文件资源管理器',
    'pythonw': '专注规划器',
    'valorant-win64-shipping': 'valorant'
}

print('\nMerging records...')
for old_name, new_name in merge_map.items():
    # 检查旧记录
    cur.execute('SELECT COUNT(*) FROM usage_records WHERE app_name = ?', (old_name,))
    count = cur.fetchone()[0]
    if count > 0:
        # 更新记录
        conn.execute('UPDATE usage_records SET app_name = ? WHERE app_name = ?', (new_name, old_name))
        print(f'  {old_name} -> {new_name}: {count} records merged')

conn.commit()

# 验证结果
print('\nAfter merge:')
cur.execute("SELECT app_name, COUNT(*) FROM usage_records GROUP BY app_name ORDER BY COUNT(*) DESC LIMIT 10")
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

conn.close()
print('\nDone!')
