"""拾光 - 考研时光伴侣 v3.2"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import atexit
from datetime import datetime, date

from config import is_another_instance_running, SETTINGS_FILE
from data_manager import DataManager
from tracker import BuiltinTracker
from wizards import SmartGoalWizard, Wizard408
from ui.goal_tab import GoalTab
from ui.task_tab import TaskTab
from ui.timer_stats_tab import TimerStatsTab
from ui.week_tab import WeekTab
from ui.time_track_tab import TimeTrackTab
from ui.progress_tab import ProgressTab
from ui.ocr_tab import OcrTab

# ── 暖调学术配色 ──
C_PAGE     = "#F8F6F2"   # 页底：暖米白
C_SIDEBAR  = "#EBE5D9"   # 侧栏：浅驼色
C_HEADER   = "#3D3830"   # 顶栏：深墨褐
C_ACCENT   = "#0D7377"   # 强调：深青绿
C_ACCENT_L = "#D4EDDA"   # 强调淡色
C_TEXT     = "#4A4238"   # 正文：炭棕
C_SUBTLE   = "#8B8178"   # 辅助文字
C_INPUT_BG = "#F2EEE6"   # 输入框底色
C_DIVIDER  = "#D5CFC6"   # 分隔线
C_RED      = "#C44536"   # 警示暖红
C_AMBER    = "#D4843A"   # 琥珀提醒
FONT       = "Microsoft YaHei"


class ShiGuangApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("拾光 v3.2")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        self.root.configure(background=C_PAGE)

        # ── 全局样式 ──
        self._setup_style()

        # ══════════════════════════════════════
        #  顶部横幅
        # ══════════════════════════════════════
        banner = tk.Frame(self.root, bg=C_HEADER, height=56)
        banner.pack(fill="x")
        banner.pack_propagate(False)

        # 左侧：标题 + 副标题
        title_area = tk.Frame(banner, bg=C_HEADER)
        title_area.pack(side="left", padx=20, pady=(8, 0))

        tk.Label(title_area, text="拾 光",
                 font=(FONT, 18, "bold"), fg="#D4C8B8",
                 bg=C_HEADER).pack(side="left")
        tk.Label(title_area, text=" · 考研路上，每一步都算数",
                 font=(FONT, 9), fg="#8B8378",
                 bg=C_HEADER).pack(side="left", padx=6)

        # 右侧：时钟 + 倒计时 + 设置
        right_area = tk.Frame(banner, bg=C_HEADER)
        right_area.pack(side="right", padx=16, pady=(0, 0))

        # 倒计时徽章
        self.countdown_badge = tk.Frame(right_area, bg=C_HEADER)
        self.countdown_badge.pack(side="left", padx=(0, 12))
        self.exam_date = self._load_settings().get("exam_date")
        self.countdown_label = tk.Label(self.countdown_badge, text="",
            font=(FONT, 11, "bold"), bg=C_HEADER)
        if self.exam_date:
            self.countdown_label.pack()
        self._refresh_countdown()

        # 时钟
        now = datetime.now()
        self.clock_label = tk.Label(right_area,
            text=now.strftime("%m月%d日 %H:%M"),
            font=(FONT, 11), fg=C_SUBTLE, bg=C_HEADER)
        self.clock_label.pack(side="left", padx=(0, 10))
        self._tick_clock()

        # 设置按钮
        self.settings_btn = tk.Button(right_area, text="考试日",
            font=(FONT, 9), bg="#4D4840", fg=C_SUBTLE, bd=0,
            activebackground="#5D5850", activeforeground="#C8BFAF",
            padx=10, pady=2, cursor="hand2",
            command=self._set_exam_date)
        self.settings_btn.pack(side="left")

        # Banner 底边装饰线
        accent_line = tk.Frame(self.root, bg=C_ACCENT, height=2)
        accent_line.pack(fill="x")

        # ══════════════════════════════════════
        #  主体：侧栏 + 内容
        # ══════════════════════════════════════
        body = tk.Frame(self.root, bg=C_PAGE)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        # 左侧边栏
        sidebar = tk.Frame(body, bg=C_SIDEBAR, width=125, highlightthickness=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # 侧栏顶部留白
        tk.Frame(sidebar, bg=C_SIDEBAR, height=12).pack(fill="x")

        # 侧栏标题
        tk.Label(sidebar, text="导  航", font=(FONT, 8),
                 fg=C_SUBTLE, bg=C_SIDEBAR).pack(anchor="w", padx=18, pady=(0, 6))

        # 导航按钮
        self.nav_btns = {}
        nav_items = [
            ("🎯  目标拆解",  "goal"),
            ("📝  今日任务",  "task"),
            ("📅  周计划表",  "week"),
            ("⏱  专注统计",  "timer"),
            ("📈  训练进度",  "progress"),
            ("📊  时间追踪",  "timetrack"),
            ("🔍  文字识别",  "ocr"),
        ]
        for i, (label, key) in enumerate(nav_items):
            btn = tk.Button(sidebar, text=label, font=(FONT, 10),
                           bg=C_SIDEBAR, fg=C_TEXT, bd=0,
                           activebackground=C_ACCENT_L, activeforeground=C_ACCENT,
                           anchor="w", padx=18, pady=7,
                           cursor="hand2",
                           command=lambda k=key: self._switch_tab(k))
            btn.pack(fill="x")
            self.nav_btns[key] = btn

        # 侧栏底部
        tk.Frame(sidebar, bg=C_SIDEBAR, height=12).pack(fill="x", side="bottom")

        # 右侧内容区
        self.content = tk.Frame(body, bg=C_PAGE)
        self.content.pack(side="left", fill="both", expand=True, padx=(0, 0))

        # 创建所有 Tab
        self.goal_tab = GoalTab(self.content, self)
        self.task_tab = TaskTab(self.content, self)
        self.week_tab = WeekTab(self.content, self)
        self.timer_stats_tab = TimerStatsTab(self.content, self)
        self.progress_tab = ProgressTab(self.content, self)
        self.timetrack_tab = TimeTrackTab(self.content, self)
        self.ocr_tab = OcrTab(self.content, self)

        # 追踪器
        self.tracker = BuiltinTracker()
        self.tracker.start()

        self._switch_tab("goal")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    # ── 导航 ──
    def _switch_tab(self, key):
        for tab in (self.goal_tab, self.task_tab, self.week_tab,
                     self.timer_stats_tab, self.progress_tab,
                     self.timetrack_tab, self.ocr_tab):
            tab.pack_forget()

        for k, btn in self.nav_btns.items():
            btn.config(bg=C_SIDEBAR, fg=C_TEXT)

        self.nav_btns[key].config(bg=C_ACCENT_L, fg=C_ACCENT)

        tab_map = {
            "goal": self.goal_tab, "task": self.task_tab,
            "week": self.week_tab, "timer": self.timer_stats_tab,
            "progress": self.progress_tab, "timetrack": self.timetrack_tab,
            "ocr": self.ocr_tab,
        }
        tab_map[key].pack(fill="both", expand=True)

        if key == "timer":
            self.timer_stats_tab.refresh_stats()
        elif key == "progress":
            self.progress_tab.refresh_progress()
        elif key == "timetrack":
            self.timetrack_tab.refresh()

    def on_close(self):
        self.tracker.stop()
        self.root.destroy()

    # ── 全局样式 ──
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=(FONT, 10), background=C_PAGE)
        style.configure("TFrame", background=C_PAGE)
        style.configure("TLabel", font=(FONT, 10), background=C_PAGE, foreground=C_TEXT)
        style.configure("TLabelframe", background=C_PAGE)
        style.configure("TLabelframe.Label", font=(FONT, 10, "bold"),
                       background=C_PAGE, foreground=C_TEXT)
        style.configure("TButton", font=(FONT, 10), padding=(10, 5))
        style.configure("TRadiobutton", font=(FONT, 10), background=C_PAGE)
        style.configure("TEntry", font=(FONT, 10), fieldbackground=C_INPUT_BG,
                       borderwidth=1, relief="solid")
        style.configure("TCombobox", font=(FONT, 10), fieldbackground=C_INPUT_BG)
        style.configure("TSpinbox", font=(FONT, 10), fieldbackground=C_INPUT_BG)
        style.map("TEntry", fieldbackground=[("focus", "#FFFFFF")])
        style.map("TCombobox", fieldbackground=[("focus", "#FFFFFF")])
        style.configure("Treeview", font=(FONT, 10), rowheight=28)
        style.configure("Treeview.Heading", font=(FONT, 10, "bold"))
        # 滚动条样式
        style.configure("TScrollbar", background=C_PAGE, troughcolor=C_INPUT_BG)

    # ── 设置 ──
    def _load_settings(self):
        return DataManager.load(SETTINGS_FILE, default={})

    def _save_settings(self, data):
        current = DataManager.load(SETTINGS_FILE, default={})
        current.update(data)
        DataManager.save(SETTINGS_FILE, current)

    def _set_exam_date(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("设置考试日期")
        dlg.geometry("320x180")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=C_PAGE)

        tk.Label(dlg, text="请输入考研初试日期：",
                 font=(FONT, 11, "bold"), bg=C_PAGE, fg=C_TEXT).pack(pady=(18, 10))

        entry_frame = tk.Frame(dlg, bg=C_PAGE)
        entry_frame.pack()

        cur_date = self._load_settings().get("exam_date", "2026-12-19")
        today = date.today()

        tk.Label(entry_frame, text="年", font=(FONT, 10), bg=C_PAGE).pack(side="left")
        year_var = tk.StringVar(value=cur_date[:4] if cur_date else str(today.year))
        ttk.Spinbox(entry_frame, from_=2025, to=2030, width=5,
                    textvariable=year_var, font=(FONT, 11)).pack(side="left", padx=(0, 5))

        tk.Label(entry_frame, text="月", font=(FONT, 10), bg=C_PAGE).pack(side="left")
        month_var = tk.StringVar(value=cur_date[5:7] if cur_date else "12")
        ttk.Spinbox(entry_frame, from_=1, to=12, width=4,
                    textvariable=month_var, font=(FONT, 11)).pack(side="left", padx=(0, 5))

        tk.Label(entry_frame, text="日", font=(FONT, 10), bg=C_PAGE).pack(side="left")
        day_var = tk.StringVar(value=cur_date[8:10] if cur_date else "19")
        ttk.Spinbox(entry_frame, from_=1, to=31, width=4,
                    textvariable=day_var, font=(FONT, 11)).pack(side="left")

        def save():
            try:
                y, m, d = int(year_var.get()), int(month_var.get()), int(day_var.get())
                new_date = date(y, m, d)
                dlg.destroy()
                self._save_settings({"exam_date": new_date.isoformat()})
                self.exam_date = new_date.isoformat()
                if not self.countdown_label.winfo_ismapped():
                    self.countdown_label.pack()
                self._refresh_countdown()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的日期", parent=dlg)

        def clear():
            dlg.destroy()
            self._save_settings({"exam_date": None})
            self.exam_date = None
            self.countdown_label.pack_forget()

        btn_frame = tk.Frame(dlg, bg=C_PAGE)
        btn_frame.pack(pady=(14, 0))
        ttk.Button(btn_frame, text="✓ 确定", command=save, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✗ 取消", command=dlg.destroy, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清除", command=clear, width=10).pack(side="left", padx=5)

    def _refresh_bmi_all(self):
        if hasattr(self, 'progress_tab'):
            self.progress_tab._update_bmi_preview()
            self.progress_tab.refresh_progress()

    # ── 时钟 ──
    def _tick_clock(self):
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%m月%d日 %H:%M"))
        self.root.after(30000, self._tick_clock)

    # ── 倒计时 ──
    def _refresh_countdown(self):
        if self.exam_date:
            try:
                ed = date.fromisoformat(self.exam_date)
                days_left = (ed - date.today()).days
                if days_left < 0:
                    text, color = "🎓 考试已结束", C_SUBTLE
                else:
                    text = f"距考研 {days_left} 天"
                    if days_left <= 30:
                        color = C_RED
                    elif days_left <= 100:
                        color = C_AMBER
                    else:
                        color = C_ACCENT
                self.countdown_label.config(text=text, fg=color)
            except Exception:
                pass
        self.root.after(600000, self._refresh_countdown)


if __name__ == "__main__":
    if is_another_instance_running():
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, "拾光已在运行中", "拾光", 0x40)
        sys.exit(0)
    ShiGuangApp()
