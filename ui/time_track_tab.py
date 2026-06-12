"""Auto-extracted module."""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sqlite3
import threading
import time
from datetime import datetime, date, timedelta
from collections import defaultdict
from config import DATA_DIR, RECORDS_FILE, TRACKER_DB
from data_manager import DataManager

class TimeTrackTab(ttk.Frame):
    CARD_COLORS = ["#4285F4", "#EA4335", "#FBBC04", "#34A853", "#FF6D01", "#46BDC6", "#7B1FA2", "#E91E63"]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._refresh_job = None

        # ── 概览卡片 ──
        cards_frame = ttk.Frame(self)
        cards_frame.pack(fill="x", padx=12, pady=(12, 4))

        self.card_vars = {}
        card_items = [
            ("📊 总时长", "total_time", "#4285F4"),
            ("⚡ 高效时间", "productive_time", "#34A853"),
            ("📱 最常用", "top_app", "#EA4335"),
        ]
        for title, key, color in card_items:
            c = tk.Frame(cards_frame, bg="#FFFFFF", highlightthickness=0)
            c.pack(side="left", fill="both", expand=True, padx=4)
            bar = tk.Frame(c, bg=color, height=3)
            bar.pack(fill="x")
            ttk.Label(c, text=title, font=("Microsoft YaHei", 9), foreground="#888").pack(pady=(8, 2))
            var = tk.StringVar(value="-")
            ttk.Label(c, textvariable=var, font=("Microsoft YaHei", 16, "bold")).pack(pady=(0, 8))
            self.card_vars[key] = var

        # ── 时间段切换 ──
        period_frame = ttk.Frame(self)
        period_frame.pack(fill="x", padx=12, pady=(0, 4))
        self.period_var = tk.StringVar(value="today")
        for text, val in [("今日", "today"), ("本周", "week"), ("总", "all")]:
            ttk.Radiobutton(period_frame, text=text, variable=self.period_var,
                           value=val, command=self.refresh).pack(side="left", padx=(0, 12))

        # ── 应用排行 ──
        self.bar_section = ttk.LabelFrame(self, text="📋 应用排行（今日）", padding=4)
        self.bar_section.pack(fill="both", expand=True, padx=12, pady=4)
        bar_outer = ttk.Frame(self.bar_section)
        bar_outer.pack(fill="both", expand=True)
        self.bar_canvas = tk.Canvas(bar_outer, bg="#FAFAFA", height=300, highlightthickness=0)
        self.bar_canvas.pack(side="left", fill="both", expand=True)
        # 滚轮绑定
        self.bar_canvas.bind("<MouseWheel>", lambda e: self.bar_canvas.yview_scroll(int(-1 * e.delta / 120), "units"))
        # 滚动条创建但不显示（仅用于 yscrollcommand 回调）
        self._bar_sb = ttk.Scrollbar(bar_outer, orient="vertical", command=self.bar_canvas.yview)
        self.bar_canvas.configure(yscrollcommand=self._bar_sb.set)

        # ── 状态栏 ──
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=12, pady=(4, 12))
        self.status_label = ttk.Label(status_frame, text="🔄 正在加载…", font=("Microsoft YaHei", 9), foreground="#888")
        self.status_label.pack(side="left")
        ttk.Button(status_frame, text="🔄 刷新", command=self.refresh).pack(side="right")

    def on_show(self):
        """Tab 显示时调用"""
        self.refresh()
        # 每 30 秒自动刷新
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self._schedule_refresh()

    def on_hide(self):
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None

    def _schedule_refresh(self):
        self.refresh()
        self._refresh_job = self.after(30000, self._schedule_refresh)

    def _period_from_var(self):
        """根据 period_var 返回 SQL WHERE 条件"""
        p = self.period_var.get()
        if p == "today":
            today = datetime.now().strftime("%Y-%m-%d")
            return ("start_time LIKE ?", (today + "%",), "今日")
        elif p == "week":
            return ("start_time >= date('now', '-6 days')", (), "本周")
        else:
            return ("1=1", (), "总")

    def refresh(self):
        """从 SQLite 读取数据并刷新显示"""
        try:
            if not os.path.exists(TRACKER_DB):
                self._set_empty("⏳ 等待数据…（尚无追踪记录）")
                return
            where_sql, where_params, period_label = self._period_from_var()
            conn = sqlite3.connect(TRACKER_DB)

            # 总时长
            cur = conn.execute(
                f"SELECT COALESCE(SUM(duration_seconds),0) FROM usage_records WHERE {where_sql}",
                where_params
            )
            total_sec = cur.fetchone()[0]

            if total_sec == 0:
                conn.close()
                empty_msgs = {"今日": "📭 今日暂无记录", "本周": "📭 本周暂无记录", "总": "📭 暂无记录"}
                self._set_empty(empty_msgs.get(period_label, "📭 暂无记录"))
                return

            # 高效时间
            cur = conn.execute(
                f"SELECT COALESCE(SUM(duration_seconds),0) FROM usage_records WHERE {where_sql} AND productivity_score >= 70",
                where_params
            )
            prod_sec = cur.fetchone()[0]

            # 最常用
            cur = conn.execute(
                f"SELECT app_name, SUM(duration_seconds) as td FROM usage_records WHERE {where_sql} GROUP BY app_name ORDER BY td DESC LIMIT 1",
                where_params
            )
            row = cur.fetchone()
            top_app = row[0] if row else "-"

            # 应用排行 Top 10
            cur = conn.execute(
                f"SELECT app_name, SUM(duration_seconds) as td FROM usage_records WHERE {where_sql} GROUP BY app_name ORDER BY td DESC LIMIT 10",
                where_params
            )
            apps = cur.fetchall()

            conn.close()

            # 更新标题
            self.bar_section.configure(text=f"📋 应用排行（{period_label}）")

            # 更新卡片
            m, s = divmod(total_sec, 60)
            h, m = divmod(m, 60)
            if h > 0:
                self.card_vars["total_time"].set(f"{h}h {m}m")
            else:
                self.card_vars["total_time"].set(f"{m}m {s}s")

            m2, s2 = divmod(prod_sec, 60)
            h2, m2 = divmod(m2, 60)
            if h2 > 0:
                self.card_vars["productive_time"].set(f"{h2}h {m2}m")
            else:
                self.card_vars["productive_time"].set(f"{m2}m {s2}s")

            self.card_vars["top_app"].set(top_app[:14] + "…" if len(top_app) > 15 else top_app)

            # 绘制柱状图
            self._draw_bars(apps, total_sec)

            self.status_label.config(
                text=f"✅ 已更新  {datetime.now().strftime('%H:%M:%S')}", foreground="#888")

        except Exception as e:
            self._set_empty(f"⚠️ 读取失败：{e}")

    def _set_empty(self, msg):
        for v in self.card_vars.values():
            v.set("-")
        self.bar_canvas.delete("all")
        self.bar_canvas.create_text(300, 90, text=msg, font=("Microsoft YaHei", 12), fill="#999")
        self.status_label.config(text=msg, foreground="#999")

    def _draw_bars(self, apps, total_sec):
        cv = self.bar_canvas
        cv.delete("all")
        cv.update_idletasks()
        w = cv.winfo_width()
        if not w or w < 10:
            w = 600
        if not apps:
            return
        max_td = max(r[1] for r in apps)
        # bar_area_w 给右侧留足空间（标签+时长文本）
        bar_area_w = max(80, int(w * 0.55))
        bar_h = 28
        gap = 6
        font = ("Microsoft YaHei", 10)

        for i, (name, td) in enumerate(apps):
            y = 20 + i * (bar_h + gap)
            if max_td > 0:
                ratio = ((1 + td) / (1 + max_td)) ** 0.7
                bw = max(10, int(ratio * bar_area_w))
            else:
                bw = 4
            color = self.CARD_COLORS[i % len(self.CARD_COLORS)]
            short = (name[:16] + "…") if len(name) > 17 else name
            cv.create_text(100, y + bar_h // 2, text=short, font=font, anchor="e", fill="#333")
            cv.create_rectangle(110, y, 110 + bw, y + bar_h, fill=color, outline="", tags="bar")
            m, s = divmod(td, 60)
            hh, m = divmod(m, 60)
            dur = f"{hh}h{m}m" if hh > 0 else f"{m}m{s}s"
            cv.create_text(118 + bw, y + bar_h // 2, text=f"{dur}", font=font, anchor="w", fill="#555")
        # 更新滚动区
        cv.configure(scrollregion=cv.bbox("all"))


