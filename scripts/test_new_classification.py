# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')

print("==================================================")
print("10월 3주차 (2026-W42, week_start_date='2026-10-15') 전수 검증")
print("==================================================")

df_w42 = pd.read_sql("""
    SELECT 
        u.id, u.managedAt, u.mediumName, u.direction, u.tags,
        COALESCE(tm.journey, u.journey) as journey,
        COALESCE(tm.tag_a, u.tag_a) as tag_a,
        COALESCE(tm.tag_b, u.tag_b) as tag_b,
        COALESCE(tm.tag_c, u.tag_c) as tag_c
    FROM userchat u
    LEFT JOIN tag_master tm ON u.tags = tm.full_tag
    WHERE u.week_start_date = '2026-10-15'
""", conn)

print(f"Total rows: {len(df_w42)}")

# 채널 분류
df_w42['channel_calc'] = df_w42['mediumName'].apply(
    lambda x: '전화' if str(x).strip().lower() == 'phonenumber' else '채팅'
)

print("\n--- 채널별 건수 (전화 vs 채팅) ---")
print(df_w42['channel_calc'].value_counts())

print("\n--- 채널 & 방향(In/Out)별 건수 ---")
print(pd.crosstab(df_w42['channel_calc'], df_w42['direction'], margins=True))

print("\n--- 여정(Journey)별 분포 ---")
print(df_w42['journey'].value_counts(dropna=False))

# 품질 클레임 (journey == '제품사용')
df_quality = df_w42[df_w42['journey'] == '제품사용']
print(f"\n--- 품질 클레임 (journey == '제품사용'): {len(df_quality)}건 ---")
print(df_quality['tags'].value_counts())

# 서비스 클레임 (journey == '사후관리/클레임')
df_service = df_w42[df_w42['journey'] == '사후관리/클레임']
print(f"\n--- 서비스 클레임 (journey == '사후관리/클레임'): {len(df_service)}건 ---")
for idx, r in df_service.iterrows():
    print(f"  ID={r['id']} | Date={r['managedAt']} | Channel={r['channel_calc']}({r['direction']}) | Tag={r['tags']}")

print("\n==================================================")
print("10월 2주차 (2026-W41, 2026-10-08 ~ 2026-10-15 17:00) 전수 검증")
print("==================================================")

df_w41 = pd.read_sql("""
    SELECT 
        u.id, u.managedAt, u.mediumName, u.direction, u.tags,
        COALESCE(tm.journey, u.journey) as journey,
        COALESCE(tm.tag_a, u.tag_a) as tag_a,
        COALESCE(tm.tag_b, u.tag_b) as tag_b,
        COALESCE(tm.tag_c, u.tag_c) as tag_c,
        u.__source_file
    FROM userchat u
    LEFT JOIN tag_master tm ON u.tags = tm.full_tag
    WHERE u.managedAt >= '2026-10-08 00:00:00' AND u.managedAt < '2026-10-15 17:00:00'
""", conn)

print(f"Total rows in 10W2: {len(df_w41)}")

df_w41['channel_calc'] = df_w41['mediumName'].apply(
    lambda x: '전화' if str(x).strip().lower() == 'phonenumber' else '채팅'
)
print("\n--- 10W2 채널별 건수 ---")
print(pd.crosstab(df_w41['channel_calc'], df_w41['direction'], margins=True))

print("\n--- 10W2 여정(Journey)별 분포 ---")
print(df_w41['journey'].value_counts(dropna=False))

# 품질 클레임 (journey == '제품사용')
df_w41_quality = df_w41[df_w41['journey'] == '제품사용']
print(f"\n--- 10W2 품질 클레임 (journey == '제품사용'): {len(df_w41_quality)}건 ---")
print(df_w41_quality['tag_a'].value_counts())

# 서비스 클레임 (journey == '사후관리/클레임')
df_w41_service = df_w41[df_w41['journey'] == '사후관리/클레임']
print(f"\n--- 10W2 서비스 클레임 (journey == '사후관리/클레임'): {len(df_w41_service)}건 ---")
for idx, r in df_w41_service.iterrows():
    print(f"  ID={r['id']} | Date={r['managedAt']} | Channel={r['channel_calc']}({r['direction']}) | Tag={r['tags']}")
