# -*- coding: utf-8 -*-
import sqlite3
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
cur = conn.cursor()

# 1. View sql
cur.execute("SELECT sql FROM sqlite_master WHERE name='fact_voc'")
view_sql = cur.fetchone()[0]
print("=== fact_voc definition (first 300 chars) ===")
print(view_sql[:300])

# 2. Check W42 channels, medium_type, direction
df_w42 = pd.read_sql("""
    SELECT id, managedAt, week_start_date, week, channel_type, medium_type, direction,
           journey, tag_a, tag_b, tag_c, full_tag
    FROM fact_voc
    WHERE week IN ('W42', '2026-W42') OR week_start_date = '2026-10-15'
""", conn)
print(f"\nW42 total rows in fact_voc: {len(df_w42)}")
print("\nMedium type breakdown in W42:")
print(df_w42['medium_type'].value_counts(dropna=False))

print("\nChannel type breakdown in W42:")
print(df_w42['channel_type'].value_counts(dropna=False))

print("\nDirection by medium_type in W42:")
print(pd.crosstab(df_w42['medium_type'].fillna('NULL'), df_w42['direction'].fillna('NULL'), margins=True))

# 3. Check W41
df_w41 = pd.read_sql("""
    SELECT id, managedAt, week_start_date, week, channel_type, medium_type, direction,
           journey, tag_a, tag_b, tag_c, full_tag
    FROM fact_voc
    WHERE week IN ('W41', '2026-W41') OR week_start_date = '2026-10-08'
""", conn)
print(f"\nW41 total rows in fact_voc: {len(df_w41)}")
print("\nMedium type breakdown in W41:")
print(df_w41['medium_type'].value_counts(dropna=False))
print("\nDirection by medium_type in W41:")
print(pd.crosstab(df_w41['medium_type'].fillna('NULL'), df_w41['direction'].fillna('NULL'), margins=True))

# 4. Check journey values across DB
print("\nJourney distribution in W41:")
print(df_w41['journey'].value_counts(dropna=False))
print("\nJourney distribution in W42:")
print(df_w42['journey'].value_counts(dropna=False))

# 5. Check '사후관리' or '클레임' in journey
print("\nW41 rows where journey contains 사후관리 or 클레임:")
print(df_w41[df_w41['journey'].astype(str).str.contains('사후관리|클레임')][['id', 'journey', 'tag_a', 'tag_b', 'tag_c', 'full_tag']])

print("\nW42 rows where journey contains 사후관리 or 클레임:")
print(df_w42[df_w42['journey'].astype(str).str.contains('사후관리|클레임')][['id', 'journey', 'tag_a', 'tag_b', 'tag_c', 'full_tag']])
