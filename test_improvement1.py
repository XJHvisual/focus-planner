#!/usr/bin/env python3
"""
测试改进1：进程名识别优化
验证 app_name_mapping.json 配置是否正确加载和应用
"""

import os
import json
import sys

# 模拟 BuiltinTracker 的配置加载逻辑
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

class MockBuiltinTracker:
    """模拟 BuiltinTracker 的配置加载"""
    _mapping_config = {}
    _title_map = {}
    IGNORE_APPS = set()
    
    @classmethod
    def _load_mapping_config(cls):
        """从 app_name_mapping.json 加载映射配置"""
        config_path = os.path.join(DATA_DIR, "app_name_mapping.json")
        if not os.path.exists(config_path):
            print("[ERROR] Config file not found: %s" % config_path)
            return False
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cls._mapping_config = json.load(f)
                cls._title_map = cls._mapping_config.get("window_title_mapping", {})
                cls.IGNORE_APPS = set(cls._mapping_config.get("ignore_apps", []))
            print("[OK] Config loaded successfully")
            return True
        except Exception as e:
            print("[ERROR] Failed to load config: %s" % e)
            return False
    
    @classmethod
    def test_process_mapping(cls, process_name, title=""):
        """测试进程名映射"""
        import re
        
        # 忽略规则检查
        if process_name in cls.IGNORE_APPS:
            return None
        
        # 通用后缀清理
        process_name = re.sub(r'[-_](pc|x64|x86|win64.*|win32.*)$', '', process_name, flags=re.IGNORECASE)
        
        # 从配置文件应用进程名映射
        process_mapping = cls._mapping_config.get("process_name_mapping", {})
        if process_name in process_mapping:
            mapping_rule = process_mapping[process_name]
            if isinstance(mapping_rule, str):
                process_name = mapping_rule
            elif isinstance(mapping_rule, dict):
                if "title_contains" in mapping_rule and mapping_rule["title_contains"] in title:
                    process_name = mapping_rule["map_to"]
                elif "title_contains" not in mapping_rule:
                    process_name = mapping_rule.get("map_to", process_name)
        
        return process_name

def main():
    print("=" * 60)
    print("Test Improvement 1: Process Name Recognition Optimization")
    print("=" * 60)
    
    # 加载配置
    tracker = MockBuiltinTracker()
    if not tracker._load_mapping_config():
        sys.exit(1)
    
    print("\nConfig content:")
    print("  Process name mapping rules: %d" % len(tracker._mapping_config.get('process_name_mapping', {})))
    print("  Window title mapping: %d" % len(tracker._title_map))
    print("  Ignored apps: %s" % tracker.IGNORE_APPS)
    
    # 测试用例
    test_cases = [
        # (process_name, title, expected)
        ("valorant-win64-shipping", "", "valorant"),
        ("pythonw", "专注规划器 v3.0", "专注规划器"),
        ("explorer", "", "文件资源管理器"),
        ("qclaw", "", "QClaw"),
        ("cs2", "", "CS2"),
        ("nexus", "", None),  # Should be ignored
        ("unknown", "鸣潮", "鸣潮"),  # Title mapping
        ("unknown", "AppTimeTracker V2", "应用时间追踪器"),  # Title mapping
    ]
    
    print("\nTest cases:")
    all_passed = True
    for process_name, title, expected in test_cases:
        result = tracker.test_process_mapping(process_name, title)
        if result is None and expected is None:
            status = "[PASS]"
        elif result == expected:
            status = "[PASS]"
        else:
            status = "[FAIL]"
            all_passed = False
        
        print("  %s process_name='%s', title='%s' -> '%s' (expected: '%s')" % (status, process_name, title, result, expected))
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] All tests passed! Improvement 1 logic is correct.")
    else:
        print("[FAIL] Some tests failed, need to check code.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
