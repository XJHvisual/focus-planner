"""统一 OCR 工具 - 智能预处理 + 三引擎 + 代码检测 + Obsidian 导出
用法: python ocr.py <图片> [--engine tesseract|easyocr|paddle] [--md] [--save 笔记名]
"""
import sys, os, argparse, subprocess, time, re
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

TESSERACT = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TESSDATA = os.path.expandvars(r'%LOCALAPPDATA%\tesseract\tessdata')
OBSIDIAN_PCO = r'D:\12081\Documents\PCO'

# ── 图片预处理 ──
def preprocess(image_path, enhance=True):
    if not HAS_PIL:
        return image_path
    img = Image.open(image_path).convert('L')
    if enhance:
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = img.filter(ImageFilter.SHARPEN)
        img = ImageOps.autocontrast(img, cutoff=2)
    out = os.path.join(os.path.dirname(image_path) or '.',
                       f"_ocr_preprocessed_{int(time.time())}.png")
    img.save(out)
    return out

# ── 代码检测与 Markdown 格式化 ──
CODE_KEYWORDS = {
    'python': ['def ', 'class ', 'import ', 'from ', 'return ', 'print(', 'if __name__',
               'self.', 'lambda ', 'try:', 'except ', 'with ', 'yield ', 'async ', 'await '],
    'javascript': ['function ', 'const ', 'let ', 'var ', '=>', 'import {', 'export ',
                   'console.', 'async ', 'await ', 'new Promise', '.then('],
    'java': ['public ', 'private ', 'class ', 'void ', 'static ', 'System.out',
             'import java', 'extends ', 'implements '],
    'sql': ['SELECT ', 'FROM ', 'WHERE ', 'INSERT ', 'UPDATE ', 'DELETE ', 'CREATE TABLE',
            'JOIN ', 'GROUP BY', 'ORDER BY', 'HAVING '],
    'cpp': ['#include', 'int main', 'std::', 'cout', 'cin', 'vector<', 'template<'],
    'bash': ['#!/bin/', 'sudo ', 'apt ', 'pip ', 'echo ', 'export ', 'chmod '],
}

def detect_code_language(text):
    """检测文本最可能是哪种编程语言"""
    scores = {}
    for lang, keywords in CODE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[lang] = score
    if not scores:
        return None
    return max(scores, key=scores.get)

def is_code_line(line):
    """判断单行是否像代码"""
    stripped = line.strip()
    if not stripped:
        return False
    # 缩进行
    if line.startswith('    ') or line.startswith('\t'):
        return True
    # 特殊符号密集
    special_ratio = sum(1 for c in stripped if c in '{}[]()=;:<>.,|&!+-*/%#@')
    if len(stripped) > 5 and special_ratio / len(stripped) > 0.15:
        return True
    # 常见代码模式
    code_patterns = [
        r'^\s*(def|class|import|from|return|if|else|elif|for|while|try|except|with)\s',
        r'^\s*(public|private|protected|static|void|int|String|boolean)\s',
        r'^\s*(const|let|var|function|async|await|export|import)\s',
        r'^\s*[a-zA-Z_]\w*\s*[=<>!]=?\s*',
        r'^\s*[a-zA-Z_]\w*\(.*\)\s*[{;]?\s*$',
        r'^[{}();[\]]\s*$',
        r'^\s*#\s*(include|define|ifdef|endif|pragma)',
        r'^\s*//|/\*|\*/|#\s|-->',
    ]
    for pat in code_patterns:
        if re.match(pat, stripped):
            return True
    return False

def format_as_markdown(text):
    """将 OCR 文本转为 Markdown：自动检测代码块、加粗标题等"""
    lines = text.split('\n')
    result = []
    in_code = False
    code_buf = []
    current_lang = None

    for line in lines:
        if is_code_line(line):
            if not in_code:
                in_code = True
                code_buf = [line]
            else:
                code_buf.append(line)
        else:
            if in_code:
                # 结束代码块
                lang = detect_code_language('\n'.join(code_buf)) or ''
                result.append(f'```{lang}')
                result.extend(code_buf)
                result.append('```')
                result.append('')
                in_code = False
                code_buf = []
            # 检测是否为标题（短行、含中文、不含标点密集）
            stripped = line.strip()
            if stripped and len(stripped) < 50 and not is_code_line(line):
                # 疑似标题：中文开头且不超过30字符
                if re.match(r'^[\u4e00-\u9fff]', stripped) and len(stripped) <= 30:
                    result.append(f'## {stripped}')
                else:
                    result.append(stripped)
            elif stripped:
                result.append(stripped)

    if in_code:
        lang = detect_code_language('\n'.join(code_buf)) or ''
        result.append(f'```{lang}')
        result.extend(code_buf)
        result.append('```')

    return '\n'.join(result)

