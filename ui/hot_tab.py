"""每日热点 Tab — 知乎热榜 + 百度热搜"""
import tkinter as tk
from tkinter import ttk
import threading
import json
import os
import time
from datetime import date

from hot_sources import fetch_all_hot

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CACHE_FILE = os.path.join(DATA_DIR, "hot_cache.json")


class HotTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._items = []
        self._filtered = []
        self._loading = False

        self._build_ui()
        self._load_cache()

    # ── UI 构建 ──
    def _build_ui(self):
        # 顶部工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(toolbar, text="📰 每日热点",
                  font=("Microsoft YaHei", 13, "bold")).pack(side="left")

        # 来源筛选
        self.source_var = tk.StringVar(value="全部")
        source_frame = ttk.Frame(toolbar)
        source_frame.pack(side="right", padx=(0, 8))
        for s in ["全部", "知乎", "百度"]:
            rb = ttk.Radiobutton(source_frame, text=s, variable=self.source_var,
                                 value=s, command=self._apply_filter)
            rb.pack(side="left", padx=2)

        # 刷新按钮
        self.refresh_btn = ttk.Button(toolbar, text="🔄 刷新",
                                       command=self._async_refresh)
        self.refresh_btn.pack(side="right")

        # 更新时间
        self.time_label = ttk.Label(toolbar, text="", foreground="#909090")
        self.time_label.pack(side="right", padx=10)

        # 中间: Treeview 表格
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("rank", "title", "heat", "source")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  selectmode="browse")
        self.tree.heading("rank", text="#", anchor="center")
        self.tree.heading("title", text="标题", anchor="w")
        self.tree.heading("heat", text="热度", anchor="center")
        self.tree.heading("source", text="来源", anchor="center")

        self.tree.column("rank", width=40, anchor="center")
        self.tree.column("title", width=400, anchor="w")
        self.tree.column("heat", width=90, anchor="center")
        self.tree.column("source", width=60, anchor="center")

        # 滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                   command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 点击行 → 显示详情
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # 底部详情区
        detail_frame = ttk.LabelFrame(self, text="详情", padding=5)
        detail_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.detail_text = tk.Text(detail_frame, wrap="word", height=4,
                                    font=("Microsoft YaHei", 10),
                                    bg="#FAFAFA", relief="flat", padx=8, pady=6)
        self.detail_text.pack(fill="x")
        self.detail_text.insert("1.0", "点击上方条目查看详情")

        # 进度条 (刷新时显示)
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=100)

        # 前三条高亮色
        self.tree.tag_configure("r1", foreground="#F44336")
        self.tree.tag_configure("r2", foreground="#FF9800")
        self.tree.tag_configure("r3", foreground="#FF9800")

    # ── 缓存 ──
    def _load_cache(self):
        """加载缓存数据（如果存在）"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                cache_date = cache.get("date", "")
                if cache_date == str(date.today()):
                    self._items = cache.get("items", [])
                    self._apply_filter()
                    self.time_label.config(text=cache.get("time", ""))
                    return
            except Exception:
                pass
        # 无缓存或过期，异步加载
        self._async_refresh()

    def _save_cache(self):
        """保存到缓存"""
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        cache = {
            "date": str(date.today()),
            "time": self.time_label.cget("text"),
            "items": self._items,
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    # ── 数据加载 ──
    def _async_refresh(self):
        """异步刷新数据"""
        if self._loading:
            return
        self._loading = True
        self.refresh_btn.config(state="disabled", text="⏳ 加载中...")
        self.progress.pack(fill="x", padx=10, pady=(0, 3))
        self.progress.start()

        def fetch():
            try:
                items = fetch_all_hot(30)
            except Exception as e:
                items = []
                print(f"[热点] 获取失败: {e}")
            self.after(0, lambda: self._on_data_loaded(items))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_data_loaded(self, items):
        """数据加载完成回调（主线程）"""
        self._loading = False
        self.progress.stop()
        self.progress.pack_forget()
        self.refresh_btn.config(state="normal", text="🔄 刷新")

        now = time.strftime("%H:%M:%S")
        self.time_label.config(text=f"更新于 {now}")

        if items:
            self._items = items
            self._apply_filter()
            self._save_cache()

    # ── 过滤与展示 ──
    def _apply_filter(self):
        """根据 source_var 过滤并更新 Treeview"""
        source = self.source_var.get()
        if source == "全部":
            self._filtered = self._items
            # 全部时: 知乎在前，百度在后
            self._filtered = sorted(self._filtered, key=lambda x: (0 if x.get("source") == "知乎" else 1, x.get("rank", 0)))
        else:
            self._filtered = [i for i in self._items if i.get("source") == source]

        # 清空 tree
        for row in self.tree.get_children():
            self.tree.delete(row)

        # 填充
        for idx, item in enumerate(self._filtered, 1):
            tag = ""
            if idx <= 3 and source == "全部":
                tag = f"r{idx}"
            elif idx <= 3:
                tag = f"r{idx}"

            self.tree.insert("", "end", values=(
                idx,
                item.get("title", ""),
                item.get("heat", ""),
                item.get("source", ""),
            ), tags=(tag,) if tag else ())

    def _on_select(self, event):
        """点击条目显示详情"""
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        idx_str, title, heat, source = values[0], values[1], values[2], values[3]

        # 查找完整数据
        detail = ""
        for item in self._filtered:
            if item.get("title") == title and item.get("source") == source:
                url = item.get("url", "")
                extra = item.get("extra", "")
                parts = [f"📌 {title}"]
                parts.append(f"🔥 热度: {heat}" if heat else "🔥 热度: —")
                if extra:
                    parts.append(f"📝 {extra}")
                if url:
                    parts.append(f"🔗 {url}")
                detail = "\n\n".join(parts)
                break

        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", detail or title)
