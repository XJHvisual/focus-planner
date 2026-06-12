"""FocusPlanner - 专注规划器 v3.1"""
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

class FocusPlannerApp:
    def __init__(self):

        self.root = tk.Tk()
        self.root.title("专注规划器 v3.0")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        # 样式
        self._setup_style()

        # 头部
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=12, pady=(12, 0))
        ttk.Label(header, text="📖 专注规划器",
                  font=("Microsoft YaHei", 18, "bold")).pack(side="left")
        ttk.Label(header, text="考研路上，每一步都算数",
                  foreground="#909090",
                  font=("Microsoft YaHei", 10)).pack(side="left", padx=12)

        # 右侧：时钟 + 倒计时 + 设置按钮
        right_frame = ttk.Frame(header)
        right_frame.pack(side="right")

        # 实时时钟
        now = datetime.now()
        self.clock_label = ttk.Label(right_frame,
            text=now.strftime("%m月%d日 %H:%M:%S"),
            font=("Microsoft YaHei", 13, "bold"), foreground="#333")
        self.clock_label.pack(side="left", padx=(0, 15))
        self._tick_clock()

        # 倒计时（只有设了考试日才显示）
        self.exam_date = self._load_settings().get("exam_date")
        self.countdown_label = ttk.Label(right_frame, text="",
            font=("Microsoft YaHei", 12, "bold"))
        if self.exam_date:
            self.countdown_label.pack(side="left", padx=(0, 8))
        self._refresh_countdown()

        # 设置按钮
        self.settings_btn = ttk.Button(right_frame, text="⚙ 考试日",
            command=self._set_exam_date, width=9)
        self.settings_btn.pack(side="left")

        # 左侧导航 + 右侧内容区 — 统一白底，无缝过渡
        BODY_BG = "#FFFFFF"

        body = tk.Frame(self.root, bg=BODY_BG)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 左侧边栏（同色白底，通过选中态区分）
        sidebar = tk.Frame(body, bg=BODY_BG, width=115, highlightthickness=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Frame(sidebar, bg=BODY_BG, height=6).pack(fill="x")

        # 右侧内容区（同色白底）
        self.content = tk.Frame(body, bg=BODY_BG)
        self.content.pack(side="left", fill="both", expand=True)

        # 创建所有 Tab（作为 content 的子 widget）
        self.goal_tab = GoalTab(self.content, self)
        self.task_tab = TaskTab(self.content, self)
        self.week_tab = WeekTab(self.content, self)
        self.timer_stats_tab = TimerStatsTab(self.content, self)
        self.progress_tab = ProgressTab(self.content, self)
        self.timetrack_tab = TimeTrackTab(self.content, self)

        # 启动内置追踪器
        self.tracker = BuiltinTracker()
        self.tracker.start()

        # 导航按钮
        SIDEBAR_FONT = ("Microsoft YaHei", 10)
        self.nav_btns = {}
        nav_items = [
            ("🎯  目标拆解", self.goal_tab, "goal"),
            ("📝  今日任务", self.task_tab, "task"),
            ("📅  周计划表", self.week_tab, "week"),
            ("⏱📊 专注·统计", self.timer_stats_tab, "timer"),
            ("📈  训练进度", self.progress_tab, "progress"),
            ("📊  时间追踪", self.timetrack_tab, "timetrack"),
        ]
        for i, (label, tab, key) in enumerate(nav_items):
            btn = tk.Button(sidebar, text=label, font=SIDEBAR_FONT,
                           bg=BODY_BG, fg="#5F6368", bd=0,
                           activebackground="#E8F0FE", activeforeground="#1967D2",
                           anchor="w", padx=12, pady=8,
                           cursor="hand2",
                           command=lambda k=key: self._switch_tab(k))
            btn.pack(fill="x", pady=(6 if i == 0 else 0, 0))
            self.nav_btns[key] = btn

        tk.Frame(sidebar, bg=BODY_BG, height=6).pack(fill="x", side="bottom")

        # 默认选中第一个
        self._switch_tab("goal")

        # 启动
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def _switch_tab(self, key):
        """切换左侧导航内容"""
        # 隐藏所有
        for tab in (self.goal_tab, self.task_tab, self.week_tab,
                     self.timer_stats_tab, self.progress_tab,
                     self.timetrack_tab):
            tab.pack_forget()
        # 重置所有按钮样式
        for k, btn in self.nav_btns.items():
            btn.config(bg="#FFFFFF", fg="#5F6368")
        # 高亮当前
        self.nav_btns[key].config(bg="#E8F0FE", fg="#1967D2")
        # 显示对应内容
        tab_map = {
            "goal": self.goal_tab,
            "task": self.task_tab,
            "week": self.week_tab,
            "timer": self.timer_stats_tab,
            "progress": self.progress_tab,
            "timetrack": self.timetrack_tab,
        }
        tab_map[key].pack(fill="both", expand=True)
        # 刷新需要实时数据的 Tab
        if key == "timer":
            self.timer_stats_tab.refresh_stats()
        elif key == "progress":
            self.progress_tab.refresh_progress()
        elif key == "timetrack":
            self.timetrack_tab.refresh()

    def on_close(self):
        self.tracker.stop()
        self.root.destroy()

    # ── 样式 ──
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        FONT = "Microsoft YaHei"
        BG = "#FFFFFF"
        # 全局白底
        style.configure(".", font=(FONT, 10), background=BG, fieldbackground=BG)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", font=(FONT, 10), background=BG)
        style.configure("TLabelframe", background=BG)
        style.configure("TLabelframe.Label", font=(FONT, 10, "bold"), background=BG)
        style.configure("TButton", font=(FONT, 10), padding=(8, 4))
        style.configure("TRadiobutton", font=(FONT, 10), background=BG)
        style.configure("TEntry", font=(FONT, 10), fieldbackground="#F5F6F8",
                       borderwidth=1, relief="solid")
        style.configure("TCombobox", font=(FONT, 10), fieldbackground="#F5F6F8")
        style.configure("TSpinbox", font=(FONT, 10), fieldbackground="#F5F6F8")
        style.map("TEntry", fieldbackground=[("focus", "#FFFFFF")])
        style.map("TCombobox", fieldbackground=[("focus", "#FFFFFF")])
        style.configure("Treeview", font=(FONT, 10), rowheight=26)
        style.configure("Treeview.Heading", font=(FONT, 10, "bold"))
        # 根窗口也设白底
        self.root.configure(background=BG)

    # ── 设置 ──
    def _load_settings(self):
        return DataManager.load(SETTINGS_FILE, default={})

    def _save_settings(self, data):
        DataManager.save(SETTINGS_FILE, data)

    def _set_exam_date(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("设置考试日期")
        dlg.geometry("320x180")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text="请输入考研初试日期：",
                  font=("Microsoft YaHei", 11, "bold")).pack(pady=(18, 10))

        entry_frame = ttk.Frame(dlg)
        entry_frame.pack()

        cur_date = self._load_settings().get("exam_date", "2026-12-19")
        today = date.today()

        ttk.Label(entry_frame, text="年", font=("Microsoft YaHei", 10)).pack(side="left")
        year_var = tk.StringVar(value=cur_date[:4] if cur_date else str(today.year))
        year_entry = ttk.Spinbox(entry_frame, from_=2025, to=2030, width=5,
                                  textvariable=year_var, font=("Microsoft YaHei", 11))
        year_entry.pack(side="left", padx=(0, 5))

        ttk.Label(entry_frame, text="月", font=("Microsoft YaHei", 10)).pack(side="left")
        month_var = tk.StringVar(value=cur_date[5:7] if cur_date else "12")
        month_entry = ttk.Spinbox(entry_frame, from_=1, to=12, width=4,
                                   textvariable=month_var, font=("Microsoft YaHei", 11))
        month_entry.pack(side="left", padx=(0, 5))

        ttk.Label(entry_frame, text="日", font=("Microsoft YaHei", 10)).pack(side="left")
        day_var = tk.StringVar(value=cur_date[8:10] if cur_date else "19")
        day_entry = ttk.Spinbox(entry_frame, from_=1, to=31, width=4,
                                 textvariable=day_var, font=("Microsoft YaHei", 11))
        day_entry.pack(side="left")

        def save():
            try:
                y, m, d = int(year_var.get()), int(month_var.get()), int(day_var.get())
                new_date = date(y, m, d)
                iso = new_date.isoformat()
                dlg.destroy()
                self._save_settings({"exam_date": iso})
                self.exam_date = iso
                if not self.countdown_label.winfo_ismapped():
                    self.countdown_label.pack(side="left", padx=(0, 8),
                                              before=self.settings_btn)
                self._refresh_countdown()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的日期", parent=dlg)

        def clear():
            dlg.destroy()
            self._save_settings({})
            self.exam_date = None
            self.countdown_label.pack_forget()
            self.countdown_label.config(text="")

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=(12, 0))
        ttk.Button(btn_frame, text="✓ 确定", command=save, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✗ 取消", command=dlg.destroy, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清除", command=clear, width=10).pack(side="left", padx=5)

    def _refresh_bmi_all(self):
        """刷新所有BMI"""
        if hasattr(self, 'progress_tab'):
            self.progress_tab._update_bmi_preview()
            self.progress_tab.refresh_progress()

    # ── 实时时钟 ──
    def _tick_clock(self):
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%m月%d日 %H:%M:%S"))
        # 每秒刷新
        self.root.after(1000, self._tick_clock)

    # ── 倒计时 ──
    def _refresh_countdown(self):
        if self.exam_date:
            try:
                ed = date.fromisoformat(self.exam_date)
                days_left = (ed - date.today()).days
                if days_left < 0:
                    text = "🎓 考试已结束"
                    color = "#666"
                else:
                    text = f"⏳ 距考研 {days_left} 天"
                    if days_left <= 30:
                        color = "#F44336"
                    elif days_left <= 90:
                        color = "#FF9800"
                    else:
                        color = "#1976D2"
                self.countdown_label.config(text=text, foreground=color)
            except Exception:
                pass
        # 每10分钟刷新（天级别不需要太频繁）
        self.root.after(600000, self._refresh_countdown)


if __name__ == "__main__":
    if is_another_instance_running():
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, "专注规划器已在运行中", "FocusPlanner", 0x40)
        sys.exit(0)
    FocusPlannerApp()