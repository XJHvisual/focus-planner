"""Auto-extracted module."""
import os
import sqlite3
import threading
import time
from datetime import datetime, date
import ctypes
from config import DATA_DIR, RECORDS_FILE, TRACKER_DB
from data_manager import DataManager

class BuiltinTracker:
    """轻量级前台窗口时间追踪器，使用 ctypes 调用 Win32 API，零外部依赖"""
    POLL_INTERVAL = 2  # 秒

    def __init__(self):
        self._running = False
        self._thread = None
        self._current_app = None
        self._current_title = ""
        self._session_start = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._init_db()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._flush()

    def _init_db(self):
        conn = sqlite3.connect(TRACKER_DB)
        conn.execute("""CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            window_title TEXT DEFAULT '',
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            category TEXT DEFAULT '其他',
            productivity_score INTEGER DEFAULT 50,
            UNIQUE(app_name, start_time)
        )""")
        conn.commit()
        # 一次性迁移：从旧 AppTimeTracker V2 数据库导入已有记录
        old_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app-time-tracker-v2", "dist", "data", "tracker_v2.db")
        if os.path.exists(old_db):
            cur = conn.execute("SELECT COUNT(*) FROM usage_records")
            if cur.fetchone()[0] == 0:
                try:
                    conn.execute("ATTACH ? AS old_db", (old_db,))
                    conn.execute(
                        "INSERT OR IGNORE INTO usage_records(app_name, window_title, start_time, end_time, duration_seconds, category, productivity_score) SELECT app_name, window_title, start_time, end_time, duration_seconds, category, productivity_score FROM old_db.usage_records"
                    )
                    conn.commit()
                    conn.execute("DETACH DATABASE old_db")
                except Exception as e:
                    print(f"数据迁移失败: {e}")
        conn.close()

    _title_map = {
        "MainDialog": "鸣潮", "鸣潮": "鸣潮",
        "AppTimeTracker V2": "应用时间追踪器",
        "QClaw": "QClaw",
        "无畏契约": "valorant",
        "战绩结算弹窗": "valorant",
        "VALORANT": "valorant",
        "Riot Client": "valorant",
        "Hermes": "Hermes",
        "5E": "5e对战平台",
        "5e": "5e对战平台",
    }
    # 标题关键词映射（含deepseek/gemini等模型名 → Hermes）
    _title_keywords = [
        (["deepseek", "claude", "gemini", "gpt", "hermes"], "Hermes"),
        (["5e", "5E", "5EClient"], "5e对战平台"),
    ]
    # 已知正常应用名（免过滤）
    KNOWN_APPS = {
        'python', 'pythonw', 'taskmgr', 'mysqlworkbench', 'mysqlshellworkbench',
        'notepad', 'chrome', 'msedge', 'obsidian', 'cursor', 'devenv',
        'valorant', 'cs2', 'weixin', 'douyin', 'wps', 'electron',
        'windowsterminal', 'powershell', 'cmd', 'explorer',
        'java', 'javaw', 'steam', 'steamwebhelper', 'snippingtool',
        'fontview', 'bodian', 'launcher', 'powerpnt', 'pickhost',
        'shellexperiencehost', 'shellhost', 'searchhost',
        'photolaunch', 'openwith', 'werfault', 'zipmaster',
    }
    # 随机进程名检测
    @staticmethod
    def _is_random_name(name):
        if not name or len(name) < 5:
            return False
        lower = name.lower()
        if lower in BuiltinTracker.KNOWN_APPS:
            return False
        letters = [c for c in lower if c.isalpha()]
        if not letters:
            return False
        vowels = sum(1 for c in letters if c in 'aeiou')
        ratio = vowels / len(letters) if letters else 0
        # 无元音 + 长度≥6 = 随机串
        if ratio == 0 and len(lower) >= 6:
            return True
        # 元音极少(<10%) + 大小写混用 + 长度≥8 = 随机串
        has_upper = any(c.isupper() for c in name)
        has_lower = any(c.islower() for c in name)
        if ratio < 0.10 and has_upper and has_lower and len(name) >= 8:
            return True
        return False
    IGNORE_APPS = {"nexus", "nexusportable", "rocketdock", "rainmeter", "wallpaperengine"}
    # 已知随机进程名（无法识别来源的应用，直接忽略）
    RANDOM_APPS = {
        't1rlujgjsosf', 'bfefwxbs', 'q1rr9io', 'rfqs1lufak', 'kqembdvpack6r9',
        'mi03cgmwbnqwurc', 'zeb5ecdb4nqwurc', 'bsoip5kd4nqwurc',
        'f4vwvlm2hb1bmhk', 'ui32', '0fliogrxri', '0nqya3juwc2',
        'ubm5fnguwc2', 'xntinfzzfgr41', 'vsouo3g2m', 'kp6h5rtxiebj',
    }

    def _get_foreground(self):
        """通过 Win32 API 获取当前前台窗口信息"""
        import ctypes
        import re
        from ctypes import wintypes
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None, ""
            # 窗口标题
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value or ""
            # 进程名
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process_name = "unknown"
            if pid.value:
                kernel32 = ctypes.windll.kernel32
                h_process = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
                if h_process:
                    exe_buf = ctypes.create_unicode_buffer(260)
                    exe_len = wintypes.DWORD(260)
                    if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buf, ctypes.byref(exe_len)):
                        exe_path = exe_buf.value
                        process_name = os.path.basename(exe_path).lower().replace('.exe', '')
                        # 5E对战平台CS2：进程名是加密随机串，通过路径识别
                        if re.search(r'(?i)[/\\]5e[/\\]|[/\\]5EClient[/\\]|[/\\]5eclient[/\\]', exe_path):
                            process_name = 'cs2'
                    kernel32.CloseHandle(h_process)

            # 忽略规则
            if process_name in self.IGNORE_APPS or process_name in self.RANDOM_APPS:
                return None, ""

            # 进程名归一化
            # 通用：去掉 _pc、_x64、-win64-*、_win32_* 等平台/版本后缀
            process_name = re.sub(r'[-_](pc|x64|x86|win64.*|win32.*)$', '', process_name, flags=re.IGNORECASE)
            if process_name == "valorant-win64-shipping":
                process_name = "valorant"
            elif process_name == "pythonw" and "拾光" in title:
                process_name = "拾光"
            elif process_name == "explorer":
                process_name = "文件资源管理器"
            elif process_name == "qclaw":
                process_name = "QClaw"

            # 标题映射（按标题关键词识别应用）
            if title.strip():
                # 精确匹配
                matched = False
                for key, app_name in self._title_map.items():
                    if key in title:
                        process_name = app_name
                        matched = True
                        break
                # 关键词模糊匹配
                if not matched:
                    for keywords, app_name in self._title_keywords:
                        if any(kw.lower() in title.lower() for kw in keywords):
                            process_name = app_name
                            matched = True
                            break
                if not matched and process_name == "unknown":
                    # 用标题作为应用名（前20字符）
                    clean = title.strip()
                    process_name = clean[:20].lower() if len(clean) <= 20 else clean[:18].lower() + "…"

            # 过滤随机/无意义进程名（如 t1rlujgjsosf、bfefwxbs）
            if not title.strip() or title.strip().lower() == process_name.lower():
                if self._is_random_name(process_name):
                    return None, ""  # 跳过随机串
            elif process_name == "unknown" and (not title or not title.strip()):
                return None, ""

            # 统一小写（仅英文部分，中文不受影响）
            process_name = process_name.lower()

            return process_name, title
        except Exception:
            return None, ""

    def _run(self):
        while self._running:
            try:
                app, title = self._get_foreground()
                if app and app != self._current_app:
                    self._flush()
                    self._current_app = app
                    self._current_title = title
                    self._session_start = datetime.now()
                time.sleep(self.POLL_INTERVAL)
            except Exception:
                time.sleep(self.POLL_INTERVAL)

    def _flush(self):
        if not self._current_app or not self._session_start:
            return
        now = datetime.now()
        duration = (now - self._session_start).total_seconds()
        if duration < 1:
            return
        try:
            conn = sqlite3.connect(TRACKER_DB)
            conn.execute(
                "INSERT OR IGNORE INTO usage_records(app_name, window_title, start_time, end_time, duration_seconds) VALUES(?,?,?,?,?)",
                (self._current_app, self._current_title,
                 self._session_start.isoformat(), now.isoformat(), int(duration))
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


# ============ 📊 时间追踪 Tab（读取 AppTimeTracker V2 数据库） ============