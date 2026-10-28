# -*- coding: utf-8 -*-
import json
from collections import Counter

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

cur_w = data['WEEKS'][-1]
print('Latest week in WEEKS:', cur_w)

for w in data['WEEKS'][-5:]:
    w_key = w['key']
    chats = data.get('CHATS_BY_WEEK', {}).get(w_key, [])
    ch_counter = Counter(c.get('channel') for c in chats)
    dir_counter = Counter(f"{c.get('channel')}_{c.get('direction')}" for c in chats)
    print(f"\nWeek {w_key} ({w.get('label')}) - Total: {len(chats)}")
    print("  Channel:", dict(ch_counter))
    print("  Dir:", dict(dir_counter))

    # Also check other structures like SUMMARY, CHANNELS, etc.
    if 'OFFICIAL_WEEKLY_CHANNEL_COUNTS' in data:
        print("  OFFICIAL:", data['OFFICIAL_WEEKLY_CHANNEL_COUNTS'].get(w_key))
