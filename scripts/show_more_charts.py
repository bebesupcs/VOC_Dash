# -*- coding: utf-8 -*-
with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

def show_chart(name):
    m = re.search(rf'charts\[["\']{name}["\']\]\s*=\s*new Chart\(', text)
    if m:
        start = m.start()
        end = text.find('});', start)
        print(f"=== {name} ===")
        print(text[start:end+3])

show_chart("boardWeeklyTrendChart")
show_chart("boardMallComparisonChart")
show_chart("deliveryTypeChart")
show_chart("ctiAgentChart")
show_chart("alfTagChart")
