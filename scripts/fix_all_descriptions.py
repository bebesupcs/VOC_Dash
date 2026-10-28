# -*- coding: utf-8 -*-
"""
전체 상담 설명 정밀 파싱 및 DB 정합성 복구 스크립트
1. 테스트 데이터(홍길동) 영구 삭제
2. userchat.assigneeId .0 제거 및 정수형 매니저 ID 복원
3. 전체(3만여 건) 상담 description 정규식 파싱 -> userchat_description 업데이트
   - 제품명(product_name), 제조일자(manufacture_date), 구매처, 주문번호, 송장번호,
   - 고객문의사항(customer_issue), 조치결과(cs_action), 특이사항(special_note), 품질인계(quality_send_yn)
4. tag_master journey 동기화
"""
import sqlite3
import re
import sys
import time
import os
import json

sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()

db_path = r'C:\Users\hshwa\AppData\Local\Temp\channeltalk_voc_local.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. 홍길동 테스트 데이터 영구 삭제
cur.execute("DELETE FROM userchat WHERE id = '6ad70ade743f80ec369c' OR name = '홍길동' OR description LIKE '%테스트건 삭제예정%'")
print(f"1. Deleted test data (홍길동): {cur.rowcount} rows")
cur.execute("DELETE FROM userchat_description WHERE id = '6ad70ade743f80ec369c'")

# compensation_overrides.json 에서도 홍길동 id 정리
override_file = os.path.join(os.path.dirname(__file__), "..", "dashboard", "compensation_overrides.json")
if os.path.exists(override_file):
    try:
        with open(override_file, "r", encoding="utf-8") as f:
            overrides = json.load(f)
        if "6ad70ade743f80ec369c" in overrides.get("excluded_ids", []):
            overrides["excluded_ids"].remove("6ad70ade743f80ec369c")
        if "6ad70ade743f80ec369c" in overrides.get("excluded_reasons", {}):
            del overrides["excluded_reasons"]["6ad70ade743f80ec369c"]
        with open(override_file, "w", encoding="utf-8") as f:
            json.dump(overrides, f, ensure_ascii=False, indent=2)
        print("✓ Cleaned 홍길동 from compensation_overrides.json")
    except Exception as e:
        print("Notice on overrides clean:", e)

# 2. userchat.assigneeId .0 정리
cur.execute("UPDATE userchat SET assigneeId = REPLACE(assigneeId, '.0', '') WHERE assigneeId LIKE '%.0'")
print(f"2. Fixed assigneeId .0: {cur.rowcount} rows")

# 3. tag_master journey 동기화
cur.execute("""
    UPDATE userchat
    SET journey = (
        SELECT tm.journey 
        FROM tag_master tm 
        WHERE tm.full_tag = userchat.tags
    )
    WHERE tags IN (SELECT full_tag FROM tag_master)
      AND (journey IS NULL OR journey = '' OR journey != (SELECT tm.journey FROM tag_master tm WHERE tm.full_tag = userchat.tags))
""")
print(f"3. Updated journey from tag_master: {cur.rowcount} rows")

# 4. 전체 userchat descriptions 파싱
def robust_parse_description(desc):
    if not desc or not isinstance(desc, str):
        return {}
    patterns = {
        'product_name': r'[■□\*\-]?\s*(?:상품명|제품명)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:제조일자|구매처|출고처|주문번호|송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'manufacture_date': r'[■□\*\-]?\s*제조일자\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:구매처|출고처|주문번호|송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'order_info': r'[■□\*\-]?\s*(?:구매처/주문번호/출고처|구매처/주문번호|구매처)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:송장번호|문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'invoice_no': r'[■□\*\-]?\s*송장번호\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:문의내용|안내|조치|고객주소|특이사항|품질발송)|$)',
        'customer_issue': r'[■□\*\-]?\s*(?:문의내용|문의|상담내용|인입내용)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:안내|안내내용|조치|조치사항|고객주소|특이사항|품질발송)|$)',
        'cs_action': r'[■□◇\*\-]?\s*(?:안내내용|안내|조치내용|조치사항|조치|처리내용)\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:고객주소|특이사항|품질발송)|$)',
        'special_note': r'[■□\*\-]?\s*특이사항\s*[:：]\s*(.*?)(?=[■□◇\*\-]?\s*(?:품질발송)|$)',
    }
    res = {}
    for k, pat in patterns.items():
        m = re.search(pat, desc, re.DOTALL)
        if m:
            val = re.sub(r'[\r\n]+', ' ', m.group(1)).strip()
            res[k] = val
        else:
            res[k] = ''
    order_info = res.get('order_info', '')
    parts = [p.strip() for p in order_info.split('/')] if order_info else []
    res['mall_name'] = parts[0] if len(parts) >= 1 else ''
    res['order_no'] = parts[1] if len(parts) >= 2 else ''
    res['shipment_type'] = parts[2] if len(parts) >= 3 else ''
    
    sp = res.get('special_note', '').upper()
    if 'O' in sp or 'ㅇ' in sp or '인계' in sp or '품질' in sp:
        res['quality_send_yn'] = 'O'
    elif 'X' in sp or '없음' in sp:
        res['quality_send_yn'] = 'X'
    else:
        res['quality_send_yn'] = ''
    return res

cur.execute("SELECT id, description FROM userchat WHERE description IS NOT NULL AND description != ''")
all_rows = cur.fetchall()
print(f"4. Parsing {len(all_rows)} userchat descriptions...")

batch = []
for cid, desc in all_rows:
    p = robust_parse_description(desc)
    batch.append((
        cid, p['product_name'], p['manufacture_date'], p['mall_name'], p['order_no'],
        p['shipment_type'], p['invoice_no'], p['customer_issue'], p['cs_action'],
        p['special_note'], p['quality_send_yn']
    ))

