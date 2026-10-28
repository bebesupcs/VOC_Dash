import sqlite3, os

p = os.path.join(os.environ['TEMP'], 'channeltalk_voc_local.db')
conn = sqlite3.connect(p)
c = conn.cursor()
c.execute("""
    SELECT week_start_date, SUM(board_count) as total_board
    FROM board_daily_counts
    WHERE year IN (2025, 2026, '2025', '2026')
      AND mall_name NOT IN ('전체합계', '합계')
      AND mall_name NOT LIKE '%합계%'
      AND week_start_date >= '2026-09-24'
    GROUP BY week_start_date
    ORDER BY week_start_date ASC
""")
rows = c.fetchall()
print("Fixed board counts by week:")
for r in rows:
    print(f"  {r[0]}: {r[1]}건")
