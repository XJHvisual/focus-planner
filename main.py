"""拾光 - 考研时光伴侣 v3.3"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
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
C_PAGE     = "#F8F6F2"
C_HEADER   = "#3D3830"
C_ACCENT   = "#0D7377"
C_ACCENT_L = "#D4EDDA"
C_TEXT     = "#4A4238"
C_SUBTLE   = "#8B8178"
C_INPUT_BG = "#F2EEE6"
C_SIDEBAR  = "#EBE5D9"
C_RED      = "#C44536"
C_AMBER    = "#D4843A"
C_TOOLBAR  = "#F0EDE5"
FONT       = "Microsoft YaHei"


class ShiGuangApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("拾光 v3.3")
        self.root.geometry("1050x750")
        self.root.minsize(900, 620)
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
                 fg="#D4C8B8", bg=C_HEADER).pack(side="left", padx=18, pady=5)

        right_area = tk.Frame(banner, bg=C_HEADER)
        right_area.pack(side="right", padx=14)

        self.exam_date = self._load_settings().get("exam_date")
        self.countdown_label = tk.Label(right_area, text="",
            font=(FONT, 10, "bold"), bg=C_HEADER)
        if self.exam_date:
            self.countdown_label.pack(side="left", padx=(0, 10))
        self._refresh_countdown()

        now = datetime.now()
        self.clock_label = tk.Label(right_area,
            text=now.strftime("%m月%d日 %H:%M"),
            font=(FONT, 10), fg=C_SUBTLE, bg=C_HEADER)
        self.clock_label.pack(side="left", padx=(0, 8))
        self._tick_clock()

        tk.Button(right_area, text="考试日", font=(FONT, 8),
                  bg="#4D4840", fg=C_SUBTLE, bd=0, padx=8, pady=1,
                  activebackground="#5D5850", activeforeground="#C8BFAF",
                  cursor="hand2", command=self._set_exam_date).pack(side="left")

        tk.Frame(self.root, bg=C_ACCENT, height=2).pack(fill="x")

    # ── 工具栏 ──
    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=C_TOOLBAR, height=30)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tools = [
            ("🎯 目标拆解", self._open_goal_wizard),
            ("🔍 文字识别", self._open_ocr),
        ]
        for text, cmd in tools:
            btn = tk.Button(bar, text=text, font=(FONT, 9),
                           bg=C_TOOLBAR, fg=C_TEXT, bd=0,
                           activebackground=C_PAGE, activeforeground=C_ACCENT,
                           padx=12, pady=1, cursor="hand2", command=cmd)
            btn.pack(side="left", padx=(8, 0))

    # ── 主体：上下分区 ──
    def _build_main_layout(self):
        pw = tk.PanedWindow(self.root, orient="vertical",
                           bg=C_PAGE, sashwidth=3, sashrelief="flat")
        pw.pack(fill="both", expand=True)

        # ═══ 上区：今日任务（全宽）═══
        top = tk.Frame(pw, bg=C_PAGE)
        pw.add(top, minsize=180, stretch="always")

        tk.Label(top, text="今日任务", font=(FONT, 11, "bold"),
                 fg=C_TEXT, bg=C_PAGE).pack(anchor="w", padx=14, pady=(6, 0))
        tk.Frame(top, bg=C_ACCENT, height=1).pack(fill="x", padx=14)

        self.task_tab = TaskTab(top, self)
        self.task_tab.pack(fill="both", expand=True, padx=8, pady=4)

        # ═══ 下区：学习 | 健康（左右 Notebook）═══
        bottom = tk.Frame(pw, bg=C_PAGE)
        pw.add(bottom, minsize=300, stretch="always")

        # 左侧 Notebook：学习看板
        nb_learn = ttk.Notebook(bottom)
        nb_learn.pack(side="left", fill="both", expand=True, padx=(4, 2), pady=4)

        self.week_tab = WeekTab(nb_learn, self)
        nb_learn.add(self.week_tab, text="  📅 周计划表  ")
        self.timer_stats_tab = TimerStatsTab(nb_learn, self)
        nb_learn.add(self.timer_stats_tab, text="  ⏱ 专注统计  ")
        nb_learn.bind("<<NotebookTabChanged>>", self._on_learn_tab_changed)

        # 右侧 Notebook：健康数据
        nb_health = ttk.Notebook(bottom)
        nb_health.pack(side="right", fill="both", expand=True, padx=(2, 4), pady=4)

        self.progress_tab = ProgressTab(nb_health, self)
        nb_health.add(self.progress_tab, text="  📈 训练进度  ")
        self.timetrack_tab = TimeTrackTab(nb_health, self)
        nb_health.add(self.timetrack_tab, text="  📊 时间追踪  ")
        nb_health.bind("<<NotebookTabChanged>>", self._on_health_tab_changed)

    def _on_learn_tab_changed(self, ev):
        nb = ev.widget
        cur = nb.tab(nb.select(), "text").strip()
        if "专注" in cur:
            self.timer_stats_tab.refresh_stats()

    def _on_health_tab_changed(self, ev):
        nb = ev.widget
        cur = nb.tab(nb.select(), "text").strip()
        if "追踪" in cur:
            self.timetrack_tab.refresh()
        elif "训练" in cur:
            self.progress_tab.refresh_progress()

    # ── 工具弹窗 ──
    def _open_goal_wizard(self):
        SmartGoalWizard(self.root, self)

    def _open_ocr(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("文字识别")
        dlg.geometry("700x500")
        dlg.transient(self.root)
        dlg.configure(bg=C_PAGE)
        otr = OcrTab(dlg, self)
        otr.pack(fill="both", expand=True)

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
        style.configure("TNotebook", background=C_PAGE, borderwidth=0)
        style.configure("TNotebook.Tab", font=(FONT, 10), padding=(14, 5))
        style.map("TNotebook.Tab",
                  background=[("selected", C_ACCENT), ("!selected", C_SIDEBAR)],
                  foreground=[("selected", "#FFFFFF"), ("!selected", C_TEXT)])

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
                        color = C_ACCENT
                self.countdown_label.config(text=text, fg=color)
            except Exception:
                pass
        self.root.after(600000, self._refresh_countdown)

    def on_close(self):
        self.tracker.stop()
        self.root.destroy()


if __name__ == "__main__":
    if is_another_instance_running():
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "拾光已在运行中", "拾光", 0x40)
        sys.exit(0)
    ShiGuangApp()
