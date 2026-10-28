# -*- coding: utf-8 -*-
import re

with open(r'D:\dev\VOC리포트\dashboard\render.js', 'r', encoding='utf-8') as f:
    text = f.read()

charts_info = [
    "trendChart", "boardWeeklyTrendChart", "boardMallComparisonChart",
    "callDirChart", "reportChannelChart", "qualityTypeTrendChart",
    "deliveryTypeTrendChart", "deliveryTypeChart", "deliveryTrendChart",
    "serviceTypeTrendChart", "serviceTrendChart", "channelMixChart",
    "channelHourChart", "ctiAnswerRateTrendChart", "ctiMissedChart",
    "ctiAgentChart", "alfTagChart"
]

for ch in charts_info:
    pattern = rf'charts\[["\']?{ch}["\']?\]\s*=\s*new Chart\([^,]+,\s*\{{\s*type:\s*["\']([^"\']+)["\']'
    m = re.search(pattern, text)
    ch_type = m.group(1) if m else "unknown"
    print(f"{ch:28s} : {ch_type}")
