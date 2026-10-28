# -*- coding: utf-8 -*-
import json
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print("==================================================")
print("1. 10월 3주차 (2026-W42) 검증 결과")
print("==================================================")
w42_chats = d['CHATS_BY_WEEK'].get('2026-W42', [])
df_w42 = pd.DataFrame(w42_chats)
print(f"Total chats in W42: {len(df_w42)}")
print("\n[채널별 분포]")
print(df_w42['channel'].value_counts())

print("\n[채널 & 방향 분포]")
print(pd.crosstab(df_w42['channel'], df_w42['direction'], margins=True))

print("\n[Nature & Brand 분포]")
print(pd.crosstab(df_w42['nature'].fillna('None'), df_w42['brand'].fillna('None'), margins=True))

print("\n[서비스 클레임 상세 내역]")
w42_service = df_w42[(df_w42['nature'] == '클레임') & (df_w42['brand'] == '서비스')]
print(f"Total W42 service claims: {len(w42_service)}")
for idx, r in w42_service.iterrows():
    print(f"  ID={r['id']} | Channel={r['channel']}({r['direction']}) | Journey={r['journey']} | Tag={r['tag']}")

print("\n[품질 클레임 요약]")
w42_quality = df_w42[(df_w42['nature'] == '클레임') & (df_w42['brand'] != '서비스') & (df_w42['channel'] != '배송접수')]
print(f"Total W42 quality claims: {len(w42_quality)}")
print(w42_quality['tag'].value_counts())

print("\n==================================================")
print("2. 10월 2주차 (2026-W41) 검증 결과")
print("==================================================")
w41_chats = d['CHATS_BY_WEEK'].get('2026-W41', [])
df_w41 = pd.DataFrame(w41_chats)
print(f"Total chats in W41: {len(df_w41)}")
print("\n[채널 & 방향 분포]")
print(pd.crosstab(df_w41['channel'], df_w41['direction'], margins=True))

print("\n[서비스 클레임 상세 내역 (journey == '사후관리/클레임')]")
w41_service = df_w41[(df_w41['nature'] == '클레임') & (df_w41['brand'] == '서비스')]
print(f"Total W41 service claims: {len(w41_service)}")
for idx, r in w41_service.iterrows():
    print(f"  ID={r['id']} | Channel={r['channel']}({r['direction']}) | Journey={r['journey']} | Tag={r['tag']}")

print("\n[RAW_SUMMARY 10월 2주 vs 10월 3주]")
print("W41 Raw Summary:", d['RAW_SUMMARY'].get('2026-W41'))
print("W42 Raw Summary:", d['RAW_SUMMARY'].get('2026-W42'))
