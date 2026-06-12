"""Auto-extracted module."""
import tkinter as tk
from tkinter import ttk
import json
import os
import threading
import time
from datetime import datetime, date
from collections import defaultdict
from config import DATA_DIR, GOALS_FILE, TASKS_FILE, RECORDS_FILE, FOCUS_FILE, SETTINGS_FILE
from data_manager import DataManager

class TimerStatsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.running = False
        self.paused = False
        self.seconds = 0
        self.thread = None

        # 滚动容器
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg="#FFFFFF", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.inner, anchor="nw", tags="inner")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_canvas_configure(event):
            canvas.itemconfig("inner", width=event.width)
        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _on_canvas_configure)
        self.inner.bind("<Configure>", _on_inner_configure)

        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), "units"))

        # ── 计时区 ──
        timer_section = ttk.LabelFrame(self.inner, text="⏱ 专注计时", padding=15)
        timer_section.pack(fill="x", padx=10, pady=(10, 5))

        preset_frame = ttk.Frame(timer_section)
        preset_frame.pack()
        ttk.Label(preset_frame, text="专注时长：", font=("Microsoft YaHei", 10)).pack(side="left", padx=(0, 10))
        self.time_var = tk.IntVar(value=90)
        for t in [15, 25, 45, 60, 90, 120]:
            ttk.Radiobutton(preset_frame, text=f"{t}分钟", variable=self.time_var, value=t).pack(side="left", padx=3)

        self.timer_label = ttk.Label(timer_section, text="90:00", font=("Consolas", 42, "bold"))
        self.timer_label.pack(pady=15)
        self.status_label = ttk.Label(timer_section, text="就绪", foreground="gray")
        self.status_label.pack()

        btn_frame = ttk.Frame(timer_section)
        btn_frame.pack(pady=10)
        self.btn_start = ttk.Button(btn_frame, text="▶ 开始专注", command=self.start_timer, width=14)
        self.btn_start.pack(side="left", padx=5)
        self.btn_pause = ttk.Button(btn_frame, text="⏸ 暂停", command=self.pause_timer, state="disabled", width=14)
        self.btn_pause.pack(side="left", padx=5)
        self.btn_stop = ttk.Button(btn_frame, text="⏹ 结束", command=self.stop_timer, state="disabled", width=14)
        self.btn_stop.pack(side="left", padx=5)

        self.tip_label = ttk.Label(timer_section, text="", font=("Microsoft YaHei", 11, "bold"), foreground="#4CAF50")
        self.tip_label.pack(pady=(5, 0))

        # ── 统计区 ──
        stats_section = ttk.LabelFrame(self.inner, text="📊 数据概览", padding=12)
        stats_section.pack(fill="x", padx=10, pady=(5, 5))

        cards = ttk.Frame(stats_section)
        cards.pack(fill="x")

        for title, var_name, color in [
            ("目标总数", "total_goals", "#2196F3"),
            ("今日完成率", "completion", "#4CAF50"),
            ("今日专注", "today_focus", "#FF9800"),
            ("总专注", "total_focus", "#9C27B0"),
        ]:
            # 无边框卡片，用色条做顶部分隔
            c = tk.Frame(cards, bg="#FFFFFF", highlightthickness=0)
            c.pack(side="left", fill="both", expand=True, padx=4)
            # 顶部色条
            bar = tk.Frame(c, bg=color, height=3)
            bar.pack(fill="x")
            ttk.Label(c, text=title, font=("Microsoft YaHei", 9),
                      foreground="#888").pack(pady=(8, 2))
            var = tk.StringVar(value="-")
            setattr(self, f"{var_name}_var", var)
            ttk.Label(c, textvariable=var, font=("Microsoft YaHei", 22, "bold"),
                      foreground=color).pack(pady=(0, 8))

        # ── 记录区 ──
        rec_section = ttk.LabelFrame(self.inner, text="📋 最近专注记录", padding=10)
        rec_section.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        rec_frame = ttk.Frame(rec_section)
        rec_frame.pack(fill="both", expand=True)
        cols = ("date", "time", "minutes", "target")
        self.rec_tree = ttk.Treeview(rec_frame, columns=cols, show="headings", height=6)
        self.rec_tree.heading("date", text="日期")
        self.rec_tree.heading("time", text="时间")
        self.rec_tree.heading("minutes", text="分钟")
        self.rec_tree.heading("target", text="目标")
        self.rec_tree.column("date", width=100)
        self.rec_tree.column("time", width=80, anchor="center")
        self.rec_tree.column("minutes", width=80, anchor="center")
        self.rec_tree.column("target", width=80, anchor="center")
        rec_sb = ttk.Scrollbar(rec_frame, orient="vertical", command=self.rec_tree.yview)
        self.rec_tree.configure(yscrollcommand=rec_sb.set)
        self.rec_tree.pack(side="left", fill="both", expand=True)
        rec_sb.pack(side="right", fill="y")
        self.rec_tree.bind("<MouseWheel>", lambda e: self.rec_tree.yview_scroll(int(-1 * e.delta / 120), "units"))

        self.refresh_stats()

        # 递归绑定滚轮：所有内部控件转发给 canvas
        canvas_widget = canvas
        def _bind_scroll_recursive(w):
            try:
                w.bind("<MouseWheel>", lambda e: canvas_widget.yview_scroll(int(-1 * e.delta / 120), "units"))
                for child in w.winfo_children():
                    _bind_scroll_recursive(child)
            except Exception:
                pass
        self.after(100, lambda: _bind_scroll_recursive(self.inner))

    # ────────── 计时方法 ──────────
    def get_total_seconds(self):
        return self.time_var.get() * 60

    def start_timer(self):
        self.running = True
        self.paused = False
        self.seconds = self.time_var.get() * 60
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal")
        self.btn_stop.config(state="normal")
        self.tip_label.config(text="")
        self.thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.thread.start()

    def timer_loop(self):
        while self.running and self.seconds > 0:
            if not self.paused:
                self.after(0, self.update_display)
                time.sleep(1)
                self.seconds -= 1
            else:
                time.sleep(0.1)
        if self.running and self.seconds <= 0:
            self.after(0, self.timer_complete)

    def update_display(self):
        m = self.seconds // 60
        s = self.seconds % 60
        self.timer_label.config(text=f"{m:02d}:{s:02d}")
        self.status_label.config(text="专注中..." if not self.paused else "已暂停")

    def pause_timer(self):
        self.paused = not self.paused
        self.btn_pause.config(text="▶ 继续" if self.paused else "⏸ 暂停")
        self.update_display()

    def stop_timer(self):
        elapsed = self.get_total_seconds() - self.seconds
        self._save_record(elapsed)
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.timer_label.config(text=f"{self.time_var.get():02d}:00")
        self.status_label.config(text="已结束")
        focus_log = DataManager.load(FOCUS_FILE, {})
        today = date.today().isoformat()
        focus_log[today] = focus_log.get(today, 0) + elapsed
        DataManager.save(FOCUS_FILE, focus_log)
        self.refresh_stats()
        if self.seconds <= 0:
            self.tip_label.config(text="🎉 目标完成！可以去续火花啦～")

    def timer_complete(self):
        self._save_record(self.get_total_seconds())
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.timer_label.config(text="00:00")
        self.status_label.config(text="完成！")
        self.tip_label.config(text="🎉 目标完成！可以去续火花啦～")
        focus_log = DataManager.load(FOCUS_FILE, {})
        today = date.today().isoformat()
        focus_log[today] = focus_log.get(today, 0) + self.get_total_seconds()
        DataManager.save(FOCUS_FILE, focus_log)
        self.refresh_stats()

    def _save_record(self, elapsed_sec):
        records = DataManager.load(RECORDS_FILE)
        records.append({
            "date": date.today().isoformat(),
            "minutes": round(elapsed_sec / 60, 1),
            "duration_sec": elapsed_sec,
            "time": datetime.now().strftime("%H:%M:%S"),
            "target_min": self.time_var.get()
        })
        DataManager.save(RECORDS_FILE, records)

    # ────────── 统计方法 ──────────
    def refresh_stats(self):
        goals = DataManager.load(GOALS_FILE)
        tasks = DataManager.load(TASKS_FILE)
        records = DataManager.load(RECORDS_FILE)
        focus_log = DataManager.load(FOCUS_FILE, {})
        today = date.today().isoformat()

        self.total_goals_var.set(str(len(goals)))

        today_tasks = [t for t in tasks if t.get("date", today) == today]
        if today_tasks:
            done = sum(1 for t in today_tasks if t["done"])
            rate = round(done / len(today_tasks) * 100)
            self.completion_var.set(f"{rate}%")
        else:
            self.completion_var.set("-")

        today_sec = focus_log.get(today, 0)
        h = today_sec // 3600
        m = (today_sec % 3600) // 60
        self.today_focus_var.set(f"{h}h{m}m" if h > 0 else f"{m}分钟")

        total_sec = sum(focus_log.values())
        total_h = round(total_sec / 3600, 1)
        self.total_focus_var.set(f"{total_h}小时")

        self.rec_tree.delete(*self.rec_tree.get_children())
        for r in reversed(records[-20:]):
            self.rec_tree.insert("", "end",
                values=(r["date"], r.get("time", ""),
                        f'{r["minutes"]}分钟',
                        f'{r.get("target_min", "-")}分钟'))


# ============ 主程序 ============
# ============ 周计划表页 ============