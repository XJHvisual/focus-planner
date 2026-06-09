# -*- coding: utf-8 -*-
with open(r'D:\QClawWorkspace\all_in_one\main.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('fill="tk.Y"', 'fill=tk.Y').replace('fill="tk.X"', 'fill=tk.X')
with open(r'D:\QClawWorkspace\all_in_one\main.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixed')
