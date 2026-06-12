"""Goal wizards — SmartGoalWizard and Wizard408."""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
from datetime import datetime, date
from config import DATA_DIR, GOALS_FILE, FITNESS_DETAIL_DATA, SETTINGS_FILE
from data_manager import DataManager

class SmartGoalWizard(tk.Toplevel):
    def __init__(self, parent, on_generate, mode="generic"):
        super().__init__(parent)
        self.mode = mode
        self.title("考研目标智能拆解")
        self.geometry("500x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        # 居中
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px = parent.winfo_rootx() + max(0, (pw - 500) // 2)
        py = parent.winfo_rooty() + max(0, (ph - 450) // 2)
        self.geometry(f"500x450+{px}+{py}")
        self.on_generate = on_generate
        self.pages = []
        self.current_page = 0
        self.data = {}

        self.header = ttk.Label(self, text="第 1 步 / 3 步", font=("", 11, "bold"))
        self.header.pack(pady=(15, 5))

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True, padx=30, pady=10)

        self.btn_frame = ttk.Frame(self)
        self.btn_frame.pack(fill="x", padx=30, pady=(0, 15))

        self.btn_prev = ttk.Button(self.btn_frame, text="上一步", command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left")
        self.btn_next = ttk.Button(self.btn_frame, text="下一步", command=self.next_page)
        self.btn_next.pack(side="right")

        self.create_page_1()
        self.show_page(0)

    def create_page_1(self):
        f = ttk.Frame(self.container)
        ttk.Label(f, text="基本信息", font=("", 12, "bold")).pack(anchor="w", pady=(0, 10))

        for label, key in [("目标院校:", "school"), ("目标专业:", "major"),
                            ("目标分数:", "score"), ("当前年级:", "grade")]:
            row = ttk.Frame(f)
            row.pack(fill="x", pady=5)
            ttk.Label(row, text=label, width=10).pack(side="left")
            entry = ttk.Entry(row, width=30)
            entry.pack(side="left", fill="x", expand=True)
            setattr(self, f"entry_{key}", entry)

        self.pages.append(f)

    def create_page_2(self):
        f = ttk.Frame(self.container)
        ttk.Label(f, text="各科目标分数", font=("", 12, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(f, text="（留空表示暂未确定）", foreground="gray").pack(anchor="w", pady=(0, 5))

        self.subjects = ["政治", "英语", "数学", "专业课"]
        self.subject_entries = {}
        for sub in self.subjects:
            row = ttk.Frame(f)
            row.pack(fill="x", pady=5)
            ttk.Label(row, text=f"{sub}:", width=10).pack(side="left")
            entry = ttk.Entry(row, width=15)
            entry.pack(side="left")
            ttk.Label(row, text="分", foreground="gray").pack(side="left", padx=(5, 0))
            self.subject_entries[sub] = entry

        self.pages.append(f)

    def create_page_3(self):
        f = ttk.Frame(self.container)
        ttk.Label(f, text="复习计划", font=("", 12, "bold")).pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(f)
        row.pack(fill="x", pady=5)
        ttk.Label(row, text="开始复习:", width=10).pack(side="left")
        self.start_month_var = tk.StringVar(value="3月")
        month_combo = ttk.Combobox(row, textvariable=self.start_month_var, width=10,
                                    values=[f"{i}月" for i in range(1, 13)])
        month_combo.pack(side="left", padx=(0, 10))

        self.start_year_var = tk.StringVar(value=str(date.today().year))
        year_combo = ttk.Combobox(row, textvariable=self.start_year_var, width=8,
                                   values=[str(date.today().year + i) for i in range(3)])
        year_combo.pack(side="left")
        ttk.Label(row, text="年", foreground="gray").pack(side="left")

        ttk.Label(f, text="",
                  foreground="gray",
                  wraplength=400).pack(anchor="w", pady=(20, 0))
        ttk.Label(f, text="系统将自动生成：长期目标 → 年度目标 → 月目标 → 周目标 → 日目标",
                  foreground="gray", wraplength=400).pack(anchor="w", pady=(5, 0))

        self.pages.append(f)

    def show_page(self, idx):
        for p in self.pages:
            p.pack_forget()
        self.pages[idx].pack(fill="both", expand=True)
        self.header.config(text=f"第 {idx + 1} 步 / 3 步")
        self.btn_prev.config(state="normal" if idx > 0 else "disabled")
        text = "生成目标" if idx == 2 else "下一步"
        self.btn_next.config(text=text)

    def next_page(self):
        if self.current_page < 2:
            self.current_page += 1
            if self.current_page == 1 and len(self.pages) < 2:
                self.create_page_2()
            elif self.current_page == 2 and len(self.pages) < 3:
                self.create_page_3()
            self.show_page(self.current_page)
        else:
            self.generate()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_page(self.current_page)

    def collect_data(self):
        self.data["school"] = self.entry_school.get().strip()
        self.data["major"] = self.entry_major.get().strip()
        self.data["score"] = self.entry_score.get().strip()
        self.data["grade"] = self.entry_grade.get().strip()

        self.data["subjects"] = {}
        for sub, entry in self.subject_entries.items():
            val = entry.get().strip()
            if val:
                self.data["subjects"][sub] = val

        self.data["start"] = f"{self.start_year_var.get()}年{self.start_month_var.get()}"
        self.data["exam_year"] = int(self.start_year_var.get()) + (0 if self.start_month_var.get() in
                                     ["1月", "2月", "3月"] else 1)

    def generate(self):
        self.collect_data()
        school = self.data.get("school", "目标院校")
        major = self.data.get("major", "目标专业")
        score = self.data.get("score", "")
        start = self.data.get("start", "")

        # 构建五级目标
        goals = [
            # 长期目标
            {"id": self._gid(), "name": f"考研上岸：{school} {major}",
             "level": "长期", "parent": None, "children": []},
            # 年度目标
            {"id": self._gid(), "name": f"复试通过 & 收到录取通知",
             "level": "年度", "parent": None, "children": []},
            # 月度目标
            {"id": self._gid(), "name": f"考前冲刺：真题模拟 + 查漏补缺",
             "level": "月度", "parent": None, "children": []},
            # 周目标
            {"id": self._gid(), "name": "每周完成一套真题 + 薄弱点专项训练",
             "level": "每周", "parent": None, "children": []},
            # 日目标
            {"id": self._gid(), "name": "基础知识背诵（1小时）",
             "level": "每日", "parent": None, "children": []},
            {"id": self._gid(), "name": "专业课精读 + 笔记整理（1.5小时）",
             "level": "每日", "parent": None, "children": []},
            {"id": self._gid(), "name": "数学/英语练习（1小时）",
             "level": "每日", "parent": None, "children": []},
        ]

        # 添加各科具体目标
        subjects_data = self.data.get("subjects", {})
        for sub, target_score in subjects_data.items():
            goals.append({
                "id": self._gid(), "name": f"{sub}目标{target_score}分 | 基础→强化→冲刺",
                "level": "月度", "parent": None, "children": []
            })
            goals.append({
                "id": self._gid(), "name": f"{sub}：每日练习 + 错题整理",
                "level": "每周", "parent": None, "children": []
            })

        if score:
            goals[0]["name"] += f"（目标{score}分）"

        # 建立父子关系：长期 > 年度 > 月度 > 周 > 日
        # 按 level 分组
        levels = {"长期": [], "年度": [], "月度": [], "每周": [], "每日": []}
        for g in goals:
            if g["level"] in levels:
                levels[g["level"]].append(g)

        # 长期 → 年度
        for a in levels["年度"]:
            a["parent"] = levels["长期"][0]["id"]
            levels["长期"][0]["children"].append(a["id"])
        # 年度 → 月度
        for m in levels["月度"]:
            m["parent"] = levels["年度"][0]["id"]
            levels["年度"][0]["children"].append(m["id"])
        # 月度 → 周（第一个月度目标绑定第一组周目标）
        if levels["月度"] and levels["每周"]:
            mid = len(levels["月度"])
            for i, w in enumerate(levels["每周"]):
                w["parent"] = levels["月度"][i % mid]["id"]
                levels["月度"][i % mid]["children"].append(w["id"])
        # 周 → 日
        if levels["每周"] and levels["每日"]:
            for i, d in enumerate(levels["每日"]):
                d["parent"] = levels["每周"][i % len(levels["每周"])]["id"]
                levels["每周"][i % len(levels["每周"])]["children"].append(d["id"])

        self.on_generate(goals)
        messagebox.showinfo("完成", f"已生成 {len(goals)} 个目标！\n点击「目标拆解」页查看")
        self.destroy()

    _gid_counter = 0

    @classmethod
    def _gid(cls):
        cls._gid_counter += 1
        return f"g{cls._gid_counter:04d}"


# ============ 408 专属拆解向导 ============
class Wizard408(tk.Toplevel):
    """408 计算机考研目标拆解 — 按四科 + 三轮复习阶段生成目标"""

    SUBJECTS = [
        ("数据结构", 45),
        ("计算机组成原理", 45),
        ("操作系统", 35),
        ("计算机网络", 25),
    ]
    PHASES = ["基础阶段", "强化阶段", "冲刺阶段"]

    def __init__(self, parent, on_generate, preset_11408=False):
        super().__init__(parent)
        self.title("408 计算机考研拆解")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.preset_11408 = preset_11408
        # 居中
        w, h = 580, 480
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px = parent.winfo_rootx() + max(0, (pw - w) // 2)
        py = parent.winfo_rooty() + max(0, (ph - h) // 2)
        self.geometry(f"{w}x{h}+{px}+{py}")
        self.pages = []
        self.current_page = 0

        self.header = ttk.Label(self, text="第 1 步 / 3 步", font=("", 11, "bold"))
        self.header.pack(pady=(15, 5))

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True, padx=30, pady=10)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=30, pady=(0, 15))
        self.btn_prev = ttk.Button(btn_frame, text="上一步", command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left")
        self.btn_next = ttk.Button(btn_frame, text="下一步", command=self.next_page)
        self.btn_next.pack(side="right")

        self.create_page_1()
        self.show_page(0)

    # ── 第1步：基本信息 + 考试科目 ───────────────────────────
    def create_page_1(self):
        f = ttk.Frame(self.container)
        ttk.Label(f, text="基本信息", font=("", 12, "bold")).pack(anchor="w", pady=(0, 10))

        for label, key in [
            ("目标院校:", "school"),
            ("目标专业:", "major"),
            ("总分目标:", "total_score"),
        ]:
            row = ttk.Frame(f)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=10).pack(side="left")
            entry = ttk.Entry(row, width=30)
            entry.pack(side="left", fill="x", expand=True)
            setattr(self, f"entry_{key}", entry)

        if self.preset_11408:
            self.entry_total_score.insert(0, "350")

        ttk.Separator(f).pack(fill="x", pady=(12, 8))
        ttk.Label(f, text="公共课目标分数（选填）", font=("", 10, "bold")).pack(anchor="w")
        for label, key in [("数学一:", "math1"), ("英语一:", "english1"), ("政治:", "politics")]:
            row = ttk.Frame(f)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=10).pack(side="left")
            entry = ttk.Entry(row, width=8)
            entry.pack(side="left")
            ttk.Label(row, text="分", foreground="gray").pack(side="left", padx=(3, 0))
            if self.preset_11408:
                defaults = {"math1": "110", "english1": "65", "politics": "65"}
                entry.insert(0, defaults.get(key, ""))
            setattr(self, f"entry_{key}", entry)

        self.pages.append(f)

    # ── 第2步：各科当前水平评估 ─────────────────────────────
    def create_page_2(self):
        f = ttk.Frame(self.container)
        ttk.Label(f, text="各科当前水平评估（用于调整复习重点）", font=("", 12, "bold")).pack(anchor="w", pady=(0, 5))
        ttk.Label(f, text="请根据实际情况选择，系统会据此调整各科任务优先级", foreground="gray").pack(anchor="w", pady=(0, 8))

        self.level_vars = {}
        for sub, pts in self.SUBJECTS:
            row = ttk.Frame(f)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=f"{sub}（{pts}分）:", width=16, anchor="w").pack(side="left")
            var = tk.StringVar(value="一般")
            for level in ["薄弱", "一般", "良好"]:
                ttk.Radiobutton(row, text=level, variable=var, value=level).pack(side="left", padx=6)
            self.level_vars[sub] = var

        ttk.Separator(f).pack(fill="x", pady=(10, 8))
        ttk.Label(f, text="复习总轮次偏好", font=("", 10, "bold")).pack(anchor="w")
        self.rounds_var = tk.StringVar(value="3轮")
        round_row = ttk.Frame(f)
        round_row.pack(fill="x", pady=4)
        for r in ["2轮（时间短）", "3轮（标准）", "4轮（时间充裕）"]:
            ttk.Radiobutton(round_row, text=r, variable=self.rounds_var, value=r).pack(side="left", padx=8)

        self.pages.append(f)

    # ── 第3步：复习时间规划 ─────────────────────────────────
    def create_page_3(self):
        f = ttk.Frame(self.container)
        ttk.Label(f, text="复习时间规划", font=("", 12, "bold")).pack(anchor="w", pady=(0, 10))

        # 开始时间
        row1 = ttk.Frame(f)
        row1.pack(fill="x", pady=4)
        ttk.Label(row1, text="开始复习:", width=10).pack(side="left")
        self.start_month_var = tk.StringVar(value="3月")
        ttk.Combobox(row1, textvariable=self.start_month_var, width=8,
                      values=[f"{i}月" for i in range(1, 13)]).pack(side="left", padx=(0, 5))
        self.start_year_var = tk.StringVar(value=str(date.today().year))
        ttk.Combobox(row1, textvariable=self.start_year_var, width=8,
                      values=[str(date.today().year + i) for i in range(3)]).pack(side="left")
        ttk.Label(row1, text="年", foreground="gray").pack(side="left", padx=(3, 0))

        # 每日学习时长
        row2 = ttk.Frame(f)
        row2.pack(fill="x", pady=4)
        ttk.Label(row2, text="日均学习:", width=10).pack(side="left")
        self.daily_hours_var = tk.StringVar(value="8小时")
        ttk.Combobox(row2, textvariable=self.daily_hours_var, width=10,
                      values=["4小时", "6小时", "8小时", "10小时", "12小时"]).pack(side="left")

        ttk.Separator(f).pack(fill="x", pady=(15, 10))
        ttk.Label(f, text="生成内容预览：", font=("", 10, "bold")).pack(anchor="w")
        preview = (
            "• 长期目标：上岸目标院校\n"
            "• 年度目标：初试 + 复试\n"
            "• 三轮复习计划（基础/强化/冲刺），每轮含四科具体任务\n"
            "• 月度目标：按月份拆解三轮任务\n"
            "• 周目标：每周四科轮转 + 真题\n"
            "• 日目标：数据结构 / 计组 / 操作系统 / 计网 每日任务"
        )
        ttk.Label(f, text=preview, foreground="gray", justify="left").pack(anchor="w", pady=(5, 0))

        self.pages.append(f)

    # ── 页面切换 ─────────────────────────────────────────────
    def show_page(self, idx):
        for p in self.pages:
            p.pack_forget()
        self.pages[idx].pack(fill="both", expand=True)
        self.header.config(text=f"第 {idx + 1} 步 / 3 步")
        self.btn_prev.config(state="normal" if idx > 0 else "disabled")
        self.btn_next.config(text="生成目标" if idx == 2 else "下一步")

    def next_page(self):
        if self.current_page < 2:
            self.current_page += 1
            if self.current_page == 1 and len(self.pages) < 2:
                self.create_page_2()
            elif self.current_page == 2 and len(self.pages) < 3:
                self.create_page_3()
            self.show_page(self.current_page)
        else:
            self.generate()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_page(self.current_page)

    # ── 生成目标 ─────────────────────────────────────────────
    def generate(self):
        school = self.entry_school.get().strip() or "目标院校"
        major = self.entry_major.get().strip() or "计算机科学与技术"
        total_score = self.entry_total_score.get().strip()
        start = f"{self.start_year_var.get()}年{self.start_month_var.get()}"
        daily_h = int(self.daily_hours_var.get().replace("小时", "") or 8)
        rounds = self.rounds_var.get()

        # 按薄弱程度排序科目（薄弱的优先级高）
        level_order = {"薄弱": 0, "一般": 1, "良好": 2}
        subject_priority = sorted(
            [(sub, pts, self.level_vars[sub].get()) for sub, pts in self.SUBJECTS],
            key=lambda x: level_order.get(x[2], 1)
        )

        goals = []
        g = lambda name, level, parent=None, children=None: {
            "id": self._gid(), "name": name,
            "level": level, "parent": parent,
            "children": children or []
        }

        # ── 长期目标 ──────────────────────────────────────────
        long_term = g(f"考研上岸：{school} {major}（目标{total_score}分）" if total_score else f"考研上岸：{school} {major}", "长期")
        goals.append(long_term)

        # ── 年度目标 ──────────────────────────────────────────
        annual = g("年度目标：初试高分 + 复试通过", "年度")
        annual["parent"] = long_term["id"]
        long_term["children"].append(annual["id"])
        goals.append(annual)

        # 公共课也加入年度目标
        pub_tasks = []
        for label, key in [("数学一", "math1"), ("英语一", "english1"), ("政治", "politics")]:
            val = getattr(self, f"entry_{key}").get().strip()
            if val:
                pub_tasks.append(g(f"{label} 目标{val}分", "月度"))
                pub_tasks[-1]["parent"] = annual["id"]
                annual["children"].append(pub_tasks[-1]["id"])
                goals.append(pub_tasks[-1])

        # ── 三轮复习（挂在年度目标下）────────────────────────
        phase_map = {"基础阶段": ("第1轮"), "强化阶段": ("第2轮"), "冲刺阶段": ("第3轮")}
        phase_goals = {}
        for phase_name, _ in self.PHASES:
            ph = g(f"{phase_name}（{phase_map[phase_name]}）", "月度")
            ph["parent"] = annual["id"]
            annual["children"].append(ph["id"])
            goals.append(ph)
            phase_goals[phase_name] = ph

        # 每科在每阶段的任务
        phase_subject_tasks = {
            "基础阶段": {
                "数据结构":       ["通读教材（严蔚敏/王道），整理笔记", "完成课后习题 + 王道选择题", "重点：线性表、树、图、排序"],
                "计算机组成原理": ["通读教材（唐朔飞/王道），理解硬件结构", "完成王道选择题，理解指令执行过程", "重点：数据表示、CPU结构、指令流水线"],
                "操作系统":       ["通读教材（汤小丹/王道），建立整体概念", "完成王道选择题，理解进程调度", "重点：进程管理、内存管理、文件系统"],
                "计算机网络":     ["通读教材（谢希仁/王道），掌握分层模型", "完成王道选择题，熟记协议细节", "重点：TCP/IP、HTTP、路由算法"],
            },
            "强化阶段": {
                "数据结构":       ["王道/天勤大题专项训练", "代码实现经典算法（排序/查找/树）", "完成王道每章大题 + 错题整理"],
                "计算机组成原理": ["王道大题专项：Cache映射、流水线计算", "CPU设计题 + 数据通路分析", "完成王道每章大题 + 错题整理"],
                "操作系统":       ["王道大题专项：PV操作、内存分配算法", "高频考点刷题：死锁、虚拟内存", "完成王道每章大题 + 错题整理"],
                "计算机网络":     ["王道大题专项：子网划分、协议分析", "高频考点：TCP可靠传输、路由协议", "完成王道每章大题 + 错题整理"],
            },
            "冲刺阶段": {
                "数据结构":       ["408真题：数据结构大题专项（2010-2025）", "模拟卷限时训练，查漏补缺", "高频算法模板背诵（快排/堆排/DFS/BFS）"],
                "计算机组成原理": ["408真题：计组大题专项（2010-2025）", "模拟卷限时训练，Cache/流水线计算熟练", "易错点汇总：浮点运算、指令格式"],
                "操作系统":       ["408真题：OS大题专项（2010-2025）", "模拟卷限时训练，PV操作熟练", "易错点汇总：银行家算法、页面置换"],
                "计算机网络":     ["408真题：计网大题专项（2010-2025）", "模拟卷限时训练，协议分析熟练", "易错点汇总：拥塞控制、IP协议"],
            },
        }

        for phase_name, ph_goal in phase_goals.items():
            for sub, pts in subject_priority:
                sub_goal = g(f"{sub}（{pts}分）— {phase_name}", "每周")
                sub_goal["parent"] = ph_goal["id"]
                ph_goal["children"].append(sub_goal["id"])
                goals.append(sub_goal)

                # 每周任务：每科2-3个具体任务
                for task_desc in phase_subject_tasks[phase_name].get(sub, [])[:3]:
                    t = g(f"{sub}：{task_desc}", "每日")
                    t["parent"] = sub_goal["id"]
                    sub_goal["children"].append(t["id"])
                    goals.append(t)

        # ── 月度目标（按月份拆解）─────────────────────────────
        months = ["3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
        month_subjects = {
            "3月": ["数据结构"], "4月": ["数据结构","计算机组成原理"],
            "5月": ["计算机组成原理","操作系统"], "6月": ["操作系统","计算机网络"],
            "7月": ["数据结构","计算机组成原理"], "8月": ["操作系统","计算机网络"],
            "9月": ["四科综合复习"], "10月": ["真题训练"],
            "11月": ["模拟卷训练"], "12月": ["考前冲刺+查漏补缺"],
        }
        for m in months:
            subs = "/".join(month_subjects.get(m, ["四科"]))
            mg = g(f"{m} — {subs} 专项突破", "月度")
            mg["parent"] = annual["id"]
            annual["children"].append(mg["id"])
            goals.append(mg)

        # ── 周目标（通用模板）─────────────────────────────────
        week_template = [
            "周一：数据结构 算法题 + 笔记整理（2h）",
            "周二：计算机组成原理 大题专项（2h）",
            "周三：操作系统 PV操作 + 内存管理（2h）",
            "周四：计算机网络 协议分析（2h）",
            "周五：四科综合真题练习（3h）",
            "周六：错题整理 + 本周总结（2h）",
            "周日：休息 / 薄弱科目补强（自选）",
        ]
        for wt in week_template:
            wg = g(wt, "每周")
            wg["parent"] = annual["id"]
            annual["children"].append(wg["id"])
            goals.append(wg)

        # ── 日目标模板 ────────────────────────────────────────
        daily_template = [
            "数据结构：算法手写练习（30min）",
            "计算机组成原理：Cache/流水线计算题（30min）",
            "操作系统：PV操作大题（30min）",
            "计算机网络：协议细节背诵（20min）",
            "408真题：每日1道综合大题（40min）",
        ]
        for dt in daily_template:
            dg = g(dt, "每日")
            dg["parent"] = annual["id"]
            annual["children"].append(dg["id"])
            goals.append(dg)

        self.on_generate(goals)
        messagebox.showinfo("完成", f"已生成 {len(goals)} 个目标！\n点击「目标拆解」页查看")
        self.destroy()

    _gid_counter = 0

    @classmethod
    def _gid(cls):
        cls._gid_counter += 1
        return f"g{cls._gid_counter:04d}"


# ============ 目标管理页 ============