#!/usr/bin/env python3
"""
测试模块级配置加载是否正确
"""
import os
import sys
import json

# 模拟打包后的环境
if hasattr(sys, '_MEIPASS'):
    DATA_DIR = os.path.join(sys._MEIPASS, "data")
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

print("=" * 60)
print("Testing module-level config loading")
print("=" * 60)
print("DATA_DIR: %s" % DATA_DIR)
print("DATA_DIR exists: %s" % os.path.exists(DATA_DIR))

# 测试模块级配置加载
_MAPPING_CONFIG = {}
_TITLE_MAP = {}
_IGNORE_APPS = set()

def _load_mapping_config():
    global _MAPPING_CONFIG, _TITLE_MAP, _IGNORE_APPS
    config_path = os.path.join(DATA_DIR, "app_name_mapping.json")
    print("\nConfig path: %s" % config_path)
    print("Config exists: %s" % os.path.exists(config_path))
    if not os.path.exists(config_path):
        print("[ERROR] Config file not found!")
        return
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            _MAPPING_CONFIG = json.load(f)
            _TITLE_MAP = _MAPPING_CONFIG.get("window_title_mapping", {})
            _IGNORE_APPS = set(_MAPPING_CONFIG.get("ignore_apps", []))
        print("[OK] Config loaded successfully")
    except Exception as e:
        print("[ERROR] Failed to load config: %s" % e)
        return
    
    print("\nMapping config:")
    print("  process_name_mapping: %d rules" % len(_MAPPING_CONFIG.get('process_name_mapping', {})))
    print("  window_title_mapping: %d rules" % len(_TITLE_MAP))
    print("  ignore_apps: %s" % _IGNORE_APPS)
    
    # 测试进程名映射
    print("\nTesting process name mapping:")
    test_cases = [
        ("valorant-win64-shipping", "valorant"),
        ("cs2", "CS2"),
        ("explorer", "文件资源管理器"),
    ]
    for process_name, expected in test_cases:
        import re
        # 通用后缀清理
        normalized = re.sub(r'[-_](pc|x64|x86|win64.*|win32.*)$', '', process_name, flags=re.IGNORECASE)
        # 应用映射
        process_mapping = _MAPPING_CONFIG.get("process_name_mapping", {})
        if normalized in process_mapping:
            result = process_mapping[normalized]
            if isinstance(result, str):
                normalized = result
        status = "[PASS]" if normalized == expected else "[FAIL]"
        print("  %s '%s' -> '%s' (expected: '%s')" % (status, process_name, normalized, expected))

_load_mapping_config()
print("=" * 60)
