# -*- coding: utf-8 -*-
with open(r'D:\dev\VOC리포트\scripts\sync_channeltalk_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'if not full_tag|tags|tag_map', text)]
for idx in matches[:10]:
    print(text[max(0, idx-50):idx+200])
    print('---')
