import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

db_path = r"X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db"
con = sqlite3.connect(db_path)
cur = con.cursor()

official_18_ids = [
  '6ac60458602bbcf491bf', # 물티슈/포장공정/엔드터짐
  '6ac6f0d48ee827555b9c', # 물티슈/피부이상/발진
  '6ac72692cee5c5e7578a', # 물티슈/포장공정/찢김
  '6ac7359badf05fa7f039', # 물티슈/포장공정/박스테이프
  '6ac740932fa77cb81693', # 물티슈/포장공정/캡떨어짐
  '6ac75cbeafb194dab888', # 물티슈/용액/거품과다
  '6acc3704c063e596b16a', # 물티슈/포장공정/수량부족
  '6acc4351ed8f7f508aa1', # 물티슈/용액/질감이상
  '6acc479008cd6f3d1b9e', # 물티슈/피부이상/발진
  '6acc68e255ef7bf8f95f', # 물티슈/원단면/팝업불량
  '6acc798699a43a99954e', # 물티슈/피부이상/발진
  '6acc85ca1234c57c1f74', # 물티슈/이취/기름냄새
  '6acc9a8cb909417793ae', # 물티슈/원단(공정)이물/기타이물
  '6acd898046bd93c20c74', # 물티슈/원단면/보푸라기(가장자리)
  '6acd8a1e71c40253c0ba', # 물티슈/용액/거품과다
  '6acd8aea3853f0c54878', # 물티슈/포장공정/라벨불량
  '6acd94598bb51955a2a9', # 물티슈/원단(공정)이물/PET
  '6aced5550c9c2af7bdd2', # 물티슈/용액/수분과다
]

for cid in official_18_ids:
    cur.execute("SELECT id, tags, managedAt, report_date, journey, tag_a, tag_b, tag_c FROM userchat WHERE id = ?", (cid,))
    uc = cur.fetchone()
    cur.execute("SELECT id, date, month, week_of_month, week_start_date, journey, tag_a, tag_b, tag_c FROM fact_voc WHERE id = ?", (cid,))
    fv = cur.fetchone()
    print(f"\nID: {cid}")
    print(f"  userchat: {uc}")
    print(f"  fact_voc: {fv}")
