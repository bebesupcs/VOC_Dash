# -*- coding: utf-8 -*-
import sqlite3
import json
import os
import tempfile

db_path = os.path.join(tempfile.gettempdir(), 'channeltalk_voc_local.db')
print('Resolved db_path:', os.path.exists(db_path), repr(db_path))
con = sqlite3.connect(db_path)
cur = con.cursor()

# The 27 items from existing Excel:
existing_items = [
    ("김지훈", "2026-10-15", "물티슈", "원단면", "보푸라기(원단면)"),
    ("김동욱", "2026-10-15", "물티슈", "원단면", "보푸라기(원단면)"),
    ("김동욱", "2026-10-15", "물티슈", "원단면", "보푸라기(가장자리)"),
    ("이혜림", "2026-10-15", "물티슈", "원단(공정)이물", "기타이물"),
    ("김지훈", "2026-10-15", "물티슈", "원단면", "보푸라기(가장자리)"),
    ("김정도", "2026-10-15", "클레임(공통)", "휴먼에러", "세팅오류"),
    ("이은영", "2026-10-16", "물티슈", "용액", "수분부족"),
    ("이혜림", "2026-10-16", "물티슈", "원단면", "부정형절단"),
    ("곽아름", "2026-10-16", "물티슈", "이취", "화학-약품냄새"),
    ("안주희", "2026-10-19", "물티슈", "포장공정", "접지물림"),
    ("소비자", "2026-10-19", "물티슈", "용액", "거품과다"),
    ("이동희", "2026-10-19", "물티슈", "포장공정", "찢김"),
    ("정소영", "2026-10-19", "물티슈", "원단(공정)이물", "원사찌꺼기"),
    ("김은주", "2026-10-19", "물티슈", "포장공정", "찢김"),
    ("이소현", "2026-10-19", "클레임(공통)", "휴먼에러", "세팅오류"),
    ("정은주", "2026-10-20", "물티슈", "원단면", "원사뭉침"),
    ("오서윤", "2026-10-20", "물티슈", "원단(공정)이물", "탄화물이물"),
    ("김상균", "2026-10-20", "물티슈", "포장공정", "캡불량"),
    ("오정아", "2026-10-20", "물티슈", "이취", "화학-약품냄새"),
    ("최윤영", "2026-10-20", "물티슈", "포장공정", "캡탈락"),
    ("노아",   "2026-10-20", "물티슈", "원단면", "보푸라기(가장자리)"),
    ("김민경", "2026-10-20", "물티슈", "원단면", "보푸라기(원단면)"),
    ("전광석", "2026-10-20", "물티슈", "포장(외관)", "인쇄불량"),
    ("노아",   "2026-10-21", "물티슈", "원단면", "보푸라기(가장자리)"),
    ("김선희", "2026-10-21", "물티슈", "포장공정", "스티커누락"),
    ("김한나", "2026-10-21", "물티슈", "포장공정", "누액(터짐)"),
    ("김소영", "2026-10-21", "물티슈", "포장공정", "캡파손")
]

# The 16 items extracted by report raw:
extracted_16 = [
    ("김지훈", "2026-10-15", "물티슈", "원단면", "보푸라기(원단면)"),
    ("김동욱", "2026-10-15", "물티슈", "원단면", "보푸라기(원단면)"),
    ("김동욱", "2026-10-15", "물티슈", "원단면", "보푸라기(가장자리)"),
    ("김지훈", "2026-10-15", "물티슈", "원단면", "보푸라기(가장자리)"),
    ("이혜림", "2026-10-16", "물티슈", "원단면", "부정형절단"),
    ("곽아름", "2026-10-16", "물티슈", "이취", "화학-약품냄새"),
    ("안주희", "2026-10-19", "물티슈", "포장공정", "접지물림"),
    ("소비자", "2026-10-19", "물티슈", "용액", "거품과다"),
    ("이동희", "2026-10-19", "물티슈", "포장공정", "찢김"),
    ("김은주", "2026-10-19", "물티슈", "포장공정", "찢김"),
    ("오서윤", "2026-10-20", "물티슈", "원단(공정)이물", "탄화물이물"),
    ("김상균", "2026-10-20", "물티슈", "포장공정", "캡불량"),
    ("오정아", "2026-10-20", "물티슈", "이취", "화학-약품냄새"),
    ("김민경", "2026-10-20", "물티슈", "원단면", "보푸라기(원단면)"),
    ("노아",   "2026-10-21", "물티슈", "원단면", "보푸라기(가장자리)"),
    ("김소영", "2026-10-21", "물티슈", "포장공정", "캡파손")
]

print(f"Total Existing: {len(existing_items)}, Total Extracted: {len(extracted_16)}")

# Find missing items
ex_copy = list(extracted_16)
missing = []
for item in existing_items:
    if item in ex_copy:
        ex_copy.remove(item)
    else:
        missing.append(item)

print(f"Missing count: {len(missing)}")
for m in missing:
    print("MISSING:", m)
    # Search in DB
    name, dt, cat, mid, sub = m
    cur.execute("""
        SELECT u.id, u.managedAt, u.name, u.tag_a, u.tag_b, u.tag_c, u.journey, d.customer_issue, d.quality_send_yn
        FROM userchat u
        LEFT JOIN userchat_description d ON u.id = d.id
        WHERE u.name = ? AND date(u.managedAt) = ?
    """, (name, dt))
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  DB found: id={r[0]}, tags=({r[3]}, {r[4]}, {r[5]}), journey={r[6]}, issue={(r[7] or '')[:30]}")
    else:
        print(f"  DB NOT found for name={name}, date={dt}. Searching name only:")
        cur.execute("""
            SELECT u.id, u.managedAt, u.name, u.tag_a, u.tag_b, u.tag_c, u.journey, d.customer_issue
            FROM userchat u
            LEFT JOIN userchat_description d ON u.id = d.id
            WHERE u.name = ?
            ORDER BY u.managedAt DESC LIMIT 3
        """, (name,))
        for r in cur.fetchall():
            print(f"    found on {r[1]}: tags=({r[3]}, {r[4]}, {r[5]}), journey={r[6]}, issue={(r[7] or '')[:30]}")
