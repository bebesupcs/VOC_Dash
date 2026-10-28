# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

ids = ['6a8a8906594dae54a1ca', '6aaa3bdd69de25e15bd2']

for cid in ids:
    c.execute('SELECT * FROM fact_voc WHERE id = ?', (cid,))
    row = c.fetchone()
    cols = [d[0] for d in c.description]
    d = dict(zip(cols, row))
    print(f"=== ID: {cid} ===")
    print(f"  일자(date): {d.get('date')}")
    print(f"  접수시각(managedAt): {d.get('managedAt')}")
    print(f"  월(month): {d.get('month')}, 주차(week): {d.get('week')}")
    print(f"  고객명: {d.get('customer_name')}")
    print(f"  상담사: {d.get('manager_name')}")
    print(f"  태그: {d.get('tags')} (tag_a={d.get('tag_a')}, tag_b={d.get('tag_b')}, tag_c={d.get('tag_c')})")
    print(f"  고객여정(journey): {d.get('journey')}")
    print(f"  VOC유형: {d.get('voc_type')}")
    print(f"  채널: {d.get('channel_type')}, 방향: {d.get('direction')}")
    print(f"  제품명: {d.get('product_name')}")
    print(f"  문의내용: {d.get('customer_issue')}")
    print(f"  조치내용: {d.get('cs_action')}")
    print(f"  품질발송여부: {d.get('quality_send_yn')}")
    print()

conn.close()
