import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for w, chats in sorted(d.get('CHATS_BY_WEEK', {}).items()):
    chat_only = [c for c in chats if c.get('channel') == '채팅']
    if not chat_only:
        continue
    mgrs = {}
    for c in chat_only:
        a = c.get('agent') or 'None'
        mgrs[a] = mgrs.get(a, 0) + 1
    print(f'{w}: total_chat={len(chat_only)}, breakdown={mgrs}')
