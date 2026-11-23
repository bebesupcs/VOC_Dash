# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

ids = [
    '6ad960ddcc38aa812c02',
    '6ad96eb99f8f5c8602d8',
    '6adab675bb17cb5c2f5e',
    '6adab6c0c5801f58adcf',
    '6adac3e96866aa0d3f46',
    '6adac63bad715eebbd90',
    '6adae4ffcfd53fa4f4c0',
    '6adafd98409070fe85e7',
    '6adea98bb3ef87387978',
    '6adeab620319cce2a025',
    '6adeb733334ff561d354',
    '6adedafe2c35d72ad841',
    '6adf046d1accfdb6e3db',
    '6ae01189004f95939596',
    '6ae019106d552ede2c55',
    '6ae037a55192063d56a4',
    '6ae057d6b9f1a4bcd63b',
    '6ae194fb65d6b3a828b2'
]

d = json.load(open('dashboard/data.json', encoding='utf-8'))
found = {}
for wk, calls in d.get('CTI_BY_WEEK', {}).items():
    for c in calls:
        if c.get('id') in ids:
            found[c.get('id')] = (wk, c)

print(f"Total searched: {len(ids)}, Found in CTI_BY_WEEK: {len(found)}")
for cid in ids:
    if cid in found:
        wk, c = found[cid]
        print(f"ID: {cid} | 주차: {wk} | 일시: {c.get('time')} | 방향: {c.get('dir')} | 응답: {c.get('ans')} | 사유: {repr(c.get('reason'))} | 태그: {repr(c.get('tag'))} | 대기: {c.get('wait')}s | 통화: {c.get('talk')}s | 운영시간내: {c.get('is_in_hours')} | 문의: {repr(c.get('issue'))} | 조치: {repr(c.get('act'))}")
    else:
        print(f"ID: {cid} | NOT FOUND in data.json")
