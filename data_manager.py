"""DataManager - JSON file read/write with atomic saves."""
import json
import os
from config import DATA_DIR

class DataManager:
    @staticmethod
    def load(path, default=None):
        if default is None:
            default = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    @staticmethod
    def save(path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ============ 智能拆解向导 ============