# ── 保存到 Obsidian ──
def save_to_obsidian(text, note_name, course_dir=None):
    """保存 OCR 结果到 Obsidian PCO 知识库"""
    base = OBSIDIAN_PCO
    if course_dir:
        base = os.path.join(base, course_dir)
    os.makedirs(base, exist_ok=True)

    # 确保 .md 后缀
    if not note_name.endswith('.md'):
        note_name += '.md'

    filepath = os.path.join(base, note_name)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
    return filepath

# ── Tesseract ──
def ocr_tesseract(image_path, lang='chi_sim+eng', psm=6):
    out = os.path.join(os.environ.get('TEMP', '/tmp'), f'ocr_tess_{int(time.time())}')
    env = os.environ.copy()
    env['TESSDATA_PREFIX'] = TESSDATA
    subprocess.run([TESSERACT, image_path, out, '-l', lang, '--psm', str(psm)],
                   capture_output=True, timeout=120, env=env)
    outfile = out + '.txt'
    if os.path.exists(outfile):
        with open(outfile, 'r', encoding='utf-8') as f:
            return f.read()
    return "识别失败"

# ── EasyOCR ──
_easyocr_reader = None
def get_easyocr_reader(langs):
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(langs, gpu=False)
    return _easyocr_reader

def ocr_easyocr(image_path, langs=['ch_sim', 'en']):
    reader = get_easyocr_reader(langs)
    results = reader.readtext(image_path, detail=0)
    return '\n'.join(results)

# ── PaddleOCR ──
_paddle_reader = None
def get_paddle_reader():
    global _paddle_reader
    if _paddle_reader is None:
        from paddleocr import PaddleOCR
        _paddle_reader = PaddleOCR(lang='ch', use_angle_cls=True, show_log=False)
    return _paddle_reader

def ocr_paddle(image_path):
    reader = get_paddle_reader()
    results = reader.ocr(image_path)
    if not results or not results[0]:
        return "识别失败"
    lines = []
    for line in results[0]:
        text = line[1][0]
        lines.append(text)
    return '\n'.join(lines)

# ── 后处理 ──
def clean_text(text):
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) <= 1 and stripped not in '一二三四五六七八九十':
            continue
        if stripped:
            cleaned.append(stripped)
    return '\n'.join(cleaned)

# ── 主流程 ──
def ocr(image_path, engine='auto', lang='chi_sim+eng', markdown=False,
        preprocess_img=True, save_as=None, course_dir=None):
    if not os.path.exists(image_path):
        return f"错误：文件不存在 - {image_path}"

    t_start = time.time()

    # 预处理
    proc_path = image_path
    if preprocess_img and HAS_PIL:
        proc_path = preprocess(image_path)

    # 引擎选择
    if engine == 'auto':
        engine = 'tesseract'

    # OCR
    if engine == 'tesseract':
        result = ocr_tesseract(proc_path, lang)
        result = clean_text(result)
    elif engine == 'easyocr':
        result = ocr_easyocr(proc_path, lang.split(','))
    elif engine == 'paddle':
        result = ocr_paddle(proc_path)
    else:
        result = ocr_tesseract(proc_path, lang)

    # Markdown 格式化（代码检测）
    if markdown:
        result = format_as_markdown(result)

    elapsed = time.time() - t_start
    print(f"[{engine}] {elapsed:.1f}s")

    # 保存到 Obsidian
    if save_as:
        path = save_to_obsidian(result, save_as, course_dir)
        print(f"已保存到: {path}")

    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='统一 OCR 工具')
    parser.add_argument('image', help='图片路径')
    parser.add_argument('--engine', default='auto', choices=['auto', 'tesseract', 'easyocr', 'paddle'])
    parser.add_argument('--lang', default='chi_sim+eng')
    parser.add_argument('--md', action='store_true', help='输出 Markdown 格式（代码检测）')
    parser.add_argument('--no-prep', action='store_true', help='跳过预处理')
    parser.add_argument('--save', help='保存到 Obsidian PCO 的笔记名（不含.md）')
    parser.add_argument('--course', help='课程目录（数据库原理/计算机组成原理/信息安全概论）')
    args = parser.parse_args()

    print(ocr(args.image, args.engine, args.lang, args.md,
              not args.no_prep, args.save, args.course))
