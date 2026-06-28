# 每日热点模块 — 实施计划

> **For Hermes:** 按此计划逐步实现，每步验证后再继续。

**Goal:** 为拾光添加「每日热点」Tab，展示微博/知乎/百度热搜，帮助考研同学快速了解当日热点。

**Architecture:** 新建 `ui/hot_tab.py`，通过 threading 异步请求各平台 API，统一数据格式后展示在 Tkinter Treeview 中；可选接入 DeepSeek 对热点做考研相关度总结。数据缓存到本地 JSON 避免重复请求。

**Tech Stack:** Python stdlib (threading, json, urllib), requests, BeautifulSoup (百度), Tkinter Treeview + ttk

---

## 数据源调研结论

| 平台 | API 方式 | 需要认证 | 稳定性 | 推荐 |
|------|---------|---------|--------|------|
| 知乎 | REST API (JSON) | 无需 Cookie | ⭐⭐⭐ 高 | ✅ 首选 |
| 百度 | HTML 解析 | 无需 Cookie | ⭐⭐ 中 | ✅ 可用 |
| 微博 | AJAX API | **必须 Cookie+XSRF** | ⭐ 低(过期频繁) | ❌ 不适合桌面应用 |
| 抖音 | 逆向 | 困难 | ⭐ 低 | ❌ 跳过 |

**决定：只用知乎 + 百度。** 微博需要浏览器 Cookie 注入，桌面应用无法稳定维护。

## 知乎 API 端点

```
GET https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=30
Headers: User-Agent=Mozilla/5.0 (iPhone...)
返回: { data: [{ target: { title, url, excerpt, answer_count, follower_count }, detail_text: "热度 xxx 万" }] }
```

## 百度 API 端点

```
GET https://top.baidu.com/board?tab=realtime
Headers: User-Agent=Chrome UA
解析: BeautifulSoup → div.category-wrap_iQLoo → 提取 rank, title, desc, heat
```

---

## 任务列表

### Task 1: 创建数据源模块 `hot_sources.py`

**Objective:** 封装知乎和百度的数据获取逻辑

**Files:**
- Create: `D:\QClawWorkspace\all_in_one\hot_sources.py`

**代码:**

```python
"""每日热点数据源 — 知乎热榜 + 百度热搜"""
import json
import urllib.request
import urllib.error
import time
from typing import List, Dict, Optional

# ── 知乎 ──
ZHIHU_URL = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
ZHIHU_HEADERS = {
    "User-Agent": (
        "osee2unifiedRelease/4318 osee2unifiedReleaseVersion/7.7.0 "
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    )
}

def fetch_zhihu_hot(limit: int = 20) -> List[Dict]:
    """获取知乎热榜，返回统一格式"""
    url = f"{ZHIHU_URL}?limit={limit}"
    req = urllib.request.Request(url, headers=ZHIHU_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[知乎] 请求失败: {e}")
        return []

    items = []
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for rank, item in enumerate(data.get("data", [])[:limit], 1):
        target = item.get("target", {}) if isinstance(item.get("target"), dict) else item
        title = target.get("title", "")
        if not title:
            continue

        raw_url = target.get("url", "")
        question_url = raw_url.replace("api", "www").replace("questions", "question") if raw_url else ""

        # 热度解析
        detail = item.get("detail_text", "")
        heat = _parse_zhihu_heat(detail)

        items.append({
            "rank": rank,
            "title": title,
            "url": question_url,
            "heat": heat,
            "source": "知乎",
            "extra": f"{target.get('answer_count', 0) or 0} 回答",
            "scraped_at": now,
        })
    return items

def _parse_zhihu_heat(detail_text: str) -> str:
    """将 '123 万热度' → '123 万'"""
    if not detail_text:
        return ""
    import re
    m = re.search(r'([\d.]+)\s*万', str(detail_text))
    return f"{m.group(1)} 万" if m else str(detail_text).strip()

# ── 百度 ──
BAIDU_URL = "https://top.baidu.com/board?tab=realtime"
BAIDU_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
}

def fetch_baidu_hot(limit: int = 20) -> List[Dict]:
    """获取百度热搜，使用 BeautifulSoup 解析"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[百度] BeautifulSoup 未安装")
        return []

    req = urllib.request.Request(BAIDU_URL, headers=BAIDU_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[百度] 请求失败: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = []
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    cards = soup.find_all("div", class_="category-wrap_iQLoo")
    for i, card in enumerate(cards[:limit], 1):
        # 标题
        title_div = card.find("div", class_="c-single-text-ellipsis")
        title = title_div.get_text(strip=True) if title_div else ""
        if not title:
            continue

        # 热度
        hot_div = card.find("div", class_="hot-index_1Bl1a")
        heat = hot_div.get_text(strip=True) if hot_div else ""

        # 描述
        desc_div = card.find("div", class_="hot-desc_1m_jR")
        desc = desc_div.get_text(strip=True).replace("查看更多>", "").strip() if desc_div else ""

        # 链接
        link_tag = card.find("a", href=True)
        url = link_tag["href"] if link_tag else ""
        if url and not url.startswith("http"):
            url = "https://www.baidu.com" + url

        items.append({
            "rank": i,
            "title": title,
            "url": url,
            "heat": heat,
            "source": "百度",
            "extra": desc,
            "scraped_at": now,
        })
    return items

# ── 统一入口 ──
def fetch_all_hot(limit: int = 20) -> List[Dict]:
    """获取所有平台热点，合并后按来源分组返回"""
    all_items = []
    all_items.extend(fetch_zhihu_hot(limit))
    all_items.extend(fetch_baidu_hot(limit))
    return all_items
```

