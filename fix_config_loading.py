#!/usr/bin/env python3
"""
修复 BuiltinTracker 的配置加载问题
将配置加载代码从类定义内部移到模块级别
"""

import os
import json
import re

# 读取 main.py
with open(r"D:\QClawWorkspace\all_in_one\main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 找到 BuiltinTracker 类的开始位置
class_start = content.find("class BuiltinTracker:")

# 找到 _init_db 方法的结束位置（在 _load_mapping_config 之前）
# 我们需要在类定义开始后，找到正确的插入点

# 方案：直接重写整个改进1的逻辑
# 1. 在文件开头部分（DATA_DIR 定义后）添加模块级配置加载
# 2. 修改 BuiltinTracker 类使用模块级配置

# 先添加模块级配置加载代码（在 DATA_DIR 定义后）
data_dir_line = 'DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")'
if hasattr(sys, '_MEIPASS'):
    data_dir_line = '''if hasattr(sys, '_MEIPASS'):
    DATA_DIR = os.path.join(sys._MEIPASS, "data")
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")'''

print("需要手动修复 main.py 中的配置加载代码")
print("建议：将配置加载代码移到 BuiltinTracker 类定义之前")