cur.executemany("""
    INSERT INTO userchat_description (
        id, product_name, manufacture_date, mall_name, order_no, shipment_type,
        invoice_no, customer_issue, cs_action, special_note, quality_send_yn
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        product_name = excluded.product_name,
        manufacture_date = excluded.manufacture_date,
        mall_name = excluded.mall_name,
        order_no = excluded.order_no,
        shipment_type = excluded.shipment_type,
        invoice_no = excluded.invoice_no,
        customer_issue = excluded.customer_issue,
        cs_action = excluded.cs_action,
        special_note = excluded.special_note,
        quality_send_yn = excluded.quality_send_yn
""", batch)

conn.commit()
print(f"4. Completed parsing & inserting {len(batch)} descriptions in {time.time()-t0:.2f}s")

# 5. fact_voc View 갱신 (REPLACE .0 매핑 및 special_note, quality_send_yn 명시 포함)
cur.execute("DROP VIEW IF EXISTS fact_voc")
cur.execute("""
CREATE VIEW fact_voc AS
    WITH base AS (
        SELECT
            uc.*,
            COALESCE(uc.report_date, DATE(uc.managedAt)) AS __basis_date
        FROM userchat uc
    ),
    period_week AS (
        SELECT
            base.*,
            DATE(
                __basis_date,
                '-' || ((CAST(STRFTIME('%w', __basis_date) AS INTEGER) + 3) % 7) || ' days'
            ) AS __week_start_date
        FROM base
    ),
    periods AS (
        SELECT
            period_week.*,
            DATE(__week_start_date, '+6 days') AS __week_end_date,
            DATE(__week_start_date, '+4 days') AS __week_anchor_date
        FROM period_week
    )
    SELECT
        p.id,
        p.__basis_date AS date,
        p.__basis_date AS report_date,
        p.business_date,
        p.is_after_hours,
        p.is_weekend,
        p.operation_status,
        p.managedAt,
        p.name,
        p.description,
        p.tags,
        p.direction,
        p.assigneeId,
        p.mediumName,
        p.mediumType,
        p.mediumSenderName,
        p.alfTriggered,
        p.ai_status,
        p.closedAt,
        p.managedAt AS managed_at,
        p.name AS customer_name,
        p.tags AS full_tag,
        p.assigneeId AS assignee_id,
        mgr.name AS manager_name,
        p.mediumName AS medium_name,
        p.mediumType AS medium_type,
        p.mediumSenderName AS medium_sender_name,
        p.alfTriggered AS alf_triggered,
        p.closedAt AS closed_at,
        CASE
            WHEN TRIM(COALESCE(p.journey, '')) IN ('구매/배송', '사후관리/클레임', '제품사용')
                THEN '클레임'
            ELSE '단순문의'
        END AS voc_type,
        COALESCE(
            oco.channel_type,
            CASE
                WHEN LOWER(TRIM(COALESCE(p.mediumName, ''))) = 'phonenumber'
                    THEN '전화'
                ELSE '채팅'
            END
        ) AS channel_type,
        p.journey,
        p.tag_a,
        p.tag_b,
        p.tag_c,
        p.profile_csat,
        p.is_ai_inflow,
        p.is_ai_completed,
        p.is_ai_transferred,
        p.is_non_phone_inbound,
        p.is_ai_handled,
        p.is_agent_handled,
        p.handle_type,
        CAST(STRFTIME('%Y', p.__week_anchor_date) AS INTEGER) AS year,
        STRFTIME('%Y-%m', p.__week_anchor_date) AS month,
        CAST(STRFTIME('%V', p.__week_start_date) AS INTEGER) AS week_num,
        'W' || STRFTIME('%V', p.__week_start_date) AS week,
        PRINTF(
            '%d월 %d주',
            CAST(STRFTIME('%m', p.__week_anchor_date) AS INTEGER),
            CAST((CAST(STRFTIME('%d', p.__week_anchor_date) AS INTEGER) - 1) / 7 AS INTEGER) + 1
        ) AS week_of_month,
        p.__week_start_date AS week_start_date,
        p.__week_end_date AS week_end_date,
        'Q' || (
            CAST((CAST(STRFTIME('%m', p.__week_anchor_date) AS INTEGER) - 1) / 3 AS INTEGER) + 1
        ) AS quarter,
        p.__schema_year,
        ud.product_name,
        ud.manufacture_date,
        ud.mall_name,
        ud.order_no,
        ud.shipment_type,
        ud.invoice_no,
        ud.customer_issue,
        ud.cs_action,
        ud.special_note,
        ud.quality_send_yn
    FROM periods p
    LEFT JOIN userchat_description ud
        ON p.id = ud.id
    LEFT JOIN manager mgr
        ON REPLACE(CAST(p.assigneeId AS TEXT), '.0', '') = CAST(mgr.id AS TEXT)
    LEFT JOIN official_channel_override oco
        ON p.id = oco.id
""")
conn.commit()
print("5. Successfully updated fact_voc view definition!")

# 검증
for target_name in ['김지훈', '김정도']:
    r = cur.execute(f"""
        SELECT f.id, f.customer_name, f.product_name, f.manufacture_date, f.customer_issue, f.cs_action, f.special_note, f.quality_send_yn, f.manager_name
        FROM fact_voc f
        WHERE f.customer_name LIKE '%{target_name}%'
        LIMIT 1
    """).fetchone()
    if r:
        print(f"✓ Verification [{target_name}]: ID={r[0]}, prod={r[2]}, mfg={r[3]}, note={r[6]}, q_send={r[7]}, mgr={r[8]}")

conn.close()
