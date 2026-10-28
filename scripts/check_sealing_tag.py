# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT * FROM tag_master WHERE full_tag LIKE '%실링%' OR tag_c LIKE '%실링%'")
rows = c.fetchall()
print('tag_master matches for 실링:')
cols = [d[0] for d in c.description]
for r in rows:
    print(dict(zip(cols, r)))

conn.close()

# Also check google_tag_master_cache.csv
import csv
with open('dashboard/google_tag_master_cache.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    print('\nGoogle Tag Master Cache matches:')
    for row in reader:
        if any('실링' in cell for cell in row):
            print(row)
