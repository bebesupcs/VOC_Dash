# -*- coding: utf-8 -*-
with open('dashboard/render.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [f"L{i+1}: {l.strip()}" for i, l in enumerate(text.splitlines()) if any(k in l for k in ['전화', '콜', 'MEET', 'meet', 'channel', 'inbound', 'INBOUND'])]
with open('render_matches.txt', 'w', encoding='utf-8') as out:
    out.write("\n".join(matches[:100]))
print(f"Total matches: {len(matches)}. Written to render_matches.txt")
