import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db')
c = conn.cursor()

c.execute("SELECT id, name FROM manager")
managers = c.fetchall()
mgr_map = {m[0]: m[1] for m in managers}
print('Sample Managers in DB:', list(mgr_map.items())[:10])

# Check userchat in week '2026-W42'
c.execute("""
    SELECT u.id, u.managedAt, u.assigneeId, m.name as managerName, u.mediumType, u.mediumName, u.direction
    FROM userchat u
    LEFT JOIN manager m ON u.assigneeId = m.id
    WHERE u.week = '2026-W42'
""")
rows = c.fetchall()
print(f'Total 2026-W42 userchats in DB: {len(rows)}')
mgr_counts = {}
for r in rows:
    name = r[3] or '미배정'
    mgr_counts[name] = mgr_counts.get(name, 0) + 1
print('2026-W42 Manager Breakdown in DB:', mgr_counts)

# Also check week 2026-W41
c.execute("""
    SELECT m.name, count(*)
    FROM userchat u
    LEFT JOIN manager m ON u.assigneeId = m.id
    WHERE u.week = '2026-W41'
    GROUP BY m.name
""")
print('\n2026-W41 Manager Breakdown in DB:', c.fetchall())

conn.close()
