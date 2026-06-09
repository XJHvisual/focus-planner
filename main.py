import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import time
import sys
import atexit
import sqlite3
from datetime import datetime, date, timedelta
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
import tempfile

_LOCK_DIR = os.path.join(tempfile.gettempdir(), "FocusPlannerLock")


def is_another_instance_running():
    """原子目录锁：Windows os.mkdir() 为原子操作，FileExistsError 表示已有实例"""
    try:
        os.mkdir(_LOCK_DIR)
        return False
    except FileExistsError:
        return True


def _cleanup_lock():
    """退出时清理锁目录"""
    try:
        os.rmdir(_LOCK_DIR)
    except (OSError, FileNotFoundError):
        pass

atexit.register(_cleanup_lock)
GOALS_FILE = os.path.join(DATA_DIR, "goals.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
FREE_TIME_FILE = os.path.join(DATA_DIR, "free_time.json")
RECORDS_FILE = os.path.join(DATA_DIR, "records.json")
FOCUS_FILE = os.path.join(DATA_DIR, "focus_log.json")
TRAINING_LOG_FILE = os.path.join(DATA_DIR, "training_log.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# ============ 健身训练详情数据 ============
FITNESS_DETAIL_DATA = {
    0: {  # 周一 上肢
        "title": "💪 周一：上肢力量训练（胸+肩+三头）",
        "subtitle": "全天空闲 | 约60分钟 | 组间休息60秒",
        "actions": [
            (1, "俯卧撑", "4组 × 力竭",
             "面朝下趴在瑜伽垫上，双手撑地略宽于肩，手指朝前，身体从头到脚成一条直线（不塌腰不撅臀）。弯曲手肘整体下降，直到胸部接近地面。用胸部和手臂力量推回到起始位置。全程核心收紧。",
             "做不了标准版可双膝跪地做「跪姿俯卧撑」"),
            (2, "哑铃卧推", "4组 × 10~12次",
             "仰卧瑜伽垫上，双膝弯曲脚踩地。每只手各握一个哑铃举到胸部正上方，掌心朝脚的方向。手肘约45度角。缓慢下放直到哑铃碰到胸部两侧（或手肘碰地面），停顿1秒，用力推回。下放吸气，推起呼气。",
             "推到顶端时不要猛烈锁死手肘"),
            (3, "哑铃飞鸟", "3组 × 12~15次",
             "仰卧瑜伽垫上，双手各持哑铃伸直举到胸部正上方，掌心相对。保持手肘微弯（固定角度不变），双臂向两侧缓慢打开，像「拥抱一个很大的人」，直到胸部被充分拉伸。停顿1秒，用胸部力量重合找回起始位置。",
             "手肘角度全程不变，靠胸部发力不是手臂"),
            (4, "哑铃推举", "4组 × 10~12次",
             "坐在椅子或床边，挺胸收腹，双脚踩实地面。双手各持哑铃举到肩膀两侧，掌心朝前，手肘约90度，哑铃与耳朵齐平。用肩膀力量将哑铃向上推起直到手臂伸直（不要往后仰身体借力）。缓慢下放回起始位置。",
             "不要往后仰身体借力，保持躯干稳定"),
            (5, "哑铃侧平举", "3组 × 12~15次",
             "站立，双脚与肩同宽，膝盖微屈。双手各持哑铃自然下垂，掌心相对。手肘微弯并保持固定，将双臂向两侧抬起，抬到与肩膀同高即可。感受肩部侧面发力。缓慢放下。",
             "不要用太大重量，感受肩部侧面发力"),
            (6, "哑铃俯身飞鸟", "3组 × 12~15次",
             "站立，双脚与肩同宽，膝盖微屈。上半身向前俯身约45~60度，背部挺直（像鞠躬）。双手各持哑铃自然下垂，掌心相对。手肘微弯并固定，将哑铃向两侧抬起直到手臂与地面平行（或略高）。收缩肩胛骨，缓慢放下。",
             "练肩膀后侧和上背部，重量不宜过大"),
            (7, "哑铃颈后臂屈伸", "3组 × 12~15次",
             "坐在椅子或床边，双手共握一只哑铃（两手托住一端，另一端朝下），举到头顶上方手臂伸直。保持上臂不动（贴近耳朵），弯曲手肘让哑铃向脑后下方缓慢下放，直到前臂有拉伸感。用力伸直手臂回到起始位置。",
             "大臂全程不动，只有小臂在动；10kg太重可双手各持一个"),
            (8, "窄距俯卧撑", "3组 × 力竭",
             "和标准俯卧撑一样，但双手间距与肩同宽或更窄（约一拳距离）。手肘贴紧身体两侧不要向外打开。下放时手肘向后收，不是向两侧打开。推起时感受三头肌发力。",
             "同样可以跪姿做"),
        ]
    },
    1: {  # 周二 核心+有氧
        "title": "🔥 周二/周六：核心 + 有氧",
        "subtitle": "晚上空闲 | 约30~40分钟 | 时间紧张可只做核心15min",
        "actions": [
            (1, "卷腹", "4组 × 20次",
             "仰卧瑜伽垫上，双膝弯曲脚踩地。双手轻轻放在耳朵两侧（不抱头）。下背（腰部）始终贴紧地面。用腹部力量将肩胛骨抬离地面即可（不需要坐起来）。缓慢下放，感受腹肌持续张力。",
             "是「卷起来」不是「坐起来」，幅度小但发力更集中；脖子放松"),
            (2, "俄罗斯转体", "3组 × 30次",
             "坐在瑜伽垫上，双膝弯曲脚踩地。上半身向后倾斜约45度，背部挺直。双手在胸前合十（或抱哑铃增加难度）。用腹部力量将上半身左右旋转，尽量让手触碰身体两侧地面。",
             "是躯干在旋转，不是只用手左右摆；转时尽量让手碰地面"),
            (3, "平板支撑", "3组 × 45~60秒",
             "俯卧瑜伽垫上，用前臂（手肘到拳头）撑地，手肘在肩膀正下方。双脚并拢或略分开，脚尖点地。身体从头到脚成一条直线（不塌腰不撅臀）。收紧核心，保持自然呼吸。",
             "如果腰部酸痛说明塌腰了，立刻调整；宁可时间短也要标准"),
            (4, "死虫式", "3组 × 每侧10次",
             "仰卧瑜伽垫上，双手伸直朝天花板，双腿抬起膝盖弯曲90度（小腿与地面平行）。腰部贴紧地面（最重要）。缓慢将右手向头顶伸展同时左腿伸直（不碰地），然后收回。换侧交替进行。全程腰部不能拱起！",
             "全程腰部不能离开地面！腰部拱起说明幅度太大，减小幅度"),
            (5, "登山跑", "3组 × 30秒",
             "从高位平板支撑姿势开始（双手撑地手臂伸直，身体成直线）。交替将左右膝盖快速向胸部方向提拉，像在地面上跑步一样，但身体保持稳定不动。保持核心收紧，呼吸均匀。",
             "臀部不要抬太高，身体尽量保持平稳"),
            (6, "跳绳 / 高抬腿", "15~20分钟",
             "跳绳：中等速度保持节奏。高抬腿（空间不够时）：站立交替快速抬膝至腰部高度，手臂自然摆动。强度：微微出汗、能说话但略喘。可间歇进行（练30秒歇30秒）。",
             "中等强度有氧，不需要一直不停"),
        ]
    },
    3: {  # 周四 下肢
        "title": "🦵 周四/周日：下肢力量训练",
        "subtitle": "周四晚上40~50min | 周日全天50min+拉伸",
        "actions": [
            (1, "哑铃深蹲", "4组 × 12~15次",
             "站立，双脚与肩同宽或略宽，脚尖微微朝外。双手各持哑铃自然下垂。挺胸，背部挺直，目视前方。弯曲膝盖和髋部，像「往椅子上坐」一样下蹲，直到大腿至少与地面平行。用臀部和大腿力量站起。",
             "全程背部挺直不弯腰驼背；下蹲吸气站起呼气"),
            (2, "哑铃箭步蹲", "3组 × 每侧12次",
             "站立，双手各持哑铃垂于身体两侧。右脚向前迈出一大步。弯曲双膝，身体直直下降直到后膝接近地面（不碰地）。前膝不超过脚尖太多。用前腿力量站起回到起始位置。左右交替。",
             "身体保持直立不前倾；步幅要够大，否则前膝压力太大"),
            (3, "哑铃罗马尼亚硬拉", "4组 × 10~12次",
             "站立，双脚与髋同宽，膝盖微弯（全程保持微弯不锁死）。双手各持哑铃垂于身体前方。挺胸，背部完全挺直。以髋部为轴，上半身向前俯身约45度，感受大腿后侧拉伸。臀部往前推回到直立位。",
             "不是弯腰！是「髋关节铰链」动作，臀部往后推，背部全程挺直"),
            (4, "哑铃提踵", "4组 × 15~20次",
             "站立，双手各持哑铃垂于身体两侧。找一本厚书或站在瑜伽垫边缘（让脚跟悬空）。缓慢踮起脚尖，用小腿力量将身体向上推。在最高点停顿1-2秒，缓慢放下脚跟感受拉伸。",
             "动作要慢，感受小腿的收缩和拉伸"),
            (5, "臀桥", "3组 × 15次",
             "仰卧瑜伽垫上，双膝弯曲脚踩地（脚跟靠近臀部）。双手自然放在身体两侧掌心朝下。用臀部力量将髋部向上推起，直到身体从膝盖到肩膀成一条直线。在顶端夹紧臀部1秒，缓慢放下。",
             "想增加难度可在小腹上放一个哑铃"),
            (6, "靠墙静蹲", "3组 × 45~60秒",
             "背靠墙壁站立，双脚向前迈出约一步距离。背部贴紧墙面，弯曲膝盖身体沿墙面下滑。滑到大腿与地面平行（像坐在隐形的椅子上）。保持这个姿势，小腿与地面垂直。",
             "小腿与地面垂直，膝盖不超过脚尖；太难可先蹲浅一点"),
        ]
    },
    4: {  # 周五 背部
        "title": "🔙 周五：背部力量训练（窄距引体+二头）",
        "subtitle": "全天空闲 | 约60分钟 | 组间休息60秒",
        "actions": [
            (1, "窄距引体向上", "4组 × 力竭",
             "双手正握单杠（掌心朝前），间距约与肩同宽或略窄。双臂完全伸直身体悬垂。用背部和手臂力量将身体向上拉，直到下巴过杠。拉起时肩胛骨向下向后收（想象把腋窝塞进裤兜里）。缓慢下放到手臂伸直。",
             "做不了可用：跳起借力（重点练离心）、脚踩凳子辅助、弹力带辅助"),
            (2, "哑铃单臂划船", "4组 × 每侧10~12次",
             "左侧身体朝向瑜伽垫，左膝和左手撑在垫子上（左手在肩膀正下方）。右脚向后伸或右膝也跪在垫子上。右手持哑铃手臂自然下垂。背部挺直，用背部力量将哑铃向腰腹部拉起（想象用手肘去碰天花板）。顶峰收缩1秒，缓慢放下。",
             "背部全程挺直；不要用手臂发力拉"),
            (3, "哑铃俯身划船（双手）", "3组 × 12次",
             "站立，双脚与肩同宽，膝盖微弯。上半身向前俯身约45度，背部挺直。双手各持哑铃自然下垂，掌心相对。将哑铃向身体两侧（腰腹部方向）拉起。顶峰收缩肩胛骨，缓慢放下。",
             "与俯身飞鸟的区别：划船是往身体方向拉（手肘弯曲），飞鸟是往两侧打开（手肘固定）"),
            (4, "哑铃弯举", "4组 × 10~12次",
             "站立，双脚与肩同宽，膝盖微屈。双手各持哑铃自然下垂，掌心朝前。上臂贴紧身体两侧不动，弯曲手肘将哑铃向上弯举到肩膀前方。停顿1秒，缓慢放下（约2秒感受拉伸）。",
             "不要甩腰借力，上臂全程不动；放下时约2秒感受拉伸"),
            (5, "锤式弯举", "3组 × 12次",
             "和普通弯举姿势一样，但掌心相对（像握锤子一样）而不是朝前。同样弯曲手肘将哑铃向上弯举到肩膀前方。缓慢放下。",
             "练肱肌（手臂外侧），能让手臂看起来更粗"),
            (6, "单杠悬垂", "3组 × 30~45秒",
             "双手正握单杠，手臂伸直，身体自然悬垂。全身放松让身体自然拉伸。保持30~45秒。",
             "拉伸脊柱和背部肌肉，增强握力，改善体态"),
        ]
    },
    5: {  # 周六 核心+有氧（复用周二）
        "title": "🔥 周六：核心 + 有氧",
        "subtitle": "全天空闲 | 约30~40分钟 | 时间紧张可只做核心15min",
        "actions": [
            (1, "卷腹", "4组 × 20次",
             "仰卧瑜伽垫上，双膝弯曲脚踩地。双手轻轻放在耳朵两侧（不抱头）。下背（腰部）始终贴紧地面。用腹部力量将肩胛骨抬离地面即可（不需要坐起来）。缓慢下放，感受腹肌持续张力。",
             "是「卷起来」不是「坐起来」，幅度小但发力更集中；脖子放松"),
            (2, "俄罗斯转体", "3组 × 30次",
             "坐在瑜伽垫上，双膝弯曲脚踩地。上半身向后倾斜约45度，背部挺直。双手在胸前合十（或抱哑铃增加难度）。用腹部力量将上半身左右旋转，尽量让手触碰身体两侧地面。",
             "是躯干在旋转，不是只用手左右摆；转时尽量让手碰地面"),
            (3, "平板支撑", "3组 × 45~60秒",
             "俯卧瑜伽垫上，用前臂（手肘到拳头）撑地，手肘在肩膀正下方。双脚并拢或略分开，脚尖点地。身体从头到脚成一条直线（不塌腰不撅臀）。收紧核心，保持自然呼吸。",
             "如果腰部酸痛说明塌腰了，立刻调整；宁可时间短也要标准"),
            (4, "死虫式", "3组 × 每侧10次",
             "仰卧瑜伽垫上，双手伸直朝天花板，双腿抬起膝盖弯曲90度（小腿与地面平行）。腰部贴紧地面（最重要）。缓慢将右手向头顶伸展同时左腿伸直（不碰地），然后收回。换侧交替进行。全程腰部不能拱起！",
             "全程腰部不能离开地面！腰部拱起说明幅度太大，减小幅度"),
            (5, "登山跑", "3组 × 30秒",
             "从高位平板支撑姿势开始（双手撑地手臂伸直，身体成直线）。交替将左右膝盖快速向胸部方向提拉，像在地面上跑步一样，但身体保持稳定不动。保持核心收紧，呼吸均匀。",
             "臀部不要抬太高，身体尽量保持平稳"),
            (6, "跳绳 / 高抬腿", "15~20分钟",
             "跳绳：中等速度保持节奏。高抬腿（空间不够时）：站立交替快速抬膝至腰部高度，手臂自然摆动。强度：微微出汗、能说话但略喘。可间歇进行（练30秒歇30秒）。",
             "中等强度有氧，不需要一直不停"),
        ]
    },
    6: {  # 周日 下肢力量（复用周四）
        "title": "🦵 周日：下肢力量训练",
        "subtitle": "全天空闲 | 约50min+拉伸",
        "actions": [
            (1, "哑铃深蹲", "4组 × 12~15次",
             "站立，双脚与肩同宽或略宽，脚尖微微朝外。双手各持哑铃自然下垂。挺胸，背部挺直，目视前方。弯曲膝盖和髋部，像「往椅子上坐」一样下蹲，直到大腿至少与地面平行。用臀部和大腿力量站起。",
             "全程背部挺直不弯腰驼背；下蹲吸气站起呼气"),
            (2, "哑铃箭步蹲", "3组 × 每侧12次",
             "站立，双手各持哑铃垂于身体两侧。右脚向前迈出一大步。弯曲双膝，身体直直下降直到后膝接近地面（不碰地）。前膝不超过脚尖太多。用前腿力量站起回到起始位置。左右交替。",
             "身体保持直立不前倾；步幅要够大，否则前膝压力太大"),
            (3, "哑铃罗马尼亚硬拉", "4组 × 10~12次",
             "站立，双脚与髋同宽，膝盖微弯（全程保持微弯不锁死）。双手各持哑铃垂于身体前方。挺胸，背部完全挺直。以髋部为轴，上半身向前俯身约45度，感受大腿后侧拉伸。臀部往前推回到直立位。",
             "不是弯腰！是「髋关节铰链」动作，臀部往后推，背部全程挺直"),
            (4, "哑铃提踵", "4组 × 15~20次",
             "站立，双手各持哑铃垂于身体两侧。找一本厚书或站在瑜伽垫边缘（让脚跟悬空）。缓慢踮起脚尖，用小腿力量将身体向上推。在最高点停顿1-2秒，缓慢放下脚跟感受拉伸。",
             "动作要慢，感受小腿的收缩和拉伸"),
            (5, "臀桥", "3组 × 15次",
             "仰卧瑜伽垫上，双膝弯曲脚踩地（脚跟靠近臀部）。双手自然放在身体两侧掌心朝下。用臀部力量将髋部向上推起，直到身体从膝盖到肩膀成一条直线。在顶端夹紧臀部1秒，缓慢放下。",
             "想增加难度可在小腹上放一个哑铃"),
            (6, "靠墙静蹲", "3组 × 45~60秒",
             "背靠墙壁站立，双脚向前迈出约一步距离。背部贴紧墙面，弯曲膝盖身体沿墙面下滑。滑到大腿与地面平行（像坐在隐形的椅子上）。保持这个姿势，小腿与地面垂直。",
             "小腿与地面垂直，膝盖不超过脚尖；太难可先蹲浅一点"),
        ]
    },
}


# ============ 数据管理 ============
class DataManager:
    @staticmethod
    def load(path, default=None):
        if default is None:
            default = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    @staticmethod
    def save(path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ============ 智能拆解向导 ============
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

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<MouseWheel>", lambda e: self.tree.yview_scroll(int(-1 * e.delta / 120), "units"))

        self.refresh_goal_tree()

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
class BuiltinTracker:
    """轻量级前台窗口时间追踪器，使用 ctypes 调用 Win32 API，零外部依赖"""
    POLL_INTERVAL = 2  # 秒

    def __init__(self):
        self._running = False
        self._thread = None
        self._current_app = None
        self._current_title = ""
        self._session_start = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._init_db()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._flush()

    def _init_db(self):
        conn = sqlite3.connect(TRACKER_DB)
        conn.execute("""CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            window_title TEXT DEFAULT '',
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            category TEXT DEFAULT '其他',
            productivity_score INTEGER DEFAULT 50,
            UNIQUE(app_name, start_time)
        )""")
        conn.commit()
        # 一次性迁移：从旧 AppTimeTracker V2 数据库导入已有记录
        old_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app-time-tracker-v2", "dist", "data", "tracker_v2.db")
        if os.path.exists(old_db):
            cur = conn.execute("SELECT COUNT(*) FROM usage_records")
            if cur.fetchone()[0] == 0:
                try:
                    conn.execute("ATTACH ? AS old_db", (old_db,))
                    conn.execute(
                        "INSERT OR IGNORE INTO usage_records(app_name, window_title, start_time, end_time, duration_seconds, category, productivity_score) SELECT app_name, window_title, start_time, end_time, duration_seconds, category, productivity_score FROM old_db.usage_records"
                    )
                    conn.commit()
                    conn.execute("DETACH DATABASE old_db")
                except Exception as e:
                    print(f"数据迁移失败: {e}")
        conn.close()

    _title_map = {
        "MainDialog": "鸣潮", "鸣潮": "鸣潮",
        "AppTimeTracker V2": "应用时间追踪器",
        "QClaw": "QClaw",
        "无畏契约": "valorant",
    }
    IGNORE_APPS = {"nexus", "nexusportable", "rocketdock", "rainmeter", "wallpaperengine"}

    def _get_foreground(self):
        """通过 Win32 API 获取当前前台窗口信息"""
        import ctypes
        from ctypes import wintypes
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None, ""
            # 窗口标题
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value or ""
            # 进程名
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process_name = "unknown"
            if pid.value:
                kernel32 = ctypes.windll.kernel32
                h_process = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
                if h_process:
                    exe_buf = ctypes.create_unicode_buffer(260)
                    exe_len = wintypes.DWORD(260)
                    if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buf, ctypes.byref(exe_len)):
                        process_name = os.path.basename(exe_buf.value).lower().replace('.exe', '')
                    kernel32.CloseHandle(h_process)

            # 忽略规则
            if process_name in self.IGNORE_APPS:
                return None, ""

            # 进程名归一化
            import re
            # 通用：去掉 _pc、_x64、-win64-*、_win32_* 等平台/版本后缀
            process_name = re.sub(r'[-_](pc|x64|x86|win64.*|win32.*)$', '', process_name, flags=re.IGNORECASE)
            if process_name == "valorant-win64-shipping":
                process_name = "valorant"
            elif process_name == "pythonw" and "专注规划器" in title:
                process_name = "专注规划器"
            elif process_name == "explorer":
                process_name = "文件资源管理器"
            elif process_name == "qclaw":
                process_name = "QClaw"

            # 标题映射（unknown 进程按标题识别）
            if process_name == "unknown" and title.strip():
                matched = False
                for key, app_name in self._title_map.items():
                    if key in title:
                        process_name = app_name
                        matched = True
                        break
                if not matched and title.strip():
                    # 用标题作为应用名（前20字符）
                    clean = title.strip()
                    process_name = clean[:20] if len(clean) <= 20 else clean[:18] + "…"
            elif process_name == "unknown" and (not title or not title.strip()):
                return None, ""

            return process_name, title
        except Exception:
            return None, ""

    def _run(self):
        while self._running:
            try:
                app, title = self._get_foreground()
                if app and app != self._current_app:
                    self._flush()
                    self._current_app = app
                    self._current_title = title
                    self._session_start = datetime.now()
                time.sleep(self.POLL_INTERVAL)
            except Exception:
                time.sleep(self.POLL_INTERVAL)

    def _flush(self):
        if not self._current_app or not self._session_start:
            return
        now = datetime.now()
        duration = (now - self._session_start).total_seconds()
        if duration < 1:
            return
        try:
            conn = sqlite3.connect(TRACKER_DB)
            conn.execute(
                "INSERT OR IGNORE INTO usage_records(app_name, window_title, start_time, end_time, duration_seconds) VALUES(?,?,?,?,?)",
                (self._current_app, self._current_title,
                 self._session_start.isoformat(), now.isoformat(), int(duration))
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


# ============ 📊 时间追踪 Tab（读取 AppTimeTracker V2 数据库） ============
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
        ttk.Entry(row1, textvariable=self.weight_var, width=7).pack(side="left", padx=(0,15))
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
        cols = ("date", "weight", "training_done", "training_total")
        self.rec_tree = ttk.Treeview(bot, columns=cols, show="headings", height=6)
        self.rec_tree.heading("date", text="日期")
        self.rec_tree.heading("weight", text="体重(kg)")
        self.rec_tree.heading("training_done", text="完成训练")
        self.rec_tree.heading("training_total", text="总训练")
        self.rec_tree.column("date", width=100)
        self.rec_tree.column("weight", width=80)
        self.rec_tree.column("training_done", width=80)
        self.rec_tree.column("training_total", width=80)
        rec_sb = ttk.Scrollbar(bot, orient="vertical", command=self.rec_tree.yview)
        self.rec_tree.configure(yscrollcommand=rec_sb.set)
        self.rec_tree.pack(side="left", fill="both", expand=True)
        rec_sb.pack(side="right", fill="y")
        self.rec_tree.bind("<MouseWheel>", lambda e: self.rec_tree.yview_scroll(int(-1 * e.delta / 120), "units"))

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
        self.weight_var.set("")
        self.refresh_progress()
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
        for ds in dates:
            entry = log.get(ds, {})
            self.rec_tree.insert("", "end", values=(
                ds,
                f"{entry.get('weight', '-')}" if entry.get('weight') else "-",
                entry.get("training_done", 0),
                entry.get("training_total", 0)
            ))

        self.draw_weight_chart()
        self.draw_rate_chart()

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


class FocusPlannerApp:
    def __init__(self):

        self.root = tk.Tk()
        self.root.title("专注规划器 v3.0")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        # 样式
        self._setup_style()

        # 头部
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=12, pady=(12, 0))
        ttk.Label(header, text="📖 专注规划器",
                  font=("Microsoft YaHei", 18, "bold")).pack(side="left")
        ttk.Label(header, text="考研路上，每一步都算数",
                  foreground="#909090",
                  font=("Microsoft YaHei", 10)).pack(side="left", padx=12)

        # 右侧：时钟 + 倒计时 + 设置按钮
        right_frame = ttk.Frame(header)
        right_frame.pack(side="right")

        # 实时时钟
        now = datetime.now()
        self.clock_label = ttk.Label(right_frame,
            text=now.strftime("%m月%d日 %H:%M:%S"),
            font=("Microsoft YaHei", 13, "bold"), foreground="#333")
        self.clock_label.pack(side="left", padx=(0, 15))
        self._tick_clock()

        # 倒计时（只有设了考试日才显示）
        self.exam_date = self._load_settings().get("exam_date")
        self.countdown_label = ttk.Label(right_frame, text="",
            font=("Microsoft YaHei", 12, "bold"))
        if self.exam_date:
            self.countdown_label.pack(side="left", padx=(0, 8))
        self._refresh_countdown()

        # 设置按钮
        self.settings_btn = ttk.Button(right_frame, text="⚙ 考试日",
            command=self._set_exam_date, width=9)
        self.settings_btn.pack(side="left")

        # 左侧导航 + 右侧内容区 — 统一白底，无缝过渡
        BODY_BG = "#FFFFFF"

        body = tk.Frame(self.root, bg=BODY_BG)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 左侧边栏（同色白底，通过选中态区分）
        sidebar = tk.Frame(body, bg=BODY_BG, width=115, highlightthickness=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Frame(sidebar, bg=BODY_BG, height=6).pack(fill="x")

        # 右侧内容区（同色白底）
        self.content = tk.Frame(body, bg=BODY_BG)
        self.content.pack(side="left", fill="both", expand=True)

        # 创建所有 Tab（作为 content 的子 widget）
        self.goal_tab = GoalTab(self.content, self)
        self.task_tab = TaskTab(self.content, self)
        self.week_tab = WeekTab(self.content, self)
        self.timer_stats_tab = TimerStatsTab(self.content, self)
        self.progress_tab = ProgressTab(self.content, self)
        self.timetrack_tab = TimeTrackTab(self.content, self)

        # 启动内置追踪器
        self.tracker = BuiltinTracker()
        self.tracker.start()

        # 导航按钮
        SIDEBAR_FONT = ("Microsoft YaHei", 10)
        self.nav_btns = {}
        nav_items = [
            ("🎯  目标拆解", self.goal_tab, "goal"),
            ("📝  今日任务", self.task_tab, "task"),
            ("📅  周计划表", self.week_tab, "week"),
            ("⏱📊 专注·统计", self.timer_stats_tab, "timer"),
            ("📈  训练进度", self.progress_tab, "progress"),
            ("📊  时间追踪", self.timetrack_tab, "timetrack"),
        ]
        for i, (label, tab, key) in enumerate(nav_items):
            btn = tk.Button(sidebar, text=label, font=SIDEBAR_FONT,
                           bg=BODY_BG, fg="#5F6368", bd=0,
                           activebackground="#E8F0FE", activeforeground="#1967D2",
                           anchor="w", padx=12, pady=8,
                           cursor="hand2",
                           command=lambda k=key: self._switch_tab(k))
            btn.pack(fill="x", pady=(6 if i == 0 else 0, 0))
            self.nav_btns[key] = btn

        tk.Frame(sidebar, bg=BODY_BG, height=6).pack(fill="x", side="bottom")

        # 默认选中第一个
        self._switch_tab("goal")

        # 启动
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def _switch_tab(self, key):
        """切换左侧导航内容"""
        # 隐藏所有
        for tab in (self.goal_tab, self.task_tab, self.week_tab,
                     self.timer_stats_tab, self.progress_tab,
                     self.timetrack_tab):
            tab.pack_forget()
        # 重置所有按钮样式
        for k, btn in self.nav_btns.items():
            btn.config(bg="#FFFFFF", fg="#5F6368")
        # 高亮当前
        self.nav_btns[key].config(bg="#E8F0FE", fg="#1967D2")
        # 显示对应内容
        tab_map = {
            "goal": self.goal_tab,
            "task": self.task_tab,
            "week": self.week_tab,
            "timer": self.timer_stats_tab,
            "progress": self.progress_tab,
            "timetrack": self.timetrack_tab,
        }
        tab_map[key].pack(fill="both", expand=True)
        # 刷新需要实时数据的 Tab
        if key == "timer":
            self.timer_stats_tab.refresh_stats()
        elif key == "progress":
            self.progress_tab.refresh_progress()
        elif key == "timetrack":
            self.timetrack_tab.refresh()

    def on_close(self):
        self.tracker.stop()
        self.root.destroy()

    # ── 样式 ──
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        FONT = "Microsoft YaHei"
        BG = "#FFFFFF"
        # 全局白底
        style.configure(".", font=(FONT, 10), background=BG, fieldbackground=BG)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", font=(FONT, 10), background=BG)
        style.configure("TLabelframe", background=BG)
        style.configure("TLabelframe.Label", font=(FONT, 10, "bold"), background=BG)
        style.configure("TButton", font=(FONT, 10), padding=(8, 4))
        style.configure("TRadiobutton", font=(FONT, 10), background=BG)
        style.configure("TEntry", font=(FONT, 10), fieldbackground="#F5F6F8",
                       borderwidth=1, relief="solid")
        style.configure("TCombobox", font=(FONT, 10), fieldbackground="#F5F6F8")
        style.configure("TSpinbox", font=(FONT, 10), fieldbackground="#F5F6F8")
        style.map("TEntry", fieldbackground=[("focus", "#FFFFFF")])
        style.map("TCombobox", fieldbackground=[("focus", "#FFFFFF")])
        style.configure("Treeview", font=(FONT, 10), rowheight=26)
        style.configure("Treeview.Heading", font=(FONT, 10, "bold"))
        # 根窗口也设白底
        self.root.configure(background=BG)

    # ── 设置 ──
    def _load_settings(self):
        return DataManager.load(SETTINGS_FILE, default={})

    def _save_settings(self, data):
        DataManager.save(SETTINGS_FILE, data)

    def _set_exam_date(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("设置考试日期")
        dlg.geometry("320x180")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text="请输入考研初试日期：",
                  font=("Microsoft YaHei", 11, "bold")).pack(pady=(18, 10))

        entry_frame = ttk.Frame(dlg)
        entry_frame.pack()

        cur_date = self._load_settings().get("exam_date", "2026-12-19")
        today = date.today()

        ttk.Label(entry_frame, text="年", font=("Microsoft YaHei", 10)).pack(side="left")
        year_var = tk.StringVar(value=cur_date[:4] if cur_date else str(today.year))
        year_entry = ttk.Spinbox(entry_frame, from_=2025, to=2030, width=5,
                                  textvariable=year_var, font=("Microsoft YaHei", 11))
        year_entry.pack(side="left", padx=(0, 5))

        ttk.Label(entry_frame, text="月", font=("Microsoft YaHei", 10)).pack(side="left")
        month_var = tk.StringVar(value=cur_date[5:7] if cur_date else "12")
        month_entry = ttk.Spinbox(entry_frame, from_=1, to=12, width=4,
                                   textvariable=month_var, font=("Microsoft YaHei", 11))
        month_entry.pack(side="left", padx=(0, 5))

        ttk.Label(entry_frame, text="日", font=("Microsoft YaHei", 10)).pack(side="left")
        day_var = tk.StringVar(value=cur_date[8:10] if cur_date else "19")
        day_entry = ttk.Spinbox(entry_frame, from_=1, to=31, width=4,
                                 textvariable=day_var, font=("Microsoft YaHei", 11))
        day_entry.pack(side="left")

        def save():
            try:
                y, m, d = int(year_var.get()), int(month_var.get()), int(day_var.get())
                new_date = date(y, m, d)
                iso = new_date.isoformat()
                dlg.destroy()
                self._save_settings({"exam_date": iso})
                self.exam_date = iso
                if not self.countdown_label.winfo_ismapped():
                    self.countdown_label.pack(side="left", padx=(0, 8),
                                              before=self.settings_btn)
                self._refresh_countdown()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的日期", parent=dlg)

        def clear():
            dlg.destroy()
            self._save_settings({})
            self.exam_date = None
            self.countdown_label.pack_forget()
            self.countdown_label.config(text="")

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=(12, 0))
        ttk.Button(btn_frame, text="✓ 确定", command=save, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✗ 取消", command=dlg.destroy, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清除", command=clear, width=10).pack(side="left", padx=5)

    # ── 实时时钟 ──
    def _tick_clock(self):
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%m月%d日 %H:%M:%S"))
        # 每秒刷新
        self.root.after(1000, self._tick_clock)

    # ── 倒计时 ──
    def _refresh_countdown(self):
        if self.exam_date:
            try:
                ed = date.fromisoformat(self.exam_date)
                days_left = (ed - date.today()).days
                if days_left < 0:
                    text = "🎓 考试已结束"
                    color = "#666"
                else:
                    text = f"⏳ 距考研 {days_left} 天"
                    if days_left <= 30:
                        color = "#F44336"
                    elif days_left <= 90:
                        color = "#FF9800"
                    else:
                        color = "#1976D2"
                self.countdown_label.config(text=text, foreground=color)
            except Exception:
                pass
        # 每10分钟刷新（天级别不需要太频繁）
        self.root.after(600000, self._refresh_countdown)


if __name__ == "__main__":
    if is_another_instance_running():
        _cleanup_lock()
        sys.exit(0)
    FocusPlannerApp()