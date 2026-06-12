"""Auto-extracted module."""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, date, timedelta
from config import TASKS_FILE, FREE_TIME_FILE
from data_manager import DataManager

class TaskTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.view_mode = tk.StringVar(value="list")  # list | schedule | week

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 5))
        ttk.Button(toolbar, text="➕ 添加任务", command=self.add_task).pack(side="left")
        ttk.Button(toolbar, text="🗑 删除", command=self.delete_task).pack(side="left")
        ttk.Button(toolbar, text="🔄 清除已完成", command=self.clear_done).pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="⏰ 空闲时间", command=self.set_free_time).pack(side="left")
        ttk.Button(toolbar, text="📅 智能排程", command=self.auto_schedule).pack(side="left")

        self.schedule_info = ttk.Label(toolbar, text="", foreground="gray", font=("", 9))
        self.schedule_info.pack(side="right", padx=(0, 10))
        self.progress_var = tk.StringVar(value="进度：0/0")
        ttk.Label(toolbar, textvariable=self.progress_var, font=("", 10)).pack(side="right")

        # 视图切换按钮
        ttk.Separator(toolbar, orient="vertical").pack(side="right", fill="y", padx=5)
        ttk.Button(toolbar, text="📋 列表 / 🕐 日程 / 📅 周表", command=self.toggle_view).pack(side="right")

        # 容器（两个视图共享同一区域）
        self.view_container = ttk.Frame(self)
        self.view_container.pack(fill="both", expand=True)

        # ── 列表视图 ──
        self.list_frame = ttk.Frame(self.view_container)
        self.task_list = ttk.Treeview(self.list_frame,
                                       columns=("status", "duration", "recommended"),
                                       show="tree headings", selectmode="browse")
        self.task_list.heading("status", text="状态")
        self.task_list.column("status", width=50, anchor="center")
        self.task_list.heading("duration", text="时长")
        self.task_list.column("duration", width=55, anchor="center")
        self.task_list.heading("recommended", text="推荐时间")
        self.task_list.column("recommended", width=115, anchor="center")
        self.task_list.bind("<Double-1>", self.toggle_task)
        list_sb = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.task_list.yview)
        self.task_list.configure(yscrollcommand=list_sb.set)
        self.task_list.pack(side="left", fill="both", expand=True)
        list_sb.pack(side="right", fill="y")
        self.task_list.bind("<MouseWheel>", lambda e: self.task_list.yview_scroll(int(-1 * e.delta / 120), "units"))
        self.task_list.bind("<Double-1>", self.toggle_task)

        # ── 日程视图 ──
        self.schedule_frame = ttk.Frame(self.view_container)
        self.schedule_canvas = tk.Canvas(self.schedule_frame, bg="white", highlightthickness=0)
        sch_sb = ttk.Scrollbar(self.schedule_frame, orient="vertical", command=self.schedule_canvas.yview)
        self.schedule_canvas.configure(yscrollcommand=sch_sb.set)
        self.schedule_canvas.pack(side="left", fill="both", expand=True)
        sch_sb.pack(side="right", fill="y")
        self.schedule_canvas.bind("<Configure>", lambda e: self.draw_schedule())
        self.schedule_canvas.bind("<Button-1>", self.on_schedule_click)
        self.schedule_canvas.bind("<MouseWheel>", lambda e: self.schedule_canvas.yview_scroll(int(-1 * e.delta / 120), "units"))

        # ── 周视图（课程表） ──
        self.week_frame = ttk.Frame(self.view_container)
        self.week_canvas = tk.Canvas(self.week_frame, bg="white", highlightthickness=0)
        wk_sb = ttk.Scrollbar(self.week_frame, orient="vertical", command=self.week_canvas.yview)
        self.week_canvas.configure(yscrollcommand=wk_sb.set)
        self.week_canvas.pack(side="left", fill="both", expand=True)
        wk_sb.pack(side="right", fill="y")
        self.week_canvas.bind("<Configure>", lambda e: self.draw_week())
        self.week_canvas.bind("<Button-1>", self.on_week_click)
        self.week_canvas.bind("<MouseWheel>", lambda e: self.week_canvas.yview_scroll(int(-1 * e.delta / 120), "units"))

        # 默认显示列表
        self.list_frame.pack(fill="both", expand=True)

        self.refresh_task_list()

    def refresh_task_list(self):
        self.task_list.delete(*self.task_list.get_children())
        tasks = DataManager.load(TASKS_FILE)
        today = date.today().isoformat()

        # 只显示今天的任务
        today_tasks = [t for t in tasks if t.get("date", today) == today]
        done = sum(1 for t in today_tasks if t["done"])
        total = len(today_tasks)
        self.progress_var.set(f"进度：{done}/{total}")

        # 显示空闲时间信息
        ft = self._load_free_time()
        if ft and ft.get("windows"):
            windows_str = " | ".join(f"{s}-{e}" for s, e in ft["windows"])
            self.schedule_info.config(text=f"空闲：{windows_str}")
        else:
            self.schedule_info.config(text="")

        for t in today_tasks:
            status = "✅" if t["done"] else "⬜"
            dur = f"{t.get('duration_min', 30)}min" if t.get("duration_min") else "-"
            rec = t.get("recommended_time", "")
            self.task_list.insert("", "end", values=(status, dur, rec),
                                   text=t["name"], iid=t["id"])

        if self.view_mode.get() == "schedule":
            self.draw_schedule()
        elif self.view_mode.get() == "week":
            self.draw_week()

    # ── 视图切换 ─────────────────────────────────────────────
    def toggle_view(self):
        # 隐藏当前
        if self.view_mode.get() == "list":
            self.list_frame.pack_forget()
        elif self.view_mode.get() == "schedule":
            self.schedule_frame.pack_forget()
        else:
            self.week_frame.pack_forget()

        # 切换到下一个
        if self.view_mode.get() == "list":
            self.view_mode.set("schedule")
            self.schedule_frame.pack(fill="both", expand=True)
            self.draw_schedule()
        elif self.view_mode.get() == "schedule":
            self.view_mode.set("week")
            self.week_frame.pack(fill="both", expand=True)
            self.draw_week()
        else:
            self.view_mode.set("list")
            self.list_frame.pack(fill="both", expand=True)
            self.refresh_task_list()

    # ── 日程视图绘制 ─────────────────────────────────────────
    def draw_schedule(self):
        c = self.schedule_canvas
        c.delete("all")
        tasks = DataManager.load(TASKS_FILE)
        today = date.today().isoformat()
        today_tasks = [t for t in tasks if t.get("date", today) == today]

        # 解析推荐时间
        scheduled = []
        unscheduled = []
        for t in today_tasks:
            rec = t.get("recommended_time", "")
            if rec and "-" in rec:
                scheduled.append(t)
            else:
                unscheduled.append(t)

        W = c.winfo_width()
        if W < 200:
            W = 400
        LEFT = 55
        RIGHT_PAD = 10
        BAR_X = LEFT + 5
        BAR_W = W - BAR_X - RIGHT_PAD - 10

        HOUR_TOP = 40
        HOUR_HEIGHT = 60
        START_H = 6
        END_H = 23

        # 颜色
        COLORS = ["#E3F2FD", "#E8F5E9", "#FFF3E0", "#F3E5F5", "#E0F7FA",
                  "#FFF9C4", "#F1F8E9", "#FCE4EC", "#EDE7F6", "#E8EAF6"]
        BLUE = "#1976D2"
        GREEN = "#2E7D32"
        GRAY = "#9E9E9E"
        LIGHT_GRAY = "#F5F5F5"
        DONE_STRIP = "#A5D6A7"

        # 时间解析
        def to_min(tstr):
            h, m = int(tstr.split(':')[0]), int(tstr.split(':')[1])
            return h * 60 + m

        # 绘制每个小时的行
        for hour in range(START_H, END_H + 1):
            y = HOUR_TOP + (hour - START_H) * HOUR_HEIGHT
            # 小时标签
            c.create_text(LEFT - 5, y + HOUR_HEIGHT // 2,
                          text=f"{hour:02d}:00", fill="#666", font=("", 9),
                          anchor="e")
            # 行背景（交替色）
            if hour % 2 == 0:
                c.create_rectangle(BAR_X, y, BAR_X + BAR_W, y + HOUR_HEIGHT,
                                    fill=LIGHT_GRAY, outline="")
            # 分隔线
            c.create_line(LEFT, y, BAR_X + BAR_W, y, fill="#E0E0E0")

        # 底部线
        last_y = HOUR_TOP + (END_H - START_H + 1) * HOUR_HEIGHT
        c.create_line(LEFT, last_y, BAR_X + BAR_W, last_y, fill="#E0E0E0")

        # 绘制空闲时间窗口（浅蓝背景）
        ft = self._load_free_time()
        for s, e in ft.get("windows", []):
            sm = to_min(s)
            em = to_min(e)
            if sm < START_H * 60:
                sm = START_H * 60
            if em > (END_H + 1) * 60:
                em = (END_H + 1) * 60
            y1 = HOUR_TOP + (sm / 60 - START_H) * HOUR_HEIGHT
            y2 = HOUR_TOP + (em / 60 - START_H) * HOUR_HEIGHT
            c.create_rectangle(BAR_X, y1, BAR_X + BAR_W, y2,
                                fill="#E3F2FD", outline="#90CAF9", stipple="gray25")

        # 绘制已排程任务
        color_idx = 0
        for t in scheduled:
            rec = t["recommended_time"]
            s_str, e_str = [x.strip() for x in rec.split("-", 1)]
            sm = to_min(s_str)
            em = to_min(e_str)
            y1 = HOUR_TOP + (sm / 60 - START_H) * HOUR_HEIGHT
            y2 = HOUR_TOP + (em / 60 - START_H) * HOUR_HEIGHT
            if y2 < HOUR_TOP:
                continue

            color = COLORS[color_idx % len(COLORS)]
            dark = "#5C6BC0" if t["done"] else "#1565C0"
            color_idx += 1

            # 任务块背景
            c.create_rectangle(BAR_X, y1 + 1, BAR_X + BAR_W, y2 - 1,
                                fill=DONE_STRIP if t["done"] else color,
                                outline=GREEN if t["done"] else dark,
                                width=2, tags=f"task_{t['id']}")
            # 任务名称
            name = t["name"]
            if len(name) > 30:
                name = name[:28] + "…"
            dur = t.get("duration_min", 30)
            label = f"{'✅' if t['done'] else '⬜'} {name} ({dur}min)"
            c.create_text(BAR_X + 8, y1 + (y2 - y1) // 2,
                          text=label, anchor="w", fill="#333", font=("", 10, "bold"),
                          tags=f"task_{t['id']}")

        # 未排程任务列表（显示在底部）
        unsched_y = last_y + 15
        if unscheduled:
            c.create_text(LEFT, unsched_y, text="📌 未排程任务：", anchor="w",
                          fill=GRAY, font=("", 9, "bold"))
            unsched_y += 20
            for t in unscheduled:
                dur = t.get("duration_min", 30)
                label = f"{'✅' if t['done'] else '⬜'} {t['name']} ({dur}min)"
                c.create_text(LEFT + 10, unsched_y, text=label, anchor="w",
                              fill="#666", font=("", 9))
                unsched_y += 18

        # 设置滚动区域
        c.config(scrollregion=(0, 0, W, max(last_y + 50, unsched_y + 20)))

    def on_schedule_click(self, event):
        """点击日程上的任务 → 切换完成状态"""
        items = self.schedule_canvas.find_overlapping(event.x, event.y, event.x, event.y)
        tags_set = set()
        for i in items:
            for tag in self.schedule_canvas.gettags(i):
                if tag.startswith("task_"):
                    tags_set.add(tag)
        if not tags_set:
            return
        # 取第一个任务
        for tag in sorted(tags_set):
            task_id = tag[5:]
            tasks = DataManager.load(TASKS_FILE)
            for t in tasks:
                if t["id"] == task_id:
                    t["done"] = not t["done"]
                    break
            DataManager.save(TASKS_FILE, tasks)
            self.draw_schedule()
            today_tasks = [t for t in tasks if t.get('date', date.today().isoformat()) == date.today().isoformat()]
            self.progress_var.set(
                f"进度：{sum(1 for t in today_tasks if t['done'])}/{len(today_tasks)}"
            )
            break

    # ── 周视图绘制（课程表） ───────────────────────────────
    def draw_week(self):
        c = self.week_canvas
        c.delete("all")
        tasks = DataManager.load(TASKS_FILE)
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        W = c.winfo_width()
        if W < 200:
            W = 700
        H = c.winfo_height()
        if H < 200:
            H = 500

        # 布局常量
        HEADER_H = 50
        TIME_COL = 45
        START_H = 6
        END_H = 23
        HOUR_H = 55
        CONTENT_TOP = HEADER_H
        CONTENT_W = W - TIME_COL - 5
        DAY_W = max(60, CONTENT_W // 7)
        DAY_GAP = 2

        DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        DAY_COLORS = ["#E3F2FD", "#E8F5E9", "#FFF8E1", "#F3E5F5",
                      "#FFEBEE", "#E0F7FA", "#F1F8E9"]
        TASK_COLORS = ["#42A5F5", "#66BB6A", "#FFA726", "#AB47BC",
                       "#EF5350", "#26C6DA", "#9CCC65"]
        DONE_COLOR = "#A5D6A7"
        GRAY = "#9E9E9E"

        def to_min(tstr):
            h, m = int(tstr.split(':')[0]), int(tstr.split(':')[1])
            return h * 60 + m

        # 绘制表头
        c.create_rectangle(0, 0, W, HEADER_H, fill="#F5F5F5", outline="#E0E0E0")
        # 今天高亮列
        today_weekday = today.weekday()  # 0=周一
        for di, day_name in enumerate(DAYS):
            x = TIME_COL + di * DAY_W
            is_today = (di == today_weekday)
            if is_today:
                c.create_rectangle(x, 0, x + DAY_W, HEADER_H,
                                    fill="#1976D2", outline="#1565C0")
                date_label = (monday + timedelta(days=di)).strftime("%m/%d")
                c.create_text(x + DAY_W // 2, 18, text=f"{day_name} 📍",
                              fill="white", font=("", 11, "bold"))
                c.create_text(x + DAY_W // 2, 37, text=date_label,
                              fill="#E3F2FD", font=("", 9))
            else:
                date_label = (monday + timedelta(days=di)).strftime("%m/%d")
                c.create_text(x + DAY_W // 2, 18, text=day_name,
                              fill="#555", font=("", 11))
                c.create_text(x + DAY_W // 2, 37, text=date_label,
                              fill="#999", font=("", 9))

        # 绘制时间行
        for hour in range(START_H, END_H + 1):
            y = CONTENT_TOP + (hour - START_H) * HOUR_H
            # 时间标签
            c.create_text(TIME_COL // 2, y + HOUR_H // 2,
                          text=f"{hour:02d}:00", fill="#888", font=("", 8))
            # 水平线
            c.create_line(TIME_COL, y, W, y, fill="#E8E8E8")
            # 整点加深
            if hour == 12:
                c.create_line(TIME_COL, y, W, y, fill="#FF9800", width=1,
                              dash=(4, 4))

        # 底部线
        last_y = CONTENT_TOP + (END_H - START_H + 1) * HOUR_H
        c.create_line(TIME_COL, last_y, W, last_y, fill="#E0E0E0")

        # 绘制空闲时间背景
        ft_all = DataManager.load(FREE_TIME_FILE, default={})
        for di in range(7):
            d = monday + timedelta(days=di)
            ds = d.isoformat()
            if ds in ft_all:
                for s, e in ft_all[ds].get("windows", []):
                    sm = to_min(s)
                    em = to_min(e)
                    if sm < START_H * 60:
                        sm = START_H * 60
                    if em > (END_H + 1) * 60:
                        em = (END_H + 1) * 60
                    y1 = CONTENT_TOP + (sm / 60 - START_H) * HOUR_H
                    y2 = CONTENT_TOP + (em / 60 - START_H) * HOUR_H
                    x1 = TIME_COL + di * DAY_W + DAY_GAP
                    x2 = TIME_COL + (di + 1) * DAY_W - DAY_GAP
                    c.create_rectangle(x1, y1, x2, y2,
                                        fill=DAY_COLORS[di], outline="")

        # 绘制每天的任务块
        for di in range(7):
            d = monday + timedelta(days=di)
            ds = d.isoformat()
            day_tasks = [t for t in tasks if t.get("date") == ds]
            x1 = TIME_COL + di * DAY_W + DAY_GAP
            x2 = TIME_COL + (di + 1) * DAY_W - DAY_GAP

            for t in day_tasks:
                rec = t.get("recommended_time", "")
                if not rec or "-" not in rec:
                    continue
                try:
                    s_str, e_str = [x.strip() for x in rec.split("-", 1)]
                    sm = to_min(s_str)
                    em = to_min(e_str)
                except Exception:
                    continue

                y1 = CONTENT_TOP + (sm / 60 - START_H) * HOUR_H
                y2 = CONTENT_TOP + (em / 60 - START_H) * HOUR_H
                if y2 < CONTENT_TOP:
                    continue

                # 块颜色
                bg = DONE_COLOR if t["done"] else TASK_COLORS[di]
                bd = "#4CAF50" if t["done"] else "white"
                tags = f"wtask_{t['id']}"
                c.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y2 - 1,
                                    fill=bg, outline=bd, width=2, tags=tags)
                # 任务名（截断）
                name = t["name"]
                if len(name) > 8:
                    name = name[:7] + "…"
                prefix = "✅" if t["done"] else "⬜"
                c.create_text(x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2,
                              text=f"{prefix}{name}",
                              fill="#333", font=("", 8, "bold"),
                              tags=tags)

        # 滚动区域
        total_h = CONTENT_TOP + (END_H - START_H + 1) * HOUR_H + 20
        c.config(scrollregion=(0, 0, W, total_h))

    def on_week_click(self, event):
        """点击周视图任务块 → 切换完成状态"""
        items = self.week_canvas.find_overlapping(event.x, event.y, event.x, event.y)
        tags_set = set()
        for i in items:
            for tag in self.week_canvas.gettags(i):
                if tag.startswith("wtask_"):
                    tags_set.add(tag)
        if not tags_set:
            return
        for tag in sorted(tags_set):
            task_id = tag[6:]
            tasks = DataManager.load(TASKS_FILE)
            for t in tasks:
                if t["id"] == task_id:
                    t["done"] = not t["done"]
                    break
            DataManager.save(TASKS_FILE, tasks)
            self.draw_week()
            self.refresh_task_list()
            break

    def add_task(self):
        dialog = tk.Toplevel(self)
        dialog.title("添加任务")
        dialog.geometry("350x170")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="任务名称:").pack(pady=(15, 0))
        entry = ttk.Entry(dialog, width=40)
        entry.pack(pady=5, padx=20)
        entry.focus()

        dur_frame = ttk.Frame(dialog)
        dur_frame.pack(pady=(0, 5))
        ttk.Label(dur_frame, text="预计时长:").pack(side="left")
        dur_var = tk.StringVar(value="30")
        ttk.Spinbox(dur_frame, from_=5, to=240, increment=5, textvariable=dur_var, width=5).pack(side="left", padx=(5, 0))
        ttk.Label(dur_frame, text="分钟", foreground="gray").pack(side="left", padx=(3, 0))

        def save():
            name = entry.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入任务名称")
                return
            tasks = DataManager.load(TASKS_FILE)
            task = {"id": SmartGoalWizard._gid(), "name": name,
                     "done": False, "date": date.today().isoformat(),
                     "duration_min": int(dur_var.get())}
            tasks.append(task)
            DataManager.save(TASKS_FILE, tasks)
            self.refresh_task_list()
            dialog.destroy()

        entry.bind("<Return>", lambda e: save())
        ttk.Button(dialog, text="保存", command=save).pack(pady=10)

    def toggle_task(self, event=None):
        sel = self.task_list.selection()
        if not sel:
            return
        task_id = sel[0]
        tasks = DataManager.load(TASKS_FILE)
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = not t["done"]
                break
        DataManager.save(TASKS_FILE, tasks)
        self.refresh_task_list()

    def delete_task(self):
        sel = self.task_list.selection()
        if not sel:
            return
        task_id = sel[0]
        tasks = DataManager.load(TASKS_FILE)
        tasks = [t for t in tasks if t["id"] != task_id]
        DataManager.save(TASKS_FILE, tasks)
        self.refresh_task_list()

    def clear_done(self):
        tasks = DataManager.load(TASKS_FILE)
        today = date.today().isoformat()
        tasks = [t for t in tasks if not (t.get("date", today) == today and t["done"])]
        DataManager.save(TASKS_FILE, tasks)
        self.refresh_task_list()

    # -------- 空闲时间管理 --------
    def _load_free_time(self):
        d = DataManager.load(FREE_TIME_FILE, default={})
        if not isinstance(d, dict):
            d = {}
        today = date.today().isoformat()
        return d.get(today, {"windows": []})

    def _save_free_time(self, windows):
        d = DataManager.load(FREE_TIME_FILE)
        today = date.today().isoformat()
        d[today] = {"windows": windows}
        DataManager.save(FREE_TIME_FILE, d)

    def set_free_time(self):
        """弹出对话框，输入今日空闲时间段"""
        ft = self._load_free_time()
        dlg = tk.Toplevel(self)
        dlg.title("设置今日空闲时间")
        dlg.geometry("420x340")
        dlg.resizable(False, False)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        # 居中
        dlg.update_idletasks()
        pw, ph = self.winfo_toplevel().winfo_width(), self.winfo_toplevel().winfo_height()
        px = self.winfo_toplevel().winfo_rootx() + max(0, (pw - 420) // 2)
        py = self.winfo_toplevel().winfo_rooty() + max(0, (ph - 340) // 2)
        dlg.geometry(f"420x340+{px}+{py}")

        ttk.Label(dlg, text="设置今日空闲时间段（用于智能排程）", font=("", 11, "bold")).pack(pady=(15, 5))
        ttk.Label(dlg, text='格式：HH:MM，每行一个时间段，如 "09:00 - 11:30"', foreground="gray").pack()

        # 列表区
        list_frame = ttk.Frame(dlg)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(8, 5))
        lb = tk.Listbox(list_frame, height=6, font=("", 10))
        lb.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, command=lb.yview)
        lb.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        for s, e in ft.get("windows", []):
            lb.insert("end", f"{s} - {e}")

        # 输入区
        input_frame = ttk.Frame(dlg)
        input_frame.pack(fill="x", padx=20, pady=(0, 5))
        ttk.Label(input_frame, text="开始:").pack(side="left")
        start_var = tk.StringVar(value="09:00")
        ttk.Entry(input_frame, textvariable=start_var, width=7).pack(side="left", padx=(2, 8))
        ttk.Label(input_frame, text="结束:").pack(side="left")
        end_var = tk.StringVar(value="11:00")
        ttk.Entry(input_frame, textvariable=end_var, width=7).pack(side="left", padx=(2, 8))

        def add_win():
            s, e = start_var.get().strip(), end_var.get().strip()
            try:
                # 验证格式
                h1, m1 = divmod(int(s.split(':')[0]) * 60 + int(s.split(':')[1]), 60)
                h2, m2 = divmod(int(e.split(':')[0]) * 60 + int(e.split(':')[1]), 60)
            except Exception:
                messagebox.showerror("格式错误", "请用 HH:MM 格式，如 09:00")
                return
            lb.insert("end", f"{s} - {e}")

        def del_win():
            sel = lb.curselection()
            if sel:
                lb.delete(sel[0])

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill="x", padx=20, pady=(0, 5))
        ttk.Button(btn_frame, text="➕ 添加", command=add_win).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="🗑 删除选中", command=del_win).pack(side="left")

        def on_ok():
            windows = []
            for i in range(lb.size()):
                txt = lb.get(i)
                try:
                    s_part, e_part = [x.strip() for x in txt.split("-", 1)]
                    # 验证
                    sh, sm = int(s_part.split(':')[0]), int(s_part.split(':')[1])
                    eh, em = int(e_part.split(':')[0]), int(e_part.split(':')[1])
                    if not (0 <= sh <= 23 and 0 <= sm <= 59 and 0 <= eh <= 23 and 0 <= em <= 59):
                        raise ValueError
                    windows.append((s_part, e_part))
                except Exception:
                    messagebox.showerror("格式错误", f"时间格式有误：{txt}\n请用 HH:MM - HH:MM 格式")
                    return
            self._save_free_time(windows)
            self.refresh_task_list()
            dlg.destroy()

        ttk.Button(dlg, text="保存", command=on_ok).pack(pady=(0, 15))

    # -------- 智能排程 --------
    def auto_schedule(self):
        """根据空闲时间自动为任务分配推荐完成时间"""
        ft = self._load_free_time()
        windows = ft.get("windows", [])
        if not windows:
            messagebox.showinfo("提示", "请先设置今日空闲时间（⏰ 空闲时间）")
            return

        tasks = DataManager.load(TASKS_FILE)
        today = date.today().isoformat()
        today_tasks = [t for t in tasks if t.get("date", today) == today and not t.get("recommended_time")]

        if not today_tasks:
            messagebox.showinfo("提示", "今日任务已全部排程，或无未完成任务")
            return

        # 将时间字符串转换为分钟数
        def to_min(tstr):
            h, m = int(tstr.split(':')[0]), int(tstr.split(':')[1])
            return h * 60 + m

        def to_str(minutes):
            return f"{minutes // 60:02d}:{minutes % 60:02d}"

        # 合并 & 排序所有空闲窗口
        slots = sorted([(to_min(s), to_min(e)) for s, e in windows])
        # 合并重叠窗口
        merged = []
        for s, e in slots:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append([s, e])

        # 为每个任务分配时间
        slot_idx = 0
        cursor = merged[0][0] if merged else 0
        scheduled = 0

        for t in today_tasks:
            dur = t.get("duration_min", 30)  # 默认30分钟
            while slot_idx < len(merged):
                s, e = merged[slot_idx]
                # cursor 取当前窗口起始和上一个 cursor 的较大值
                cursor = max(cursor, s)
                if cursor + dur <= e:
                    t["recommended_time"] = f"{to_str(cursor)} - {to_str(cursor + dur)}"
                    cursor += dur
                    scheduled += 1
                    break
                else:
                    slot_idx += 1
                    cursor = merged[slot_idx][0] if slot_idx < len(merged) else 0
            else:
                # 没有足够空闲时间了
                break

        DataManager.save(TASKS_FILE, tasks)
        self.refresh_task_list()
        if scheduled < len(today_tasks):
            messagebox.showinfo("排程完成",
                f"已为 {scheduled}/{len(today_tasks)} 个任务分配时间\n"
                f"空闲时间不足，剩余任务未分配")
        else:
            messagebox.showinfo("排程完成", f"已为全部 {scheduled} 个任务分配推荐时间！")


# ============ 专注计时 + 数据统计页 ============