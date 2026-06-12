"""Auto-extracted module."""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, date
from config import GOALS_FILE, TASKS_FILE, SETTINGS_FILE
from data_manager import DataManager

class GoalTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.goals = DataManager.load(GOALS_FILE)

        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 5))

        ttk.Button(toolbar, text="🧠 智能拆解 ▼", command=self.choose_wizard).pack(side="left", padx=(0, 5))
        ttk.Button(toolbar, text="➕ 手动添加", command=self.manual_add).pack(side="left", padx=(0, 5))
        ttk.Button(toolbar, text="🗑 删除选中", command=self.delete_goal).pack(side="left")
        ttk.Button(toolbar, text="📋 添加为今日任务", command=self.add_to_tasks).pack(side="right")

        # 搜索框
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side="right", padx=(0, 10))
        ttk.Label(search_frame, text="🔍").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh_goal_tree())
        ttk.Entry(search_frame, textvariable=self.search_var, width=15).pack(side="left")

        # 树形列表
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True)

        cols = ("id", "name", "level")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings", selectmode="browse")
        self.tree.heading("name", text="目标名称")
        self.tree.heading("level", text="层级")
        self.tree.column("id", width=0, stretch=False)
        self.tree.column("level", width=60, anchor="center")

        self.tree_sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self._auto_scrollbar)
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<MouseWheel>", lambda e: self.tree.yview_scroll(int(-1 * e.delta / 120), "units"))
        # 内容变化后检查是否需要滚动条
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.after_idle(self._update_sb_visibility))
        self.after_idle(self._update_sb_visibility)

        self.refresh_goal_tree()

    def _auto_scrollbar(self, first, last):
        """中间函数：保持 Treeview 的 yscrollcommand 绑定，同时记录状态"""
        self.tree_sb.set(first, last)
        self.after_idle(self._update_sb_visibility)

    def _update_sb_visibility(self):
        """内容未超出可见区域时隐藏滚动条"""
        try:
            vbar = self.tree_sb
            # 获取 Treeview 内部高度和内容高度
            inner_h = self.tree.winfo_height()
            # 获取最后一个 item 的底部位置
            children = self.tree.get_children()
            if not children:
                vbar.pack_forget()
                return
            last_item = children[-1]
            bbox = self.tree.bbox(last_item)
            if bbox:
                content_bottom = bbox[1] + bbox[3]
                # 如果内容底部在可见区域内，隐藏滚动条
                if content_bottom <= inner_h:
                    vbar.pack_forget()
                else:
                    vbar.pack(side="right", fill="y")
            else:
                vbar.pack_forget()
        except Exception:
            vbar.pack_forget()

    def refresh_goal_tree(self):
        self.tree.delete(*self.tree.get_children())
        search = self.search_var.get().lower()
        # 构建 id -> item 映射
        id_to_item = {}

        def insert_node(goal, parent_item=""):
            if search and search not in goal["name"].lower():
                return
            item = self.tree.insert(parent_item, "end",
                                     values=(goal["id"], goal["name"], goal["level"]),
                                     text=goal["name"])
            id_to_item[goal["id"]] = item
            for child_id in goal.get("children", []):
                child = self.find_goal(child_id)
                if child:
                    insert_node(child, item)

        roots = [g for g in self.goals if g.get("parent") is None]
        for g in roots:
            insert_node(g)
        self.after_idle(self._update_sb_visibility)

    def find_goal(self, goal_id):
        for g in self.goals:
            if g["id"] == goal_id:
                return g
        return None

    def choose_wizard(self):
        dlg = tk.Toplevel(self)
        dlg.title("选择拆解模式")
        w, h = 300, 220
        # 居中于父窗口
        self.update_idletasks()
        pw, ph = self.winfo_width(), self.winfo_height()
        px = self.winfo_rootx() + max(0, (pw - w) // 2)
        py = self.winfo_rooty() + max(0, (ph - h) // 2)
        dlg.geometry(f"{w}x{h}+{px}+{py}")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text="请选择目标拆解模式：", font=("", 11, "bold")).pack(pady=(15, 10))

        ttk.Button(dlg, text="📚 通用考研拆解\n（适合所有专业）",
                   width=30, command=lambda: [dlg.destroy(), self.open_wizard_generic()]).pack(pady=5)
        ttk.Button(dlg, text="💻 408 计算机考研\n（数据结构/计组/OS/计网）",
                   width=30, command=lambda: [dlg.destroy(), self.open_wizard_408()]).pack(pady=5)
        ttk.Button(dlg, text="⚡ 11408 专属一键生成\n（预填总分350/数一110/英一65/政治65）",
                   width=30, command=lambda: [dlg.destroy(), self.open_wizard_11408()]).pack(pady=5)
        ttk.Button(dlg, text="取消", command=dlg.destroy, width=30).pack(pady=(10, 15))

    def open_wizard_generic(self):
        SmartGoalWizard(self, self.on_goals_generated, mode="generic")

    def open_wizard_408(self):
        Wizard408(self, self.on_goals_generated)

    def open_wizard_11408(self):
        Wizard408(self, self.on_goals_generated, preset_11408=True)

    def on_goals_generated(self, new_goals):
        self.goals.extend(new_goals)
        DataManager.save(GOALS_FILE, self.goals)
        self.refresh_goal_tree()

    def manual_add(self):
        dialog = tk.Toplevel(self)
        dialog.title("添加目标")
        dialog.geometry("350x200")
        dialog.resizable(False, False)

        ttk.Label(dialog, text="目标名称:").pack(pady=(15, 0))
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(pady=5, padx=20)

        ttk.Label(dialog, text="层级:").pack()
        level_var = tk.StringVar(value="每日")
        ttk.Combobox(dialog, textvariable=level_var,
                      values=["长期", "年度", "月度", "每周", "每日"],
                      width=15, state="readonly").pack(pady=5)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入目标名称")
                return
            goal = {"id": SmartGoalWizard._gid(), "name": name,
                     "level": level_var.get(), "parent": None, "children": []}
            self.goals.append(goal)
            DataManager.save(GOALS_FILE, self.goals)
            self.refresh_goal_tree()
            dialog.destroy()

        ttk.Button(dialog, text="保存", command=save).pack(pady=15)

    def delete_goal(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要删除的目标")
            return
        values = self.tree.item(sel[0], "values")
        gid = values[0]
        if messagebox.askyesno("确认", f"确定删除「{values[1]}」及其子目标吗？"):
            self._delete_recursive(gid)
            DataManager.save(GOALS_FILE, self.goals)
            self.refresh_goal_tree()

    def _delete_recursive(self, gid):
        goal = self.find_goal(gid)
        if not goal:
            return
        for child_id in list(goal.get("children", [])):
            self._delete_recursive(child_id)
        self.goals = [g for g in self.goals if g["id"] != gid]

    def add_to_tasks(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个目标")
            return
        values = self.tree.item(sel[0], "values")
        name = values[1]

        tasks = DataManager.load(TASKS_FILE)
        existing = [t["name"] for t in tasks if t["name"] == name]
        if existing:
            messagebox.showinfo("提示", "该目标已在今日任务中")
            return

        task = {"id": SmartGoalWizard._gid(), "name": name,
                 "done": False, "date": date.today().isoformat(),
                 "duration_min": 30}
        tasks.append(task)
        DataManager.save(TASKS_FILE, tasks)
        self.app.task_tab.refresh_task_list()
        messagebox.showinfo("完成", f"「{name}」已添加到今日任务")


# ============ 今日任务页 ============