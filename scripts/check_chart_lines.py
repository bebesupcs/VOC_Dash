# -*- coding: utf-8 -*-
with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

charts = [
    "trendChart", "boardWeeklyTrendChart", "boardMallComparisonChart",
    "callDirChart", "reportChannelChart", "qualityTypeTrendChart",
    "deliveryTypeTrendChart", "deliveryTypeChart", "deliveryTrendChart",
    "serviceTypeTrendChart", "serviceTrendChart", "channelMixChart",
    "channelHourChart", "ctiMissedChart", "ctiAgentChart", "alfTagChart"
]

for ch in charts:
    for i, line in enumerate(lines):
        if f'charts["{ch}"]' in line:
            print(f"{ch:26s} : Line {i+1}")
            break
