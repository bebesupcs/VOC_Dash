import requests
import json
import time

headers = {
    'x-access-key': '690074f7a3671d0b22f5',
    'x-access-secret': 'f5926f6f2a7ca93b49709126c078a0eb',
    'accept': 'application/json'
}

cutoff_ts = int(time.mktime(time.strptime("2026-09-01 00:00:00", "%Y-%m-%d %H:%M:%S"))) * 1000
cursor = None
total = 0
page = 1

while True:
    params = {'state': 'closed', 'limit': 200, 'sortOrder': 'desc'}
    if cursor:
        params['since'] = cursor
    r = requests.get('https://api.channel.io/open/v5/user-chats', headers=headers, params=params)
    data = r.json()
    chats = data.get('userChats', [])
    if not chats:
        print("No more chats.")
        break
    
    total += len(chats)
    oldest_closed = min(c.get('closedAt') or c.get('updatedAt') or 0 for c in chats)
    oldest_closed_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(oldest_closed/1000)) if oldest_closed else 'None'
    print(f"Page {page}: {len(chats)} chats | Cumulative: {total} | Oldest closed in page: {oldest_closed_str}")
    
    if oldest_closed < cutoff_ts:
        print("Reached cutoff date!")
        break
        
    cursor = data.get('next')
    if not cursor:
        print("End of pages.")
        break
    page += 1
    if page > 40:
        print("Reached page 40 safety limit.")
        break

print(f"Done! Found {total} closed chats since 2026-09-01.")
