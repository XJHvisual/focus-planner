"""周计划表 - 课程+锻炼智能合并为统一网格"""
import tkinter as tk
from tkinter import ttk
import json, os
from datetime import date, timedelta
from config import DATA_DIR, TASKS_FILE, FITNESS_DETAIL_DATA, COURSES_FILE
from data_manager import DataManager

# 锻炼计划：day -> {title, duration_min}
FITNESS_PLAN = {
    0: {"title": "上肢力量训练（胸+肩+三头）", "duration_min": 60},
    1: {"title": "核心 + 有氧", "duration_min": 40},
    3: {"title": "下肢力量训练", "duration_min": 50},
    4: {"title": "背部力量训练", "duration_min": 60},
    5: {"title": "核心 + 有氧", "duration_min": 40},
    6: {"title": "下肢力量训练 + 拉伸", "duration_min": 60},
}

def _mins(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)

def _fmt(m):
    return f"{m//60:02d}:{m%60:02d}"

def _find_fitness_slot(day_courses, duration_min):
    """为锻炼计划寻找最佳空闲时段，返回 (start_min, end_min)"""
    DAY_START = _mins("08:00")
    DAY_END = _mins("22:00")
    BUFFER = 30  # 课后缓冲时间

    if not day_courses:
        # 全天无课，放在上午
        return (DAY_START + 120, DAY_START + 120 + duration_min)

    courses_sorted = sorted(day_courses, key=lambda c: (c["start"], c["end"]))

    # 收集空闲区间
    free_intervals = []
    cursor = DAY_START

    for c in courses_sorted:
        cs = _mins(c["start"])
        ce = _mins(c["end"])
        if cursor < cs:
            free_intervals.append((cursor, cs))
        cursor = max(cursor, ce)
    if cursor < DAY_END:
        free_intervals.append((cursor, DAY_END))

    # 评分选最佳
    best_score = -1
    best_slot = None

    for i, (fs, fe) in enumerate(free_intervals):
        free_len = fe - fs
        if free_len < duration_min:
            continue

        score = 0
        # 优先度1: 最后一段（傍晚/晚间）
        if i == len(free_intervals) - 1:
            score += 10
        # 优先度2: 不拆分
        if free_len >= duration_min:
            score += 5
        # 优先度3: 长度接近
        ratio = min(duration_min / free_len, 1.0)
        score += int(ratio * 3)

        if score > best_score:
            best_score = score
            # 放置：课后加缓冲，课前减缓冲；中间段居中
            if i > 0 and i < len(free_intervals) - 1:
                start = fs + (free_len - duration_min) // 2
            elif i == 0:
                # 课前：结束时间 = 下节课开始 - 缓冲
                start = fe - duration_min - BUFFER
                if start < fs:
                    start = fs
            else:
                # 课后：开始时间 = 上节课结束 + 缓冲
                start = fs + BUFFER
            if start + duration_min > fe:
                start = fe - duration_min
            if start < fs:
                start = fs
            best_slot = (start, start + duration_min)

    # 无足够空闲 → 用最长区间截断
    if best_slot is None and free_intervals:
        longest = max(free_intervals, key=lambda x: x[1] - x[0])
        best_slot = (longest[0], min(longest[0] + duration_min, longest[1]))

    return best_slot


class WeekTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(5, 0), padx=5)
        ttk.Label(toolbar, text="📅 周计划表", font=("", 13, "bold")).pack(side="left")
        self.week_label = ttk.Label(toolbar, text="", foreground="gray")
        self.week_label.pack(side="left", padx=15)
        self.week_tag_label = ttk.Label(toolbar, text="", foreground="#0D7377", font=("", 10))
        self.week_tag_label.pack(side="left", padx=5)
        ttk.Button(toolbar, text="⬅ 上一周", command=self.prev_week).pack(side="right")
        ttk.Button(toolbar, text="下一周 ➡", command=self.next_week).pack(side="right")
        ttk.Button(toolbar, text="回到本周", command=self.this_week).pack(side="right", padx=(0,5))
        self.week_offset = 0

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * e.delta / 120), "units"))
        self.canvas.bind("<Button-1>", self.on_click)

    def _monday(self):
        today = date.today()
        return today - timedelta(days=today.weekday()) + timedelta(weeks=self.week_offset)

    def prev_week(self): self.week_offset -= 1; self.draw()
    def next_week(self): self.week_offset += 1; self.draw()
    def this_week(self): self.week_offset = 0; self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        monday = self._monday()
        sunday = monday + timedelta(days=6)
        self.week_label.config(text=f"{monday.strftime('%m/%d')} ~ {sunday.strftime('%m/%d')}")

        # 课程加载
        courses_data = DataManager.load(COURSES_FILE)
        all_courses = courses_data.get("courses", []) if isinstance(courses_data, dict) else []
        week_num = monday.isocalendar()[1]
        is_odd_week = (week_num % 2 == 1)
        self.week_tag_label.config(text=f"第{week_num}周 {'[单周]' if is_odd_week else '[双周]'}")

        courses = []
        for course in all_courses:
            weeks = course.get("weeks", "all")
            if weeks == "odd" and not is_odd_week: continue
            if weeks == "even" and is_odd_week: continue
            courses.append(course)

        # ── 算法：为每天插入锻炼块 ──
        # 收集每天的课程起止点
        day_courses_raw = [[] for _ in range(7)]
        for course in courses:
            d = course.get("day", 0)
            if 0 <= d <= 6:
                day_courses_raw[d].append({"start": course["start"], "end": course["end"]})

        fitness_blocks = []  # 合成的锻炼块 [{day, start, end, title, dur}]
        for di in range(7):
            if di in FITNESS_PLAN:
                fp = FITNESS_PLAN[di]
                slot = _find_fitness_slot(day_courses_raw[di], fp["duration_min"])
                if slot:
                    fitness_blocks.append({
                        "day": di,
                        "start": _fmt(slot[0]),
                        "end": _fmt(slot[1]),
                        "title": fp["title"],
                        "duration_min": fp["duration_min"],
                    })

        # ── 统一的事件列表（课程 + 锻炼）──
        all_events = []
        for course in courses:
            all_events.append({"day": course.get("day", 0), "start": course["start"], "end": course["end"],
                               "type": "course", "data": course})
        for fb in fitness_blocks:
            all_events.append({"day": fb["day"], "start": fb["start"], "end": fb["end"],
                               "type": "fitness", "data": fb})

        has_events = len(all_events) > 0

        # 尺寸
        W = max(c.winfo_width(), 650)
        TIME_W, PAD_X, HEADER_H = 60, 4, 52
        N_DAYS, DAY_W = 7, (W - TIME_W - PAD_X * 2) // 7
        DAYS = ["周一","周二","周三","周四","周五","周六","周日"]
        DAY_COLORS = ["#0D7377","#388E3C","#F57C00","#7B1FA2","#D32F2F","#00796B","#558B2F"]
        today = date.today()

        # ── 表头 ──
        for di in range(N_DAYS):
            x0 = TIME_W + PAD_X + di * DAY_W
            d = monday + timedelta(days=di)
            is_today = (d == today)
            bg = "#0D7377" if is_today else "#F0F0F0"
            fg = "white" if is_today else "#555"
            fg2 = "#BBDEFB" if is_today else "#999"
            label = f"{DAYS[di]}📍" if is_today else DAYS[di]
            c.create_rectangle(x0, 4, x0 + DAY_W - 2, HEADER_H - 1, fill=bg, outline="")
            c.create_text(x0 + DAY_W // 2, 18, text=label, fill=fg, font=("Microsoft YaHei", 10, "bold"))
            c.create_text(x0 + DAY_W // 2, 37, text=d.strftime('%m/%d'), fill=fg2, font=("Microsoft YaHei", 8))

        GRID_TOP = HEADER_H + 8
        GRID_BOT = GRID_TOP

        if has_events:
            # 收集所有时间点
            time_points = sorted(set(
                p for ev in all_events for p in (ev["start"], ev["end"])
            ))
            row_info = []
            total_h = 0
            for i in range(len(time_points) - 1):
                t0, t1 = time_points[i], time_points[i + 1]
                rh = max(18, int((_mins(t1) - _mins(t0)) * 2.0))
                row_info.append((t0, total_h, rh, t1))
                total_h += rh
            GRID_BOT = GRID_TOP + total_h

            # 判断每行是否被占（有事件）
            for ti, (t0, row_y, rh, t1) in enumerate(row_info):
                abs_y = GRID_TOP + row_y
                is_last = (ti == len(row_info) - 1)
                has_ev = any(
                    _mins(ev["start"]) <= _mins(t0) and _mins(ev["end"]) >= _mins(t1)
                    for ev in all_events
                )
                next_break = False
                if not is_last:
                    nt0, _, _, nt1 = row_info[ti + 1]
                    next_break = not any(
                        _mins(ev["start"]) <= _mins(nt0) and _mins(ev["end"]) >= _mins(nt1)
                        for ev in all_events
                    )
                if has_ev:
                    c.create_text(TIME_W - 4, abs_y + 3, text=t0, fill="#666", font=("Consolas", 9), anchor="ne")
                    if is_last or next_break:
                        c.create_text(TIME_W - 4, abs_y + rh - 3, text=t1, fill="#999", font=("Consolas", 8), anchor="se")
                else:
                    c.create_rectangle(TIME_W + PAD_X, abs_y, TIME_W + PAD_X + N_DAYS * DAY_W, abs_y + rh,
                                       fill="#F5F5F5", outline="")
                lc = "#D0D0D0" if is_last else "#E8E8E8"
                c.create_line(TIME_W + PAD_X, abs_y, TIME_W + PAD_X + N_DAYS * DAY_W, abs_y, fill=lc)
                for di in range(N_DAYS + 1):
                    c.create_line(TIME_W + PAD_X + di * DAY_W, abs_y, TIME_W + PAD_X + di * DAY_W, abs_y + rh,
                                  fill="#F0F0F0")
            c.create_line(TIME_W + PAD_X, GRID_BOT, TIME_W + PAD_X + N_DAYS * DAY_W, GRID_BOT, fill="#D0D0D0")

            # ── 渲染所有事件块（课程 + 锻炼）──
            for ev in all_events:
                di = ev["day"]
                if di >= N_DAYS: continue
                t0, t1 = ev["start"], ev["end"]
                sr = er = None
                for ti, (rt0, _, _, rt1) in enumerate(row_info):
                    if rt0 == t0: sr = ti
                    if rt1 == t1: er = ti
                if sr is None: continue
                y1 = GRID_TOP + row_info[sr][1]
                y2 = GRID_TOP + row_info[er][1] + row_info[er][2]
                xb = TIME_W + PAD_X + di * DAY_W
                bx1, bx2 = xb + 3, xb + DAY_W - 3
                by1, by2 = y1 + 3, y2 - 3
                bh, bw = by2 - by1, bx2 - bx1

                if ev["type"] == "fitness":
                    # 锻炼块：同课程样式，暖橙色
                    MIN_FIT_H = 45
                    if bh < MIN_FIT_H:
                        expand = (MIN_FIT_H - bh) // 2
                        by1 = max(y1, by1 - expand)
                        by2 = min(y2 + 3, by2 + expand + (MIN_FIT_H - bh) % 2)
                        bh = by2 - by1

                    cc = "#FF9800"
                    tag = f"fit_{di}"
                    r = 6
                    c.create_rectangle(bx1 + r, by1, bx2 - r, by2, fill=cc, outline="", tags=tag)
                    c.create_rectangle(bx1, by1 + r, bx2, by2 - r, fill=cc, outline="", tags=tag)
                    for ox, oy in [(bx1, by1), (bx2 - r*2, by1), (bx1, by2 - r*2), (bx2 - r*2, by2 - r*2)]:
                        c.create_oval(ox, oy, ox + r*2, oy + r*2, fill=cc, outline="", tags=tag)

                    fb = ev["data"]
                    cx = bx1 + (bx2 - bx1) // 2
                    short = fb["title"].split("（")[0] if "（" in fb["title"] else fb["title"]
                    if bh >= 45 and bw >= 70:
                        c.create_text(cx, by1 + bh // 2, text=short, fill="white",
                                      font=("Microsoft YaHei", 10, "bold"), width=bw - 10, tags=tag)
                    else:
                        c.create_text(cx, by1 + bh // 2, text=short, fill="white",
                                      font=("Microsoft YaHei", 8, "bold"), width=bw - 6, tags=tag)
                else:
                    # 课程块：保持原有样式
                    course = ev["data"]
                    cc = course.get("color", DAY_COLORS[di])
                    r = 6
                    tag = ""
                    c.create_rectangle(bx1 + r, by1, bx2 - r, by2, fill=cc, outline="")
                    c.create_rectangle(bx1, by1 + r, bx2, by2 - r, fill=cc, outline="")
                    for ox, oy in [(bx1, by1), (bx2 - r*2, by1), (bx1, by2 - r*2), (bx2 - r*2, by2 - r*2)]:
                        c.create_oval(ox, oy, ox + r*2, oy + r*2, fill=cc, outline="")
                    cx = bx1 + (bx2 - bx1) // 2
                    wt = " [单]" if course.get("weeks") == "odd" else (" [双]" if course.get("weeks") == "even" else "")
                    if bh >= 50 and bw >= 70:
                        c.create_text(cx, by1 + 12, text=course["name"] + wt, fill="white",
                                      font=("Microsoft YaHei", 10, "bold"), anchor="n", width=bw - 10)
                        if course.get("teacher"):
                            c.create_text(cx, by2 - 8, text="👨‍🏫" + course["teacher"], fill="#FFFFFF",
                                          font=("Microsoft YaHei", 9), anchor="s", width=bw - 10)
                    elif bh >= 30:
                        c.create_text(cx, by1 + 6, text=course["name"] + wt, fill="white",
                                      font=("Microsoft YaHei", 9, "bold"), anchor="n", width=bw - 10)
                        if course.get("teacher"):
                            c.create_text(cx, by2 - 5, text=course["teacher"], fill="#FFFFFF",
                                          font=("Microsoft YaHei", 8), anchor="s", width=bw - 10)
                    else:
                        c.create_text(cx, by1 + bh // 2, text=course["name"] + wt, fill="white",
                                      font=("Microsoft YaHei", 8, "bold"), width=bw - 6)

        content_h = GRID_BOT + 20
        c.config(scrollregion=(0, 0, W, content_h))

    def on_click(self, event):
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for i in items:
            for tag in self.canvas.gettags(i):
                if tag.startswith("fit_"):
                    di = int(tag[4:])
                    self.show_fitness_detail(di)
                    return

    def show_fitness_detail(self, di):
        detail = FITNESS_DETAIL_DATA.get(di)
        if not detail: return

        DAYS_CN = ["周一","周二","周三","周四","周五","周六","周日"]
        dlg = tk.Toplevel(self)
        dlg.title(f"🏋️ {DAYS_CN[di]} 锻炼计划")
        dlg.geometry("920x560")
        dlg.transient(self.winfo_toplevel())
        dlg.configure(bg="#F8F6F2")

        hf = tk.Frame(dlg, bg="#F8F6F2")
        hf.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(hf, text=detail["title"], font=("Microsoft YaHei", 13, "bold"),
                 bg="#F8F6F2", fg="#4A4238").pack(side="left")
        sub = tk.Label(dlg, text=detail["subtitle"], font=("Microsoft YaHei", 9),
                        bg="#F8F6F2", fg="#666")
        sub.pack(padx=16, pady=(2, 8))

        list_frame = tk.Frame(dlg, bg="#F8F6F2")
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        canvas = tk.Canvas(list_frame, bg="#F8F6F2", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        inner = tk.Frame(canvas, bg="#F8F6F2")
        canvas.create_window((0, 0), window=inner, anchor="nw")

        for j, (text, w) in enumerate([("序号", 5), ("动作名称", 12), ("组数×次数", 11),
                                        ("详细说明", 48), ("注意事项", 32)]):
            tk.Label(inner, text=text, width=w, font=("Microsoft YaHei", 9, "bold"),
                     bg="#0D7377", fg="#FFFFFF", padx=2, pady=4).grid(row=0, column=j, sticky="nsew")

        for r, (seq, name, sets, desc, note) in enumerate(detail["actions"], 1):
            bg = "#F2EFE8" if r % 2 == 0 else "#F8F6F2"
            tk.Label(inner, text=str(seq), width=5, font=("Microsoft YaHei", 9),
                     bg=bg, anchor="center", padx=2, pady=3).grid(row=r, column=0, sticky="nsew")
            tk.Label(inner, text=name, width=12, font=("Microsoft YaHei", 9),
                     bg=bg, anchor="w", padx=2, pady=3).grid(row=r, column=1, sticky="nsew")
            tk.Label(inner, text=sets, width=11, font=("Microsoft YaHei", 9),
                     bg=bg, anchor="center", padx=2, pady=3).grid(row=r, column=2, sticky="nsew")
            tk.Label(inner, text=desc, font=("Microsoft YaHei", 9),
                     bg=bg, anchor="w", justify="left", padx=4, pady=3,
                     wraplength=380).grid(row=r, column=3, sticky="nsew")
            tk.Label(inner, text=note, font=("Microsoft YaHei", 9),
                     bg=bg, anchor="w", justify="left", padx=4, pady=3,
                     wraplength=260).grid(row=r, column=4, sticky="nsew")

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), "units"))
        dlg.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))
        ttk.Button(tk.Frame(dlg), text="关闭", command=dlg.destroy, width=12).pack(pady=(0, 14))
