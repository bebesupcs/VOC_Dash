# -*- coding: utf-8 -*-
import sys
import sqlite3

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
conn = sqlite3.connect(db_path, timeout=30)
c = conn.cursor()

# 전체합계 제거
r = c.execute("DELETE FROM board_daily_counts WHERE mall_name IN ('전체합계', '합계') OR mall_name LIKE '%합계%'").rowcount
conn.commit()
print(f"✓ 전체합계 중복 행 삭제 완료: {r}건")

# 남은 행 수 확인
c.execute("SELECT count(*) FROM board_daily_counts")
print(f"✓ 정제 후 순수 쇼핑몰 게시판 데이터: {c.fetchone()[0]}건")
conn.close()
