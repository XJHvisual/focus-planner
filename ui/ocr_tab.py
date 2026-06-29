"""OCR 识别页 - 图片转文字 + Markdown + Obsidian 导出"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, threading, subprocess, time, re
from PIL import Image, ImageTk

TESSERACT = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TESSDATA = os.path.expandvars(r'%LOCALAPPDATA%\tesseract\tessdata')
OBSIDIAN_PCO = r'D:\12081\Documents\PCO'

from ocr import format_as_markdown, save_to_obsidian, clean_text

# ── 引擎可用性检测（用 find_spec 避免导入卡 UI）──
import importlib.util as _iu
def _check_tesseract():
    return os.path.exists(TESSERACT) and os.path.isdir(TESSDATA)

def _check_easyocr():
    return _iu.find_spec("easyocr") is not None

def _check_paddle():
    return _iu.find_spec("paddleocr") is not None

class OcrTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.image_path = None
        self._preview_img = None

        # 检测可用引擎
        self.engines = []
        if _check_tesseract():
            self.engines.append(("tesseract", "Tesseract"))
        if _check_easyocr():
            self.engines.append(("easyocr", "EasyOCR"))
        if _check_paddle():
            self.engines.append(("paddle", "PaddleOCR"))
        if not self.engines:
            self.engines = [("none", "无可用引擎")]

        # 顶部
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 3))
        ttk.Label(top, text="🔍 OCR 文字识别", font=("", 13, "bold")).pack(side="left")

        # 引擎选择（只显示可用引擎）
        engine_frame = ttk.Frame(top)
        engine_frame.pack(side="right")
        self.engine_var = tk.StringVar(value=self.engines[0][0])
        for val, label in self.engines:
            ttk.Radiobutton(engine_frame, text=label, variable=self.engine_var,
                            value=val).pack(side="right", padx=(3, 0))

        # Markdown 开关
        self.md_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Markdown", variable=self.md_var).pack(side="right", padx=10)

        # 图片预览区
        preview_frame = ttk.Frame(self)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.canvas = tk.Canvas(preview_frame, bg="#F5F5F5", highlightthickness=1,
                                 highlightbackground="#DDD")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(300, 100, text="点击按钮选择图片或从剪贴板粘贴",
                                 fill="#999", font=("", 11), tags="placeholder")

        # 按钮栏
        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", padx=10, pady=5)
        self.select_btn = ttk.Button(btn_bar, text="📁 选择", command=self.select_image)
        self.select_btn.pack(side="left", padx=(0, 4))
        self.paste_btn = ttk.Button(btn_bar, text="📋 粘贴", command=self.paste_image)
        self.paste_btn.pack(side="left", padx=(0, 8))
        self.ocr_btn = ttk.Button(btn_bar, text="🔍 开始识别", command=self.start_ocr,
                                   state="disabled", style="Primary.TButton")
        self.ocr_btn.pack(side="left", padx=(0, 8))
        self.progress = ttk.Progressbar(btn_bar, mode="indeterminate", length=80)
        self.status_label = ttk.Label(btn_bar, text="", foreground="#666")

        # 结果区
        result_frame = ttk.LabelFrame(self, text="识别结果", padding=5)
        result_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.result_text = tk.Text(result_frame, wrap="word", font=("Microsoft YaHei", 10),
                                    bg="#FAFAFA", relief="flat", padx=8, pady=8)
        self.result_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(result_frame, command=self.result_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.result_text.config(yscrollcommand=scrollbar.set)

        # 底部栏
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Button(bottom, text="📋 复制", command=self.copy_result).pack(side="left")
        ttk.Button(bottom, text="🗑 清空", command=self.clear_result).pack(side="left", padx=5)
        ttk.Button(bottom, text="💾 存到 Obsidian", command=self.save_to_obsidian_dialog).pack(side="right")
        ttk.Button(bottom, text="📝 重新格式化", command=self.reformat).pack(side="right", padx=5)

    def _set_image(self, img_path):
        self.image_path = img_path
        self.show_preview(img_path)
        self.ocr_btn.config(state="normal")

    def select_image(self):
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif"), ("所有文件", "*.*")]
        )
        if path:
            self._set_image(path)

    def paste_image(self):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showinfo("提示", "剪贴板中没有图片")
                return
            # 保存到临时文件
            tmp = os.path.join(os.environ.get('TEMP', '.'), f'ocr_clipboard_{int(time.time())}.png')
            img.save(tmp)
            self._set_image(tmp)
        except Exception as e:
            messagebox.showerror("错误", f"粘贴失败：{e}")

    def show_preview(self, path):
        try:
            from PIL import ImageOps
            img = Image.open(path)
            # 自动修正 EXIF 旋转（手机拍照常见问题）
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass  # 无 EXIF 或无法解析，保持原样
            w, h = img.size
            cw = self.canvas.winfo_width() or 600
            ch = self.canvas.winfo_height() or 200
            ratio = min((cw - 20) / w, (ch - 20) / h, 1.0)
            nw, nh = int(w * ratio), int(h * ratio)
            img = img.resize((nw, nh), Image.LANCZOS)
            self._preview_img = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(cw // 2, ch // 2, image=self._preview_img, anchor="center")
            self.canvas.create_text(cw // 2, ch - 10,
                                     text=os.path.basename(path), fill="#888", font=("", 8))
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(300, 100, text=f"无法预览：{e}", fill="#999")

    def start_ocr(self):
        if not self.image_path:
            return
        self.ocr_btn.config(state="disabled")
        self.progress.pack(side="left", padx=8)
        self.progress.start()
        self.status_label.pack(side="left")
        self.status_label.config(text="识别中...")
        engine = self.engine_var.get()
        use_md = self.md_var.get()
        threading.Thread(target=self._run_ocr, args=(engine, use_md), daemon=True).start()

    def _run_ocr(self, engine, use_md):
        try:
            env = os.environ.copy()
            env['TESSDATA_PREFIX'] = TESSDATA
            env['PYTHONHOME'] = ''
            env['UV_INTERNAL__PYTHONHOME'] = ''

            if engine == "tesseract":
                result = self._ocr_tesseract(self.image_path, env)
                result = clean_text(result)
            elif engine == "easyocr":
                result = self._ocr_easyocr(self.image_path)
            elif engine == "paddle":
                result = self._ocr_paddle(self.image_path)
            else:
                result = "无可用引擎，请安装 Tesseract/EasyOCR/PaddleOCR"

            if use_md and result and engine != "none":
                result = format_as_markdown(result)

        except Exception as e:
            result = f"识别失败：{e}"

        self.after(0, lambda: self._ocr_done(result))

    def _ocr_tesseract(self, path, env):
        out = os.path.join(os.environ.get('TEMP', '.'), f'ocr_gui_{int(time.time())}')
        subprocess.run([TESSERACT, path, out, '-l', 'chi_sim+eng', '--psm', '6'],
                       capture_output=True, timeout=120, env=env)
        outfile = out + '.txt'
        if os.path.exists(outfile):
            with open(outfile, 'r', encoding='utf-8') as f:
                return f.read()
        return "识别失败"

    def _ocr_easyocr(self, path):
        import easyocr
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
        results = reader.readtext(path, detail=0)
        return '\n'.join(results)

    def _ocr_paddle(self, path):
        from paddleocr import PaddleOCR
        reader = PaddleOCR(lang='ch', use_angle_cls=True, show_log=False)
        results = reader.ocr(path)
        if not results or not results[0]:
            return "识别失败"
        return '\n'.join(line[1][0] for line in results[0])

    def _ocr_done(self, text):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label.pack_forget()
        self.ocr_btn.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.status_label.config(text="✓ 完成")
        self.status_label.pack(side="left")

    def reformat(self):
        text = self.result_text.get("1.0", "end-1c")
        if text.strip():
            formatted = format_as_markdown(text)
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", formatted)
            self.status_label.config(text="✓ 已格式化")

    def copy_result(self):
        text = self.result_text.get("1.0", "end-1c")
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_label.config(text="✓ 已复制")

    def clear_result(self):
        self.result_text.delete("1.0", "end")
        self.status_label.config(text="")

    def save_to_obsidian_dialog(self):
        text = self.result_text.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("提示", "没有可保存的内容")
            return

        dlg = tk.Toplevel(self)
        dlg.title("保存到 Obsidian PCO")
        dlg.geometry("400x200")
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text="笔记名称：", font=("", 11)).pack(pady=(15, 5))
        name_var = tk.StringVar(value="OCR_" + time.strftime("%Y%m%d_%H%M%S"))
        name_entry = ttk.Entry(dlg, textvariable=name_var, width=30, font=("", 11))
        name_entry.pack(pady=(0, 10))
        name_entry.select_range(0, 'end')

        ttk.Label(dlg, text="课程目录（可选）：", font=("", 10)).pack()
        courses = [d for d in os.listdir(OBSIDIAN_PCO)
                   if os.path.isdir(os.path.join(OBSIDIAN_PCO, d)) and not d.startswith('.')]
        course_var = tk.StringVar()
        course_combo = ttk.Combobox(dlg, textvariable=course_var, values=courses,
                                     state="readonly", width=28)
        course_combo.pack(pady=(0, 15))

        def do_save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("错误", "请输入笔记名称", parent=dlg)
                return
            course = course_var.get().strip() or None
            try:
                path = save_to_obsidian(text, name, course)
                dlg.destroy()
                self.status_label.config(text=f"✓ 已保存到 {os.path.basename(path)}")
                self.status_label.pack(side="left")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败：{e}", parent=dlg)

        btn_f = ttk.Frame(dlg)
        btn_f.pack()
        ttk.Button(btn_f, text="✓ 保存", command=do_save, width=10).pack(side="left", padx=5)
        ttk.Button(btn_f, text="✗ 取消", command=dlg.destroy, width=10).pack(side="left", padx=5)
