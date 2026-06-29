"""拾光 - 考研时光伴侣 v3.3"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
from datetime import datetime, date

from config import is_another_instance_running, SETTINGS_FILE, TASKS_FILE, GOALS_FILE, RECORDS_FILE, FOCUS_FILE, TRAINING_LOG_FILE, FREE_TIME_FILE
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
from ui.hot_tab import HotTab

# ── UI/UX Pro Max 配色：Flat Design · 薄荷清新 ──
C_PAGE     = "#F0FDFA"   # 页底：薄荷白
C_HEADER   = "#0D9488"   # 顶栏：青绿
C_ACCENT   = "#0D9488"   # 强调：青绿
C_ACCENT_L = "#CCFBF1"   # 强调淡色
C_TEXT     = "#134E4A"   # 正文：深青绿
C_SUBTLE   = "#5E8B87"   # 辅助文字
C_INPUT_BG = "#E6F5F2"   # 输入框底色
C_SIDEBAR  = "#E0F2EF"   # 侧栏
C_RED      = "#EF4444"   # 警示红
C_AMBER    = "#F97316"   # 暖橙强调
C_TOOLBAR  = "#E6F5F2"   # 工具栏
C_TASK_BG  = "#F4FAF8"   # 任务区
C_STUDY_BG = "#ECF7F5"   # 学习区
C_HEALTH_BG= "#FEF8F4"   # 健康区（暖橙底）
C_LINE     = "#D4EDE9"   # 卡片细线
FONT       = "Microsoft YaHei"


class ShiGuangApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("拾光 v3.3")
        self.root.geometry("1440x900")
        self.root.minsize(1300, 750)
        self.root.configure(background=C_PAGE)
        self._setup_style()

        self._build_banner()
        self._build_toolbar()
        self._build_main_layout()

        self.tracker = BuiltinTracker()
        self.tracker.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    # ── Banner ──
    def _build_banner(self):
        banner = tk.Frame(self.root, bg=C_HEADER, height=44)
        banner.pack(fill="x")
        banner.pack_propagate(False)

        tk.Label(banner, text="拾 光", font=(FONT, 16, "bold"),
                 fg="#FFFFFF", bg=C_HEADER).pack(side="left", padx=18, pady=5)

        right_area = tk.Frame(banner, bg=C_HEADER)
        right_area.pack(side="right", padx=14)

        self.exam_date = self._load_settings().get("exam_date")
        self.countdown_label = tk.Label(right_area, text="",
            font=(FONT, 10, "bold"), bg=C_HEADER, fg="#FFFFFF")
        if self.exam_date:
            self.countdown_label.pack(side="left", padx=(0, 10))
        self._refresh_countdown()

        now = datetime.now()
        self.clock_label = tk.Label(right_area,
            text=now.strftime("%m月%d日 %H:%M"),
            font=(FONT, 10), fg="#CCFBF1", bg=C_HEADER)
        self.clock_label.pack(side="left", padx=(0, 8))
        self._tick_clock()

        # Canvas 圆角按钮替代 tk.Button
        self.exam_btn = tk.Canvas(right_area, width=52, height=24,
                                   bg=C_HEADER, highlightthickness=0, cursor="hand2")
        self.exam_btn.pack(side="left")
        self._draw_exam_btn()
        self.exam_btn.bind("<Button-1>", lambda e: self._set_exam_date())
        self.exam_btn.bind("<Enter>", lambda e: self._draw_exam_btn(hover=True))
        self.exam_btn.bind("<Leave>", lambda e: self._draw_exam_btn(hover=False))

        # Canvas 装饰线（teal → mint 渐变暗示）
        accent_line = tk.Canvas(self.root, height=2, bg=C_PAGE, highlightthickness=0)
        accent_line.pack(fill="x")

    # ── 工具栏 ──
    def _build_toolbar(self):
        pass  # 工具栏已整合到标签页

    def _draw_exam_btn(self, hover=False):
        """绘制 Canvas 圆角按钮"""
        c = self.exam_btn
        c.delete("all")
        w, h = 52, 24
        r = 6
        bg = "#0F9688" if hover else "#0B7A70"
        fg = "#FFFFFF" if hover else "#CCFBF1"
        # 圆角矩形
        pts = [r,0, w-r,0, w-r,0, w,0, w,r, w,h-r, w,h, w-r,h,
               r,h, 0,h, 0,h-r, 0,r, 0,0, r,0]
        c.create_polygon(pts, fill=bg, outline="", smooth=True)
        c.create_text(w//2, h//2, text="考试日", font=(FONT, 8),
                      fill=fg, anchor="center")

    # ── 主体：左工右览 ──
    def _build_main_layout(self):
        pw = tk.PanedWindow(self.root, orient="horizontal",
                           bg=C_PAGE, sashwidth=3, sashrelief="flat")
        pw.pack(fill="both", expand=True, padx=8, pady=6)

        # ═══ 左栏 38%：任务 + 专注·热点 ═══
        left = tk.Frame(pw, bg=C_TASK_BG,
                       highlightthickness=1, highlightbackground=C_LINE)
        pw.add(left, minsize=550, stretch="always", width=640)

        # 左上：今日任务
        task_hdr = tk.Frame(left, bg=C_TASK_BG)
        task_hdr.pack(fill="x", padx=10, pady=(8, 0))
        dot1 = tk.Canvas(task_hdr, width=10, height=10, bg=C_TASK_BG, highlightthickness=0)
        dot1.create_oval(2, 2, 8, 8, fill=C_AMBER, outline="")
        dot1.pack(side="left", padx=(0, 6))
        tk.Label(task_hdr, text="今日任务", font=(FONT, 11, "bold"),
                 fg=C_TEXT, bg=C_TASK_BG).pack(side="left")

        self.task_tab = TaskTab(left, self)
        self.task_tab.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        # 左下：专注 + 热点（Notebook）
        nb_left = ttk.Notebook(left)
        nb_left.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.timer_stats_tab = TimerStatsTab(nb_left, self)
        nb_left.add(self.timer_stats_tab, text="  ⏱ 专注统计  ")
        self.hot_tab = HotTab(nb_left, self)
        nb_left.add(self.hot_tab, text="  📰 每日热点  ")

        # ═══ 右栏 62%：学习 + 健康（Notebook）═══
        right = tk.Frame(pw, bg=C_STUDY_BG,
                        highlightthickness=1, highlightbackground=C_LINE)
        pw.add(right, minsize=680, stretch="always")

        nb_right = ttk.Notebook(right)
        nb_right.pack(fill="both", expand=True, padx=4, pady=4)

        self.week_tab = WeekTab(nb_right, self)
        nb_right.add(self.week_tab, text="  📅 周计划表  ")
        self.progress_tab = ProgressTab(nb_right, self)
        nb_right.add(self.progress_tab, text="  📈 训练进度  ")
        self.timetrack_tab = TimeTrackTab(nb_right, self)
        nb_right.add(self.timetrack_tab, text="  📊 时间追踪  ")
        self.ocr_tab = OcrTab(nb_right, self)
        nb_right.add(self.ocr_tab, text="  🔍 文字识别  ")
        self.goal_wizard = SmartGoalWizard(nb_right, self._on_goals_generated)
        nb_right.add(self.goal_wizard, text="  🎯 目标拆解  ")
        nb_right.bind("<<NotebookTabChanged>>", self._on_right_tab_changed)
        self.nb_right = nb_right

    def _on_right_tab_changed(self, ev):
        nb = ev.widget
        cur = nb.tab(nb.select(), "text").strip()
        if "追踪" in cur:
            self.timetrack_tab.refresh()
        elif "训练" in cur:
            self.progress_tab.refresh_progress()

    # ── 目标生成回调 ──
    def _on_goals_generated(self, goals):
        existing = DataManager.load(GOALS_FILE, default=[])
        existing.extend(goals)
        DataManager.save(GOALS_FILE, existing)

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
        style.configure("TButton", font=(FONT, 10), padding=(12, 6))
        style.map("TButton",
                  background=[("active", C_ACCENT_L), ("pressed", C_ACCENT)],
                  foreground=[("active", C_TEXT), ("pressed", "#FFFFFF")],
                  padding=[("pressed", (14, 8)), ("active", (12, 6))],
                  relief=[("pressed", "flat"), ("!pressed", "flat")])
        # 主操作按钮（绿色强调）
        style.configure("Primary.TButton", font=(FONT, 10, "bold"),
                       padding=(16, 7))
        style.map("Primary.TButton",
                  background=[("active", "#0B7A70"), ("pressed", "#096A60")],
                  foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")])
        style.configure("TRadiobutton", font=(FONT, 10), background=C_PAGE)
        style.configure("TEntry", font=(FONT, 10), fieldbackground=C_INPUT_BG,
                       borderwidth=1, relief="solid")
        style.configure("TCombobox", font=(FONT, 10), fieldbackground=C_INPUT_BG)
        style.configure("TSpinbox", font=(FONT, 10), fieldbackground=C_INPUT_BG)
        style.map("TEntry", fieldbackground=[("focus", "#FFFFFF")])
        style.map("TCombobox", fieldbackground=[("focus", "#FFFFFF")])
        style.configure("Treeview", font=(FONT, 10), rowheight=28)
        style.configure("Treeview.Heading", font=(FONT, 10, "bold"))
        style.configure("TNotebook", background=C_PAGE, borderwidth=0)
        style.configure("TNotebook.Tab", font=(FONT, 10), padding=(16, 7))
        style.map("TNotebook.Tab",
                  background=[("selected", C_ACCENT), ("active", C_ACCENT_L),
                             ("!selected", C_SIDEBAR)],
                  foreground=[("selected", "#FFFFFF"), ("active", C_TEXT),
                             ("!selected", C_TEXT)])

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
                dlg.destroy()
                self._save_settings({"exam_date": date(y, m, d).isoformat()})
                self.exam_date = date(y, m, d).isoformat()
                if not self.countdown_label.winfo_ismapped():
                    self.countdown_label.pack(side="left", padx=(0, 10))
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

    def _tick_clock(self):
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%m月%d日 %H:%M"))
        self.root.after(30000, self._tick_clock)

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
                        color = C_ACCENT_L
                self.countdown_label.config(text=text, fg=color)
            except Exception:
                pass
        self.root.after(600000, self._refresh_countdown)

    def check_all_modules(self):
        """每次完成任务后自检所有模块状态。返回问题列表，无问题返回空列表。"""
        issues = []
        tab_modules = {
            "今日任务": "task_tab",
            "周计划表": "week_tab",
            "专注统计": "timer_stats_tab",
            "训练进度": "progress_tab",
            "时间追踪": "timetrack_tab",
            "每日热点": "hot_tab",
        }
        for label, attr in tab_modules.items():
            if not hasattr(self, attr) or getattr(self, attr, None) is None:
                issues.append(f"❌ 缺失模块: {label} ({attr})")
        data_files = {
            "任务数据": (TASKS_FILE,),
            "目标数据": (GOALS_FILE,),
            "记录数据": (RECORDS_FILE,),
            "专注记录": (FOCUS_FILE,),
            "系统设置": (SETTINGS_FILE,),
            "训练日志": (TRAINING_LOG_FILE,),
            "空闲时间": (FREE_TIME_FILE,),
        }
        for label, (path,) in data_files.items():
            try:
                import os
                if os.path.exists(path):
                    DataManager.load(path)
            except Exception as e:
                issues.append(f"❌ 数据损坏: {label} — {e}")
        if not hasattr(self, 'tracker') or self.tracker is None:
            issues.append("❌ 时间追踪器未启动")
        elif not self.tracker._running:
            issues.append("⚠️ 时间追踪器已停止")
        return issues

    def on_close(self):
        self.tracker.stop()
        self.root.destroy()


if __name__ == "__main__":
    if is_another_instance_running():
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "拾光已在运行中", "拾光", 0x40)
        sys.exit(0)
    ShiGuangApp()
