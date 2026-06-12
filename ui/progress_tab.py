"""Auto-extracted module."""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, date, timedelta
from config import DATA_DIR, TASKS_FILE, TRAINING_LOG_FILE
from data_manager import DataManager

class ProgressTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # 上部：记录录入
        top = ttk.LabelFrame(self, text="📝 记录身体数据", padding=10)
        top.pack(fill="x", padx=10, pady=(5, 0))

        row1 = ttk.Frame(top)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="日期:", width=6).pack(side="left")
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(row1, textvariable=self.date_var, width=12).pack(side="left", padx=(0,15))
        ttk.Label(row1, text="体重(kg):", width=9).pack(side="left")
        self.weight_var = tk.StringVar()
        self.weight_entry = ttk.Entry(row1, textvariable=self.weight_var, width=7)
        self.weight_entry.pack(side="left", padx=(0,5))
        self.weight_var.trace_add("write", self._update_bmi_preview)

        # 身高（可点击修改）
        self.height_inline_btn = ttk.Label(row1, text="", font=("", 9), foreground="#555",
            cursor="hand2")
        self.height_inline_btn.pack(side="left", padx=(0, 5))
        self.height_inline_btn.bind("<Button-1>", lambda e: self._set_height_inline())

        # 实时BMI预览
        self.bmi_label = ttk.Label(row1, text="BMI: —", foreground="#666", font=("", 9))
        self.bmi_label.pack(side="left", padx=(0, 15))
        ttk.Button(row1, text="💾 保存记录", command=self.save_record).pack(side="left")

        # 中部：体重曲线 + 完成率（无框，用标题+色块区分）
        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, padx=10, pady=5)

        # 体重趋势
        left = tk.Frame(mid, bg="#FFFFFF", highlightthickness=0)
        left.pack(side="left", fill="both", expand=True, padx=(0,5))
        tk.Frame(left, bg="#2196F3", height=3).pack(fill="x")
        ttk.Label(left, text="⚖ 体重趋势", font=("Microsoft YaHei", 9, "bold"),
                  foreground="#666").pack(anchor="w", padx=5, pady=(5, 2))
        self.weight_canvas = tk.Canvas(left, bg="white", height=215, highlightthickness=0)
        self.weight_canvas.pack(fill="both", expand=True)
        self.weight_canvas.bind("<Configure>", lambda e: self.draw_weight_chart())

        # 完成率
        right = tk.Frame(mid, bg="#FFFFFF", highlightthickness=0)
        right.pack(side="left", fill="both", expand=True, padx=(5,0))
        tk.Frame(right, bg="#4CAF50", height=3).pack(fill="x")
        ttk.Label(right, text="✅ 每周完成率", font=("Microsoft YaHei", 9, "bold"),
                  foreground="#666").pack(anchor="w", padx=5, pady=(5, 2))
        self.rate_canvas = tk.Canvas(right, bg="white", height=215, highlightthickness=0)
        self.rate_canvas.pack(fill="both", expand=True)
        self.rate_canvas.bind("<Configure>", lambda e: self.draw_rate_chart())

        # 下部：记录表
        bot = ttk.LabelFrame(self, text="📋 历史记录", padding=5)
        bot.pack(fill="both", expand=True, padx=10, pady=(0,5))
        cols = ("date", "weight", "bmi", "training_done", "training_total")
        self.rec_tree = ttk.Treeview(bot, columns=cols, show="headings", height=6)
        self.rec_tree.heading("date", text="日期")
        self.rec_tree.heading("weight", text="体重(kg)")
        self.rec_tree.heading("bmi", text="BMI")
        self.rec_tree.heading("training_done", text="完成训练")
        self.rec_tree.heading("training_total", text="总训练")
        self.rec_tree.column("date", width=100)
        self.rec_tree.column("weight", width=80)
        self.rec_tree.column("bmi", width=65)
        self.rec_tree.column("training_done", width=80)
        self.rec_tree.column("training_total", width=80)
        rec_sb = ttk.Scrollbar(bot, orient="vertical", command=self.rec_tree.yview)
        self.rec_tree.configure(yscrollcommand=rec_sb.set)
        self.rec_tree.pack(side="left", fill="both", expand=True)
        rec_sb.pack(side="right", fill="y")
        self.rec_tree.bind("<MouseWheel>", lambda e: self.rec_tree.yview_scroll(int(-1 * e.delta / 120), "units"))

        # 初始化时刷新身高/BMI显示
        self.after(200, self._update_bmi_preview)
        self.after(300, self.refresh_progress)

    def _load_log(self):
        d = DataManager.load(TRAINING_LOG_FILE, default={})
        if not isinstance(d, dict):
            d = {}
        return d

    def _save_log(self, data):
        DataManager.save(TRAINING_LOG_FILE, data)

    def save_record(self):
        ds = self.date_var.get().strip()
        w = self.weight_var.get().strip()
        if not ds:
            messagebox.showwarning("提示", "请输入日期")
            return
        log = self._load_log()
        entry = log.get(ds, {})
        if w:
            try:
                entry["weight"] = float(w)
            except ValueError:
                messagebox.showerror("错误", "体重必须是数字")
                return
        log[ds] = entry
        self._save_log(log)
        self.refresh_progress()
        self.weight_var.set("")
        messagebox.showinfo("成功", f"{ds} 数据已保存")

    def refresh_progress(self):
        log = self._load_log()
        tasks = DataManager.load(TASKS_FILE)

        # 统计每天的完成率
        dates = sorted(log.keys(), reverse=True)
        for ds in dates:
            entry = log[ds]
            day_tasks = [t for t in tasks if t.get("date") == ds and any(
                kw in t.get("name", "") for kw in ("训练", "有氧", "拉伸", "散步", "核心", "力量"))]
            entry["training_done"] = sum(1 for t in day_tasks if t["done"])
            entry["training_total"] = len(day_tasks)

        # 刷新表格
        self.rec_tree.delete(*self.rec_tree.get_children())
        height_cm = self._load_settings().get("height_cm")
        for ds in dates:
            entry = log.get(ds, {})
            w = entry.get("weight")
            bmi_str = self._calc_bmi_str(w, height_cm) if w else "—"
            self.rec_tree.insert("", "end", values=(
                ds,
                f"{w}" if w else "—",
                bmi_str,
                entry.get("training_done", 0),
                entry.get("training_total", 0)
            ))

        self.draw_weight_chart()
        self.draw_rate_chart()
        # 刷新完成后更新BMI预览
        self._update_bmi_preview()

    def draw_weight_chart(self):
        c = self.weight_canvas
        c.delete("all")
        log = self._load_log()
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 100 or H < 80:
            return

        # 收集体重数据点
        points = []
        for ds in sorted(log.keys()):
            w = log[ds].get("weight")
            if w:
                points.append((ds, w))

        if not points:
            c.create_text(W//2, H//2, text="暂无体重数据\n请在上方录入", fill="#999", font=("", 11))
            return

        PAD_L, PAD_R, PAD_T, PAD_B = 50, 15, 25, 30
        cw = W - PAD_L - PAD_R
        ch = H - PAD_T - PAD_B

        weights = [p[1] for p in points]
        w_min = min(weights) - 1
        w_max = max(weights) + 1
        if w_max - w_min < 2:
            w_max = w_min + 2

        # Y轴
        for i in range(5):
            val = w_min + (w_max - w_min) * i / 4
            y = PAD_T + ch - ch * i / 4
            c.create_text(PAD_L - 5, y, text=f"{val:.1f}", anchor="e", fill="#888", font=("", 8))
            c.create_line(PAD_L, y, W - PAD_R, y, fill="#EEEEEE")

        # 数据线和点
        n = len(points)
        coords = []
        for i, (ds, w) in enumerate(points):
            x = PAD_L + cw * i / max(n - 1, 1)
            y = PAD_T + ch * (1 - (w - w_min) / (w_max - w_min))
            coords.extend([x, y])

        if len(coords) >= 4:
            c.create_line(*coords, fill="#1976D2", width=2, smooth=True)

        for i, (ds, w) in enumerate(points):
            x = PAD_L + cw * i / max(n - 1, 1)
            y = PAD_T + ch * (1 - (w - w_min) / (w_max - w_min))
            c.create_oval(x-4, y-4, x+4, y+4, fill="#1976D2", outline="white", width=2)
            # 数据点上方显示具体体重
            c.create_text(x, y - 12, text=f"{w:.1f}", fill="#1976D2", font=("", 8, "bold"))
            # X标签（间隔显示）
            if n <= 10 or i % max(1, n // 7) == 0:
                label = ds[5:]  # MM-DD
                c.create_text(x, H - PAD_B + 12, text=label, fill="#888", font=("", 7))

    def draw_rate_chart(self):
        c = self.rate_canvas
        c.delete("all")
        log = self._load_log()
        tasks = DataManager.load(TASKS_FILE)
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 100 or H < 80:
            return

        # 收集每周完成率
        week_data = {}  # monday_str -> (done, total)
        for t in tasks:
            if not any(kw in t.get("name", "") for kw in ("训练", "有氧", "拉伸", "散步", "核心", "力量")):
                continue
            ds = t.get("date", "")
            if not ds:
                continue
            try:
                d = date.fromisoformat(ds)
            except ValueError:
                continue
            mon = d - timedelta(days=d.weekday())
            mon_s = mon.isoformat()
            if mon_s not in week_data:
                week_data[mon_s] = [0, 0]
            week_data[mon_s][1] += 1
            if t["done"]:
                week_data[mon_s][0] += 1

        if not week_data:
            c.create_text(W//2, H//2, text="暂无训练数据", fill="#999", font=("", 11))
            return

        PAD_L, PAD_R, PAD_T, PAD_B = 45, 15, 25, 35
        cw = W - PAD_L - PAD_R
        ch = H - PAD_T - PAD_B

        weeks = sorted(week_data.keys())
        n = len(weeks)
        bar_w = min(40, cw // max(n, 1) - 5)

        # Y轴 (0% ~ 100%)
        for pct in [0, 25, 50, 75, 100]:
            y = PAD_T + ch * (1 - pct / 100)
            c.create_text(PAD_L - 5, y, text=f"{pct}%", anchor="e", fill="#888", font=("", 8))
            c.create_line(PAD_L, y, W - PAD_R, y, fill="#EEEEEE")

        # 柱状图
        COLORS = ["#42A5F5", "#66BB6A", "#FFA726", "#AB47BC", "#EF5350", "#26C6DA"]
        for i, mon_s in enumerate(weeks):
            done, total = week_data[mon_s]
            rate = done / total if total > 0 else 0
            x = PAD_L + cw * (i + 0.5) / n
            y_top = PAD_T + ch * (1 - rate)
            y_bot = PAD_T + ch
            color = COLORS[i % len(COLORS)]
            c.create_rectangle(x - bar_w//2, y_top, x + bar_w//2, y_bot, fill=color, outline="white", width=1)
            # 百分比标签
            c.create_text(x, y_top - 8, text=f"{rate*100:.0f}%", fill="#555", font=("", 8, "bold"))
            # X标签
            label = mon_s[5:]  # MM-DD
            c.create_text(x, H - PAD_B + 12, text=label, fill="#888", font=("", 7))

    # ── BMI 辅助方法 ──
    def _calc_bmi_str(self, weight_kg, height_cm):
        if not weight_kg or not height_cm:
            return "—"
        h_m = height_cm / 100.0
        bmi = weight_kg / (h_m * h_m)
        return f"{bmi:.1f}"

    def _update_bmi_preview(self, *_):
        """刷新身高内联显示和BMI预览"""
        # 刷新身高显示
        settings = self.app._load_settings()
        height_cm = settings.get("height_cm")
        if height_cm:
            self.height_inline_btn.config(text=f"📏{int(height_cm)}cm")
        else:
            self.height_inline_btn.config(text="📏未设", foreground="#999")

        # 刷新BMI预览
        w_str = self.weight_var.get().strip()
        if w_str and height_cm:
            try:
                w = float(w_str)
                bmi_str = self._calc_bmi_str(w, height_cm)
                bmi_val = float(bmi_str)
                if bmi_val < 18.5:
                    color = "#FF9800"
                elif bmi_val < 24:
                    color = "#4CAF50"
                elif bmi_val < 28:
                    color = "#FF9800"
                else:
                    color = "#F44336"
                self.bmi_label.config(text=f"BMI: {bmi_str}", foreground=color)
            except ValueError:
                self.bmi_label.config(text="BMI: —", foreground="#666")
        else:
            self.bmi_label.config(text="BMI: —", foreground="#666")

    def _set_height_inline(self):
        """在ProgressTab内弹出身高设置（复用app的对话框但刷新本tab）"""
        dlg = tk.Toplevel(self)
        dlg.title("设置身高")
        dlg.geometry("300x150")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text="请输入身高（厘米）：",
                  font=("Microsoft YaHei", 11, "bold")).pack(pady=(20, 10))

        current = self.app._load_settings().get("height_cm", "")
        var = tk.StringVar(value=str(int(current)) if current else "")

        f = ttk.Frame(dlg)
        f.pack()
        entry = ttk.Entry(f, textvariable=var, width=8,
                          font=("Microsoft YaHei", 12), justify="center")
        entry.pack(side="left")
        ttk.Label(f, text="cm", font=("Microsoft YaHei", 10)).pack(side="left", padx=(5, 0))

        def save():
            v = var.get().strip()
            if v:
                try:
                    val = float(v)
                    if val < 50 or val > 250:
                        messagebox.showerror("错误", "身高应在 50~250cm 之间", parent=dlg)
                        return
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的数字", parent=dlg)
                    return
            data = self.app._load_settings()
            data["height_cm"] = float(v) if v else None
            self.app._save_settings(data)
            dlg.destroy()
            self._update_bmi_preview()
            self.app._update_height_display()
            self.refresh_progress()

        def clear():
            data = self.app._load_settings()
            data["height_cm"] = None
            self.app._save_settings(data)
            dlg.destroy()
            self._update_bmi_preview()
            self.app._update_height_display()
            self.refresh_progress()

        btn_f = ttk.Frame(dlg)
        btn_f.pack(pady=(12, 0))
        ttk.Button(btn_f, text="✓ 确定", command=save, width=10).pack(side="left", padx=5)
        ttk.Button(btn_f, text="✗ 取消", command=dlg.destroy, width=10).pack(side="left", padx=5)
        ttk.Button(btn_f, text="清除", command=clear, width=10).pack(side="left", padx=5)

