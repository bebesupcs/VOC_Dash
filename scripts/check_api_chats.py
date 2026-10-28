# -*- coding: utf-8 -*-
import json
from sync_channeltalk_api import ChannelTalkClient, load_config

config = load_config()
ak = config.get("access_key")
sk = config.get("access_secret")

if not ak or not sk:
    print("API keys not set")
    exit(0)

client = ChannelTalkClient(ak, sk)
res = client.get_user_chats_page(state="closed", limit=5)
chats = res.get("userChats", [])
print(f"Fetched {len(chats)} user-chats")
for c in chats[:2]:
    print("ID:", c.get("id"))
    print("keys:", list(c.keys()))
    print("state:", c.get("state"))
    print("handling:", c.get("handling"))
    print("tags:", c.get("tags"))
    print("assigneeId:", c.get("assigneeId"))
    print("source:", c.get("source"))
    print("supportBot:", (c.get("source") or {}).get("supportBot"))
    print("=" * 40)
