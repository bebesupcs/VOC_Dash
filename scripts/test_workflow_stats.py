# -*- coding: utf-8 -*-
from sync_channeltalk_api import ChannelTalkClient, load_config

config = load_config()
client = ChannelTalkClient(config.get("access_key"), config.get("access_secret"))

res = client.get_user_chats_page(state="closed", limit=50)
chats = res.get("userChats", [])

workflow_cnt = 0
no_reply_cnt = 0
agent_replied_cnt = 0

for c in chats:
    source = c.get("source") or {}
    has_wf = bool(source.get("workflow"))
    reply_count = c.get("replyCount", 0)
    has_reply = bool(c.get("firstRepliedAt")) or (reply_count and reply_count > 0)
    
    if has_wf:
        workflow_cnt += 1
        if not has_reply:
            no_reply_cnt += 1
        else:
            agent_replied_cnt += 1

print(f"Total 50 chats analyzed:")
print(f"- Workflow (ALF) chats: {workflow_cnt}건")
print(f"  - No agent reply (순수 봇 완결): {no_reply_cnt}건")
print(f"  - Agent replied (상담원 이관): {agent_replied_cnt}건")
