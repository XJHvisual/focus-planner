"""Tesseract OCR 命令行工具 - 快速轻量
用法: python ocr_tess.py <图片路径> [--lang chi_sim+eng] [--psm 6]
"""
import sys, os, subprocess, argparse

TESSERACT = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TESSDATA = os.path.expandvars(r'%LOCALAPPDATA%\tesseract\tessdata')

def ocr_tess(image_path, lang='chi_sim+eng', psm=6):
    if not os.path.exists(image_path):
        print(f"错误：文件不存在 - {image_path}")
        return
    
    out = os.path.expandvars(r'%TEMP%\ocr_tess_output')
    env = os.environ.copy()
    env['TESSDATA_PREFIX'] = TESSDATA
    
    result = subprocess.run(
        [TESSERACT, image_path, out, '-l', lang, '--psm', str(psm)],
        capture_output=True, text=True, timeout=60, env=env
    )
    
    outfile = out + '.txt'
    if os.path.exists(outfile):
        with open(outfile, 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print(f"OCR 失败: {result.stderr}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Tesseract OCR - 快速图片文字识别')
    parser.add_argument('image', help='图片路径')
    parser.add_argument('--lang', default='chi_sim+eng', help='语言 (默认chi_sim+eng)')
    parser.add_argument('--psm', type=int, default=6, help='页面分割模式 (默认6)')
    args = parser.parse_args()
    ocr_tess(args.image, args.lang, args.psm)