**验证:**
```bash
cd D:\QClawWorkspace\all_in_one
PYTHONHOME= python -c "from hot_sources import fetch_all_hot; items = fetch_all_hot(5); print(f'获取 {len(items)} 条'); [print(f'{i[\"source\"]}|{i[\"rank\"]}. {i[\"title\"]}') for i in items[:10]]"
```

---

### Task 2: 创建热点 Tab `ui/hot_tab.py`

**Objective:** 实现每日热点 UI 页面

**Files:**
- Create: `D:\QClawWorkspace\all_in_one\ui\hot_tab.py`

**设计:**
- 上区: 来源切换按钮(知乎/百度/全部) + 刷新按钮 + 更新时间
- 中区: Treeview 表格 (排名 | 标题 | 热度 | 来源)
- 下区: 点击行显示详情 (摘要 + 链接)
- 异步加载: threading 请求 + `root.after()` 回主线程更新 UI
- 缓存: JSON 文件缓存当天热点，打开 tab 先显示缓存再异步刷新

**代码:**
```python
"""每日热点 Tab — 知乎热榜 + 百度热搜"""
import tkinter as tk
from tkinter import ttk
import threading
import json
import os
from datetime import date

from hot_sources import fetch_all_hot, fetch_zhihu_hot, fetch_baidu_hot

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "hot_cache.json")

class HotTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._items = []  # 全部数据
        self._filtered = []  # 过滤后的数据
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
        source_frame.pack(side="right", padx=(0, 10))
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
                                  selectmode="browse", height=15)
        self.tree.heading("rank", text="#", anchor="center")
        self.tree.heading("title", text="标题", anchor="w")
        self.tree.heading("heat", text="热度", anchor="center")
        self.tree.heading("source", text="来源", anchor="center")

        self.tree.column("rank", width=40, anchor="center")
        self.tree.column("title", width=400, anchor="w")
        self.tree.column("heat", width=80, anchor="center")
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

    # ── 数据加载 ──
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
        # 无缓存，异步加载
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
            # 回主线程更新 UI
            self.after(0, lambda: self._on_data_loaded(items))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_data_loaded(self, items):
        """数据加载完成回调（主线程）"""
        self._loading = False
        self.progress.stop()
        self.progress.pack_forget()
        self.refresh_btn.config(state="normal", text="🔄 刷新")

        import time
        now = time.strftime("%H:%M:%S")
        self.time_label.config(text=f"更新于 {now}")

        if items:
            self._items = items
            self._apply_filter()
            self._save_cache()
        else:
            # 保留缓存数据
            pass

    # ── 过滤与展示 ──
    def _apply_filter(self):
        """根据 source_var 过滤并更新 Treeview"""
        source = self.source_var.get()
        if source == "全部":
            self._filtered = self._items
        else:
            self._filtered = [i for i in self._items if i.get("source") == source]

        # 清空 tree
        for row in self.tree.get_children():
            self.tree.delete(row)

        # 填充
        for item in self._filtered:
            self.tree.insert("", "end", values=(
                item.get("rank", ""),
                item.get("title", ""),
                item.get("heat", ""),
                item.get("source", ""),
            ), tags=(str(item.get("rank", 0)),))

        # 前三条高亮
        self.tree.tag_configure("1", foreground="#F44336")
        self.tree.tag_configure("2", foreground="#FF9800")
        self.tree.tag_configure("3", foreground="#FF9800")

    def _on_select(self, event):
        """点击条目显示详情"""
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values:
            return
        title = values[1]
        source = values[3]

        # 查找完整数据
        detail = ""
        for item in self._filtered:
            if item.get("title") == title and item.get("source") == source:
                url = item.get("url", "")
                extra = item.get("extra", "")
                parts = [f"📌 {title}"]
                if extra:
                    parts.append(f"📝 {extra}")
                if url:
                    parts.append(f"🔗 {url}")
                detail = "\n".join(parts)
                break

        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", detail or title)
```

**验证:**
```bash
cd D:\QClawWorkspace\all_in_one
PYTHONHOME= python -m py_compile ui/hot_tab.py
```

---

### Task 3: 注册 Tab 到 main.py

**Objective:** 将 HotTab 接入侧边栏导航

**Files:**
- Modify: `D:\QClawWorkspace\all_in_one\main.py`

**修改步骤:**

1. **Import 添加** (在顶部 import 区域):
```python
from ui.hot_tab import HotTab
```

2. **创建实例** (在 `__init__` 中，其他 tab 创建之后):
```python
self.hot_tab = HotTab(self.content, self)
```

