# -*- coding: utf-8 -*-
import re

with open(r'D:\QClawWorkspace\all_in_one\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace all instances of ASCII double-quotes used as Chinese quotation marks
# Pattern: a CJK character immediately followed by ASCII " and ending with ASCII "
# We'll match: (CJK_char)"(Chinese_text)" and replace with (CJK_char)「(Chinese_text)」

def fix_chinese_quotes(text):
    result = text
    # Keep replacing until no more found
    while True:
        # Match: CJK char + ASCII " + CJK text + ASCII "
        m = re.search(r'([\u4e00-\u9fff])"([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+)"', result)
        if not m:
            break
        old = m.group(0)
        new = m.group(1) + '\u300c' + m.group(2) + '\u300d'
        result = result.replace(old, new, 1)
    return result

count_before = content.count('"\u52a0')
content2 = fix_chinese_quotes(content)
count_after = content2.count('"\u52a0')
print(f'Fixed {count_before - count_after} occurrences of Chinese quotes (ASCII)')

# Verify with a syntax check
import ast
try:
    ast.parse(content2)
    print('Syntax OK!')
except SyntaxError as e:
    print(f'Still has syntax error: {e}')
    # Find the line
    lines = content2.split('\n')
    if hasattr(e, 'lineno') and e.lineno:
        print(f'Line {e.lineno}: {repr(lines[e.lineno-1][:100])}')

with open(r'D:\QClawWorkspace\all_in_one\main.py', 'w', encoding='utf-8') as f:
    f.write(content2)
print('Saved')
