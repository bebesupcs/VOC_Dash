import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT DISTINCT week_start_date FROM fact_voc WHERE year=2026 ORDER BY week_start_date DESC LIMIT 5")
print('Recent weeks in fact_voc:', c.fetchall())

# Check manager_name in 2026-10-15 (W42)
c.execute("SELECT manager_name, count(1) FROM fact_voc WHERE week_start_date='2026-10-15' GROUP BY manager_name")
print('2026-10-15 manager_names:', c.fetchall())

# Check manager_name in 2026-10-08 (W41)
c.execute("SELECT manager_name, count(1) FROM fact_voc WHERE week_start_date='2026-10-08' GROUP BY manager_name")
print('2026-10-08 manager_names:', c.fetchall())

conn.close()
