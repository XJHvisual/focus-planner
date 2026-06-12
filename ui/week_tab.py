"""Auto-extracted module."""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, date, timedelta
from config import DATA_DIR, GOALS_FILE, TASKS_FILE, FITNESS_DETAIL_DATA
from data_manager import DataManager

class WeekTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(5, 0), padx=5)
        ttk.Label(toolbar, text="📅 本周计划表", font=("", 13, "bold")).pack(side="left")
        self.week_label = ttk.Label(toolbar, text="", foreground="gray")
        self.week_label.pack(side="left", padx=15)
        ttk.Button(toolbar, text="⬅ 上一周", command=self.prev_week).pack(side="right")
        ttk.Button(toolbar, text="下一周 ➡", command=self.next_week).pack(side="right")
        ttk.Button(toolbar, text="回到本周", command=self.this_week).pack(side="right", padx=(0,5))

        self.week_offset = 0
        self._header_y = 0  # 追踪表头当前 y 坐标

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<MouseWheel>", lambda e: self._on_yscroll("scroll", -1 * e.delta / 120, "units"))
        self.canvas.bind("<Motion>", self.on_hover)
        self.canvas.bind("<Leave>", self.on_leave)
        self._last_hover_di = None  # 当前悬停的日期列索引

    def _on_yscroll(self, *args):
        """滚动时锁定表头在可视区顶部"""
        self.canvas.yview(*args)
        # 移动表头到当前可视区顶部
        new_y = self.canvas.canvasy(0)
        if new_y != self._header_y:
            self.canvas.move("header", 0, new_y - self._header_y)
            self._header_y = new_y

    def on_hover(self, event):
        """鼠标移到日期头上方时变手型+高亮"""
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        found_di = None
        for i in items:
            for tag in self.canvas.gettags(i):
                if tag.startswith("wkh_") or tag.startswith("wkt_fit_"):
                    found_di = int(tag.split("_")[-1])
                    break
            if found_di is not None:
                break

        if found_di is not None:
            self.canvas.config(cursor="hand2")
            if found_di != self._last_hover_di:
                self._unhighlight_header()
                self._highlight_header(found_di)
                self._last_hover_di = found_di
        else:
            if self._last_hover_di is not None:
                self._unhighlight_header()
                self._last_hover_di = None
            if self.canvas.cget("cursor") != "arrow":
                self.canvas.config(cursor="arrow")

    def _highlight_header(self, di):
        """高亮指定列的表头（浅蓝色背景矩形）"""
        c = self.canvas
        W = max(c.winfo_width(), 700)
        DAY_W = (W - 8) // 7
        x = di * DAY_W
        c.create_rectangle(x + 2, 3, x + DAY_W - 2, 41,
                          fill="#E3F2FD", outline="", tags="_hover")
        c.tag_lower("_hover", "header")

    def _unhighlight_header(self):
        """取消高亮"""
        self.canvas.delete("_hover")

    def on_leave(self, event):
        """鼠标离开画布时恢复光标"""
        if self._last_hover_di is not None:
            self._unhighlight_header()
            self._last_hover_di = None
        self.canvas.config(cursor="arrow")

    def _monday(self):
        today = date.today()
        return today - timedelta(days=today.weekday()) + timedelta(weeks=self.week_offset)

    def prev_week(self):
        self.week_offset -= 1
        self.draw()

    def next_week(self):
        self.week_offset += 1
        self.draw()

    def this_week(self):
        self.week_offset = 0
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        self._header_y = 0  # 重置表头追踪
        monday = self._monday()
        sunday = monday + timedelta(days=6)
        self.week_label.config(text=f"{monday.strftime('%m/%d')} ~ {sunday.strftime('%m/%d')}")

        tasks = DataManager.load(TASKS_FILE)

        W = max(c.winfo_width(), 700)
        HEADER_H = 44
        DAY_W = (W - 8) // 7
        total_w = 7 * DAY_W + 4
        # 用实际画布宽设滚动区,内容不裁切
        if total_w > W:
            W = total_w
        CARD_H = 70
        CARD_PAD = 3

        DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        ACCENT = ["#4285F4", "#34A853", "#FBBC04", "#A855F7",
                  "#EA4335", "#00897B", "#7CB342"]
        LIGHT = ["#D2E3FC", "#CEEAD6", "#FEEFC3", "#E8D5F9",
                 "#F9D7D7", "#B2DFDB", "#DCEDC8"]

        today = date.today()

        # ── 表头（tag="header"，随滚动锁定在顶部）──
        c.create_rectangle(0, 0, total_w, HEADER_H, fill="#F8F9FA", outline="", tags="header")
        for di in range(7):
            x = di * DAY_W
            d = monday + timedelta(days=di)
            is_today = (d == today)
            ds = d.isoformat()
            day_tasks = [t for t in tasks if t.get("date") == ds]
            total = len(day_tasks)
            done = sum(1 for t in day_tasks if t["done"])
            count_str = f" {done}/{total}" if total > 0 else ""
            htag = f"wkh_{di}"
            col_h = "#4285F4" if is_today else "#F0F0F0"
            fg_h = "white" if is_today else "#555"
            fg2 = "#D2E3FC" if is_today else "#999"
            label = f"{DAYS[di]} 📍" if is_today else DAYS[di]
            c.create_rectangle(x + 2, 3, x + DAY_W - 2, HEADER_H - 3,
                                fill=col_h, outline="", tags=(htag, "header"))
            c.create_text(x + DAY_W // 2, 15, text=label,
                          fill=fg_h, font=("Microsoft YaHei", 10, "bold"), tags=(htag, "header"))
            c.create_text(x + DAY_W // 2, 32,
                          text=f"{d.strftime('%m/%d')}{count_str}",
                          fill=fg2, font=("Microsoft YaHei", 8), tags=(htag, "header"))

        # ── 任务卡片 ──
        max_rows = 0
        for di in range(7):
            d = monday + timedelta(days=di)
            ds = d.isoformat()
            day_tasks = [t for t in tasks if t.get("date") == ds]
            day_tasks.sort(key=lambda t: t.get("recommended_time", "23:59"))
            x0 = di * DAY_W

            has_fitness = (di in FITNESS_DETAIL_DATA)
            day_rows = len(day_tasks) + (1 if has_fitness else 0)
            if day_rows > max_rows:
                max_rows = day_rows

            for row, t in enumerate(day_tasks):
                by1 = HEADER_H + row * (CARD_H + CARD_PAD) + 2
                by2 = by1 + CARD_H
                bx1 = x0 + 4
                bx2 = x0 + DAY_W - 4
                tags = f"wkt_{t['id']}"

                if t["done"]:
                    bg = LIGHT[di]
                    fg = "#555"
                    bar_clr = "#A5D6A7"
                else:
                    bg = ACCENT[di]
                    fg = "white"
                    bar_clr = ACCENT[di]

                c.create_rectangle(bx1, by1, bx2, by2,
                                    fill=bg, outline="#E8E8E8", tags=tags)
                c.create_rectangle(bx1, by1, bx1 + 4, by2,
                                    fill=bar_clr, outline="", tags=tags)
                rec = t.get("recommended_time", "")
                time_str = rec.replace(" - ", "-") if rec else ""
                dur = t.get("duration_min", "")
                dur_str = f"  {dur}min" if dur else ""
                c.create_text(bx1 + 10, by1 + 6,
                              text=f"{time_str}{dur_str}", anchor="w",
                              fill=fg, font=("Microsoft YaHei", 7), tags=tags)
                c.create_text(bx1 + 10, by1 + CARD_H // 2 + 8,
                              text=t["name"], anchor="w",
                              fill=fg, font=("Microsoft YaHei", 9, "bold"),
                              width=bx2 - bx1 - 16, tags=tags)
                if t["done"]:
                    c.create_text(bx2 - 10, by1 + CARD_H // 2,
                                  text="✅", anchor="e",
                                  font=("Microsoft YaHei", 11), tags=tags)

            # 健身训练卡片（粉色系，与普通任务区分）
            if has_fitness:
                fit_row = len(day_tasks)
                by1 = HEADER_H + fit_row * (CARD_H + CARD_PAD) + 2
                by2 = by1 + CARD_H
                bx1 = x0 + 4
                bx2 = x0 + DAY_W - 4
                ftag = f"wkt_fit_{di}"
                fit_data = FITNESS_DETAIL_DATA[di]
                short_title = fit_data["title"].split("：", 1)[1] if "：" in fit_data["title"] else fit_data["title"]
                c.create_rectangle(bx1, by1, bx2, by2,
                                    fill="#FFF3E0", outline="#FFB74D", tags=ftag)
                c.create_rectangle(bx1, by1, bx1 + 4, by2,
                                    fill="#FF9800", outline="", tags=ftag)
                c.create_text(bx1 + 10, by1 + 6,
                              text="🏋️ 健身", anchor="w",
                              fill="#E65100", font=("Microsoft YaHei", 7), tags=ftag)
                c.create_text(bx1 + 10, by1 + CARD_H // 2 + 8,
                              text=short_title, anchor="w",
                              fill="#E65100", font=("Microsoft YaHei", 8),
                              width=bx2 - bx1 - 16, tags=ftag)

        content_h = HEADER_H + 2 + max_rows * (CARD_H + CARD_PAD) + 20
        c.config(scrollregion=(0, 0, W, content_h))

        # 表头立即对齐到当前可视区顶部
        top_y = c.canvasy(0)
        self._header_y = top_y
        c.move("header", 0, top_y)

    def on_click(self, event):
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)

        # 检查是否点了日期头
        for i in items:
            for tag in self.canvas.gettags(i):
                if tag.startswith("wkh_"):
                    di = int(tag[4:])
                    d = self._monday() + timedelta(days=di)
                    self.show_day_detail(d)
                    return

        # 检查是否点了健身卡片
        for i in items:
            for tag in self.canvas.gettags(i):
                if tag.startswith("wkt_fit_"):
                    di = int(tag[8:])
                    d = self._monday() + timedelta(days=di)
                    self.show_day_detail(d)
                    return

        # 检查是否点了任务块
        for i in items:
            for tag in self.canvas.gettags(i):
                if tag.startswith("wkt_"):
                    tid = tag[4:]
                    tasks = DataManager.load(TASKS_FILE)
                    for t in tasks:
                        if t["id"] == tid:
                            t["done"] = not t["done"]
                            break
                    DataManager.save(TASKS_FILE, tasks)
                    self.draw()
                    self.app.task_tab.refresh_task_list()
                    return

    def _show_fitness_detail(self, dlg, wd):
        """在弹窗中展示健身训练详细动作表（支持文本换行）"""
        detail = FITNESS_DETAIL_DATA.get(wd)
        if not detail:
            return False

        # 更新标题为健身主题
        for widget in dlg.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(text=detail["title"])
                        break
                break

        # 副标题
        sub = tk.Label(dlg, text=detail["subtitle"], font=("Microsoft YaHei", 9),
                        bg="#FFFFFF", fg="#666")
        sub.pack(padx=16, pady=(2, 8))

        # Canvas + Frame 手动绘制表格
        list_frame = tk.Frame(dlg, bg="#FFFFFF")
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        canvas = tk.Canvas(list_frame, bg="#FFFFFF", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        inner = tk.Frame(canvas, bg="#FFFFFF")
        canvas.create_window((0, 0), window=inner, anchor="nw")

        # 表头
        header_bg = "#1976D2"
        header_fg = "#FFFFFF"
        tk.Label(inner, text="序号", width=5, font=("Microsoft YaHei", 9, "bold"),
                 bg=header_bg, fg=header_fg, padx=2, pady=4).grid(row=0, column=0, sticky="nsew")
        tk.Label(inner, text="动作名称", width=12, font=("Microsoft YaHei", 9, "bold"),
                 bg=header_bg, fg=header_fg, padx=2, pady=4).grid(row=0, column=1, sticky="nsew")
        tk.Label(inner, text="组数×次数", width=11, font=("Microsoft YaHei", 9, "bold"),
                 bg=header_bg, fg=header_fg, padx=2, pady=4).grid(row=0, column=2, sticky="nsew")
        tk.Label(inner, text="详细说明", width=48, font=("Microsoft YaHei", 9, "bold"),
                 bg=header_bg, fg=header_fg, padx=4, pady=4).grid(row=0, column=3, sticky="nsew")
        tk.Label(inner, text="注意事项", width=32, font=("Microsoft YaHei", 9, "bold"),
                 bg=header_bg, fg=header_fg, padx=4, pady=4).grid(row=0, column=4, sticky="nsew")

        # 数据行
        for r, (seq, name, sets, desc, note) in enumerate(detail["actions"], start=1):
            row_bg = "#F8F9FA" if r % 2 == 0 else "#FFFFFF"
            tk.Label(inner, text=str(seq), width=5, font=("Microsoft YaHei", 9),
                     bg=row_bg, anchor="center", padx=2, pady=3).grid(row=r, column=0, sticky="nsew")
            tk.Label(inner, text=name, width=12, font=("Microsoft YaHei", 9),
                     bg=row_bg, anchor="w", padx=2, pady=3).grid(row=r, column=1, sticky="nsew")
            tk.Label(inner, text=sets, width=11, font=("Microsoft YaHei", 9),
                     bg=row_bg, anchor="center", padx=2, pady=3).grid(row=r, column=2, sticky="nsew")
            lbl_desc = tk.Label(inner, text=desc, font=("Microsoft YaHei", 9),
                               bg=row_bg, anchor="w", justify="left",
                               padx=4, pady=3, wraplength=380)
            lbl_desc.grid(row=r, column=3, sticky="nsew")
            lbl_note = tk.Label(inner, text=note, font=("Microsoft YaHei", 9),
                               bg=row_bg, anchor="w", justify="left",
                               padx=4, pady=3, wraplength=260)
            lbl_note.grid(row=r, column=4, sticky="nsew")

        for col in range(5):
            inner.columnconfigure(col, weight=1 if col >= 3 else 0)

        def _configure_inner(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _configure_inner)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * event.delta / 120), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def _on_destroy():
            canvas.unbind_all("<MouseWheel>")
        dlg.bind("<Destroy>", lambda e: _on_destroy())

        # 底部按钮
        btn_frame = tk.Frame(dlg, bg="#FFFFFF")
        btn_frame.pack(pady=(0, 14))
        ttk.Button(btn_frame, text="关闭", command=dlg.destroy, width=12).pack()
        return True

    def show_day_detail(self, day_date):
        """弹出某一天的详细计划（含健身训练详情）"""
        DAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        wd = day_date.weekday()
        title = f"{DAYS_CN[wd]} {day_date.strftime('%m月%d日')}"

        dlg = tk.Toplevel(self)
        dlg.title(f"📅 {title}")
        dlg.geometry("920x560")
        dlg.transient(self.winfo_toplevel())
        dlg.configure(bg="#FFFFFF")

        # 标题
        hf = tk.Frame(dlg, bg="#FFFFFF")
        hf.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(hf, text=f"📅 {title}", font=("Microsoft YaHei", 13, "bold"),
                 bg="#FFFFFF", fg="#333").pack(side="left")

        # 检查是否有健身训练详情数据
        if self._show_fitness_detail(dlg, wd):
            return

        # 无健身详情时显示普通任务列表
        list_frame = tk.Frame(dlg, bg="#FFFFFF")
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        cols = ("time", "name", "dur", "status")
        tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        tree.heading("time", text="时间")
        tree.heading("name", text="任务")
        tree.heading("dur", text="时长")
        tree.heading("status", text="")
        tree.column("time", width=85)
        tree.column("name", width=180)
        tree.column("dur", width=60, anchor="center")
        tree.column("status", width=40, anchor="center")
        tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.bind("<MouseWheel>", lambda e: tree.yview_scroll(int(-1 * e.delta / 120), "units"))

        tasks = DataManager.load(TASKS_FILE)
        ds = day_date.isoformat()
        day_tasks = [t for t in tasks if t.get("date") == ds]
        day_tasks.sort(key=lambda t: t.get("recommended_time", "23:59"))

        for t in day_tasks:
            rec = t.get("recommended_time", "-")
            dur = f"{t.get('duration_min', 30)}min"
            status = "✅" if t["done"] else "⬜"
            tree.insert("", "end", iid=t["id"], values=(rec, t["name"], dur, status))

        # 双击切换完成
        def toggle_task(event):
            sel = tree.selection()
            if not sel:
                return
            tid = sel[0]
            tasks = DataManager.load(TASKS_FILE)
            for t in tasks:
                if t["id"] == tid:
                    t["done"] = not t["done"]
                    break
            DataManager.save(TASKS_FILE, tasks)
            tree.delete(*tree.get_children())
            for t in tasks:
                if t.get("date") == ds:
                    rec = t.get("recommended_time", "-")
                    dur = f"{t.get('duration_min', 30)}min"
                    status = "✅" if t["done"] else "⬜"
                    tree.insert("", "end", iid=t["id"], values=(rec, t["name"], dur, status))
            self.draw()
            self.app.task_tab.refresh_task_list()

        tree.bind("<Double-1>", toggle_task)

        # 底部按钮
        btn_frame = tk.Frame(dlg, bg="#FFFFFF")
        btn_frame.pack(pady=(0, 14))
        ttk.Button(btn_frame, text="关闭", command=dlg.destroy, width=12).pack()


# ============ 训练进度页 ============
TRACKER_DB = os.path.join(DATA_DIR, "tracker_v2.db")


# ============ 🕐 内置前台窗口追踪器（替代 AppTimeTracker V2） ============