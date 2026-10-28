import requests
import json
import time

headers = {
    'x-access-key': '690074f7a3671d0b22f5',
    'x-access-secret': 'f5926f6f2a7ca93b49709126c078a0eb',
    'accept': 'application/json'
}

print("--- Querying page 1 closed ---")
r = requests.get('https://api.channel.io/open/v5/user-chats?state=closed&limit=20', headers=headers)
data = r.json()
chats = data.get('userChats', [])
print(f"Total chats in page 1: {len(chats)}")
for i, c in enumerate(chats[:10]):
    c_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(c.get('createdAt', 0)/1000)) if c.get('createdAt') else 'None'
    u_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(c.get('updatedAt', 0)/1000)) if c.get('updatedAt') else 'None'
    m_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(c.get('managedAt', 0)/1000)) if c.get('managedAt') else 'None'
    cl_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(c.get('closedAt', 0)/1000)) if c.get('closedAt') else 'None'
    print(f"[{i}] ID: {c.get('id')} | createdAt: {c_at} | updatedAt: {u_at} | managedAt: {m_at} | closedAt: {cl_at}")

print("Next cursor:", data.get('next'))