3. **添加到 nav_items** (在 `nav_items` 列表末尾):
```python
("📰  每日热点", self.hot_tab, "hot"),
```

4. **添加到 tab_map** (在 `_switch_tab` 的 `tab_map` dict):
```python
"hot": self.hot_tab,
```

5. **添加到隐藏循环** (在 `_switch_tab` 的 `for tab in (...)` 元组):
```python
for tab in (self.goal_tab, self.task_tab, self.week_tab,
             self.timer_stats_tab, self.progress_tab,
             self.timetrack_tab, self.ocr_tab, self.hot_tab):
```

**完整修改位置参考:**

main.py 的 import 区域 (第 8-24 行):
```python
from ui.hot_tab import HotTab  # ← 新增，放在 ocr_tab import 之后
```

main.py 的实例创建区域 (约第 90 行):
```python
self.ocr_tab = OcrTab(self.content, self)
self.hot_tab = HotTab(self.content, self)  # ← 新增
```

main.py 的 nav_items (约第 100-115 行):
```python
nav_items = [
    ("🎯  目标拆解", self.goal_tab, "goal"),
    ("📝  今日任务", self.task_tab, "task"),
    ("📅  周计划表", self.week_tab, "week"),
    ("⏱📊 专注·统计", self.timer_stats_tab, "timer"),
    ("📈  训练进度", self.progress_tab, "progress"),
    ("📊  时间追踪", self.timetrack_tab, "timetrack"),
    ("🔍  文字识别", self.ocr_tab, "ocr"),
    ("📰  每日热点", self.hot_tab, "hot"),  # ← 新增
]
```

main.py 的 _switch_tab (约第 125-150 行):
```python
def _switch_tab(self, key):
    for tab in (self.goal_tab, self.task_tab, self.week_tab,
                 self.timer_stats_tab, self.progress_tab,
                 self.timetrack_tab, self.ocr_tab, self.hot_tab):  # ← 加入 hot_tab
        tab.pack_forget()
    # ...
    tab_map = {
        # ... existing entries ...
        "hot": self.hot_tab,  # ← 新增
    }
```

**验证:**
```bash
cd D:\QClawWorkspace\all_in_one
PYTHONHOME= python -m py_compile main.py
```

---

### Task 4: 安装依赖 & 完整测试

**Objective:** 安装 BeautifulSoup 并验证全流程

**Steps:**

```bash
# 安装依赖
pip install beautifulsoup4

# 语法检查所有修改的文件
cd D:\QClawWorkspace\all_in_one
PYTHONHOME= python -m py_compile hot_sources.py
PYTHONHOME= python -m py_compile ui/hot_tab.py
PYTHONHOME= python -m py_compile main.py

# 测试数据源
PYTHONHOME= python -c "
from hot_sources import fetch_zhihu_hot, fetch_baidu_hot
zh = fetch_zhihu_hot(5)
print(f'知乎: {len(zh)} 条')
for i in zh[:3]: print(f'  {i[\"rank\"]}. {i[\"title\"]} | {i[\"heat\"]}')
bd = fetch_baidu_hot(5)
print(f'百度: {len(bd)} 条')
for i in bd[:3]: print(f'  {i[\"rank\"]}. {i[\"title\"]} | {i[\"heat\"]}')
"

# 杀掉旧实例，启动验证
cmd //c 'taskkill /f /im pythonw.exe 2>nul'
PYTHONHOME= UV_INTERNAL__PYTHONHOME= pythonw main.py
```

**UI 验证清单:**
- [ ] 侧边栏出现「📰 每日热点」按钮
- [ ] 点击后显示热点列表（首次自动刷新，后续显示缓存）
- [ ] 来源筛选按钮 (全部/知乎/百度) 正常工作
- [ ] 点击条目显示详情（摘要+链接）
- [ ] 🔄 刷新按钮异步加载，不阻塞 UI
- [ ] 关闭重开后显示当天缓存，不重复请求

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `hot_sources.py` | 数据源模块（知乎API + 百度HTML解析） |
| 新建 | `ui/hot_tab.py` | 热点 Tab UI（Treeview + 筛选 + 缓存） |
| 修改 | `main.py` | 注册 HotTab（import + 实例 + nav_items + tab_map + 隐藏循环） |
| 新建 | `data/hot_cache.json` | 运行时自动创建 |

---

## 已知风险

1. **百度 HTML class 名变化** — `category-wrap_iQLoo` 等是百度前端的 hash class，可能随版本变动。备选: 改用正则从 HTML 提取。
2. **知乎 API 限流** — 短期频繁请求可能被限。缓存机制已做日级去重，每次打开 tab 最多请求一次。
3. **网络不可用** — 显示缓存数据 + 底部提示"离线模式"。
4. **beautifulsoup4 依赖** — 百度源需要 `pip install beautifulsoup4`。如果未安装，百度源静默返回空列表。

---

## 后续可扩展 (不在本次范围)

- AI 总结: 调用 DeepSeek 对热点做考研相关度评估
- 关键词过滤: 自定义关注词（如"考研""英语""政治"等）
- 历史回看: 按日期查看历史热点
- 更多平台: B站热榜、财联社等
