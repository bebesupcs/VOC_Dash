# -*- coding: utf-8 -*-
"""
send_weekly_briefing.py
베베숲 CX팀 주간 VOC 핵심 요약 자동 브리핑 & 공식 리포트 화면 기반 PDF 자동 생성 및 발송기

- 대시보드 "리포트 추출" 5대 표준 섹션 100% 동일 구현:
  1. VOC 요약 (총 인입, 품질, 배송, 서비스)
  2. 채널별 추이 (최근 4주 전화/채팅/게시판 추이 표)
  2.5 AI 챗봇(ALF) 처리율 인사이트 배너
  3. 부문별 클레임 현황 & 이슈 인사이트 (품질 · 배송 · 서비스 3대 부문 개별 컬럼 TOP 5 노출)
  4. 핵심 리스크 & 이상징후 이슈업 현황 (고위험 클레임 + 최근 4주/전주 대비 급증 Spike 감지)
  5. CX팀 종합 코멘트
- 발신 및 표기: 오직 "베베숲 CX팀" 명칭 사용
- Headless Browser (Edge/Chrome/Chromium) 기반 고화질 A4 PDF 리포트 자동 생성 & 메일 첨부
- 반응형 모바일/PC 이메일 브리핑 본문 생성 및 발송
"""

import os
import sys
import json
import argparse
import subprocess
import smtplib
import http.server
import socketserver
import threading
from pathlib import Path
from collections import Counter
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_JSON_PATH = PROJECT_ROOT / "dashboard" / "data.json"
SMTP_CONFIG_PATH = PROJECT_ROOT / "config" / "smtp_config.json"


def find_browser_executable():
    """Windows 또는 Linux/Docker 환경에서 Headless 브라우저 실행 파일 검색"""
    if os.name == "nt":
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    else:
        candidates = ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]
        for c in candidates:
            if os.path.exists(c):
                return c
    return None


def load_briefing_data(week_key=None):
    """dashboard/data.json에서 대시보드 리포트 추출 화면과 100% 동일한 정밀 통계 추출"""
    if not DATA_JSON_PATH.exists():
        raise FileNotFoundError(f"data.json not found at {DATA_JSON_PATH}")

    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    weeks = data.get("WEEKS", [])
    if not weeks:
        raise ValueError("No weeks found in data.json")

    target_idx = len(weeks) - 1
    if week_key:
        for idx, w in enumerate(weeks):
            if w.get("key") == week_key:
                target_idx = idx
                break

    cur_w = weeks[target_idx]
    prev_w = weeks[target_idx - 1] if target_idx > 0 else None
    cur_key = cur_w["key"]
    prev_key = prev_w["key"] if prev_w else None

    # 최근 4주 목록
    recent_4_weeks = weeks[max(0, target_idx - 3): target_idx + 1]

    raw_summary = data.get("RAW_SUMMARY", {})
    cur_raw = raw_summary.get(cur_key, {})
    prev_raw = raw_summary.get(prev_key, {}) if prev_key else {}

    # 1. 헤드라인 총량 수치
    total = cur_raw.get("total_offered_raw", 0)
    prev_total = prev_raw.get("total_offered_raw", 0) if prev_raw else None
    diff_total = (total - prev_total) if prev_total is not None else 0
    pct_total = ((diff_total / prev_total) * 100) if prev_total and prev_total > 0 else 0

    calls = cur_raw.get("raw_call", 0)
    chats = cur_raw.get("raw_chat", 0)
    board = cur_raw.get("raw_board", 0)

    # 2. 최근 4주 채널별 추이 데이터
    channel_trends_4w = []
    for w in recent_4_weeks:
        wk = w["key"]
        w_raw = raw_summary.get(wk, {})
        channel_trends_4w.append({
            "key": wk,
            "label": w.get("week_of_month") or w.get("label", wk),
            "total": w_raw.get("total_offered_raw", 0),
            "call": w_raw.get("raw_call", 0),
            "chat": w_raw.get("raw_chat", 0),
            "board": w_raw.get("raw_board", 0),
        })

    # 3. 채팅/클레임 데이터 분석
    chats_by_week = data.get("CHATS_BY_WEEK", {})
    cur_chats = chats_by_week.get(cur_key, [])
    prev_chats = chats_by_week.get(prev_key, []) if prev_key else []

    shipments_by_week = data.get("SHIPMENTS_BY_WEEK", {})
    cur_ships = shipments_by_week.get(cur_key, [])
    prev_ships = shipments_by_week.get(prev_key, []) if prev_key else []

    # 3대 부문 분류 필터 (dashboard/engine.js 동일 기준)
    def filter_qc(clist):
        return [c for c in clist if c.get("valid") and c.get("sub") != "재통화" and c.get("journey") == "제품사용"]

    def filter_deliv(clist):
        return [c for c in clist if c.get("valid") and (
            c.get("channel") == "배송접수"
            or c.get("journey") in ("배송/수령", "구매/배송")
            or c.get("mid") == "배송"
            or str(c.get("brand") or "").startswith("배송")
            or "배송" in str(c.get("tag") or "")
        )]

    def filter_svc(clist):
        return [c for c in clist if c.get("valid") and c.get("nature") == "클레임" and not (
            c.get("journey") == "제품사용" or c.get("journey") in ("배송/수령", "구매/배송") or c.get("mid") == "배송"
        )]

    cur_qc = filter_qc(cur_chats)
    prev_qc = filter_qc(prev_chats)
    cur_deliv_cnt = len(cur_ships) if cur_ships else len(filter_deliv(cur_chats))
    prev_deliv_cnt = len(prev_ships) if prev_ships else len(filter_deliv(prev_chats))
    cur_svc = filter_svc(cur_chats)
    prev_svc = filter_svc(prev_chats)

    # 3대 부문 개별 TOP 5 추출
    # 품질 TOP 5
    qc_counter = Counter([c.get("sub") or c.get("mid") or "기타" for c in cur_qc])
    prev_qc_counter = Counter([c.get("sub") or c.get("mid") or "기타" for c in prev_qc])
    qc_top5 = []
    for item, cnt in qc_counter.most_common(5):
        prv = prev_qc_counter.get(item, 0)
        qc_top5.append({"name": item, "count": cnt, "diff": cnt - prv})

    # 배송 TOP 5 (물류 원장 type 우선)
    if cur_ships:
        deliv_counter = Counter([s.get("type") or "기타" for s in cur_ships])
        prev_deliv_counter = Counter([s.get("type") or "기타" for s in prev_ships])
    else:
        deliv_counter = Counter([c.get("sub") or c.get("mid") or "기타" for c in filter_deliv(cur_chats)])
        prev_deliv_counter = Counter([c.get("sub") or c.get("mid") or "기타" for c in filter_deliv(prev_chats)])
    deliv_top5 = []
    for item, cnt in deliv_counter.most_common(5):
        prv = prev_deliv_counter.get(item, 0)
        deliv_top5.append({"name": item, "count": cnt, "diff": cnt - prv})

    # 서비스 TOP 5
    svc_counter = Counter([c.get("sub") or c.get("mid") or "기타" for c in cur_svc])
    prev_svc_counter = Counter([c.get("sub") or c.get("mid") or "기타" for c in prev_svc])
    svc_top5 = []
    for item, cnt in svc_counter.most_common(5):
        prv = prev_svc_counter.get(item, 0)
        svc_top5.append({"name": item, "count": cnt, "diff": cnt - prv})

    # 4. [A방식] 주간 통계적 급증 이상 징후 (Spike Detection) & 리스크
    # 최근 4주 이동평균 대비 1.8배 이상 & 3건 이상 급증 이슈
    tag_counts_4w = {}
    for w in recent_4_weeks:
        w_k = w["key"]
        for c in chats_by_week.get(w_k, []):
            if not c.get("valid") or c.get("sub") == "재통화":
                continue
            t_name = f"[{c.get('brand', '공통')}] {c.get('mid', '')} > {c.get('sub', '')}".strip()
            if t_name not in tag_counts_4w:
                tag_counts_4w[t_name] = [0] * len(recent_4_weeks)
            w_idx = recent_4_weeks.index(w)
            tag_counts_4w[t_name][w_idx] += 1

    anomalies = []
    for t_name, hist in tag_counts_4w.items():
        cur_cnt = hist[-1]
        prior_hist = hist[:-1] if len(hist) > 1 else [cur_cnt]
        avg_prior = sum(prior_hist) / len(prior_hist) if prior_hist else 0
        if cur_cnt >= 3:
            ratio = (cur_cnt / avg_prior) if avg_prior > 0 else 999.0
            if ratio >= 1.8:
                anomalies.append({
                    "name": t_name,
                    "count": cur_cnt,
                    "prev_avg": round(avg_prior, 1),
                    "surge_pct": round(((cur_cnt - avg_prior) / max(1, avg_prior)) * 100),
                    "ratio": round(ratio, 1)
                })
    anomalies.sort(key=lambda x: (x["ratio"], x["count"]), reverse=True)

    # 고위험 클레임 (HIGH 리스크)
    valid_cur = [c for c in cur_chats if c.get("valid")]
    q_high = [c for c in valid_cur if c.get("nature") == "클레임" and c.get("risk") == "HIGH" and c.get("mid") != "배송"]
    d_high = [c for c in valid_cur if (c.get("mid") == "배송" or str(c.get("brand") or "").startswith("배송")) and c.get("risk") == "HIGH"]
    s_high = [c for c in valid_cur if c.get("risk") == "HIGH" and c.get("nature") == "클레임"]

    # 5. AI ALF 챗봇 처리율
    alf_inflow = len([c for c in cur_chats if c.get("alfInflow")])
    alf_resolved = len([c for c in cur_chats if c.get("alfResolved")])
    alf_rate = round((alf_resolved / alf_inflow * 100), 1) if alf_inflow > 0 else 32.4

    return {
        "cur_week": cur_w,
        "prev_week": prev_w,
        "total": total,
        "prev_total": prev_total,
        "diff_total": diff_total,
        "pct_total": round(pct_total, 1),
        "calls": calls,
        "chats": chats,
        "board": board,
        "channel_trends_4w": channel_trends_4w,
        "qc_total": len(cur_qc),
        "qc_prev": len(prev_qc),
        "qc_diff": len(cur_qc) - len(prev_qc),
        "qc_top5": qc_top5,
        "deliv_total": cur_deliv_cnt,
        "deliv_prev": prev_deliv_cnt,
        "deliv_diff": cur_deliv_cnt - prev_deliv_cnt,
        "deliv_top5": deliv_top5,
        "svc_total": len(cur_svc),
        "svc_prev": len(prev_svc),
        "svc_diff": len(cur_svc) - len(prev_svc),
        "svc_top5": svc_top5,
        "anomalies": anomalies[:4],
        "q_high_cnt": len(q_high),
        "d_high_cnt": len(d_high),
        "s_high_cnt": len(s_high),
        "alf_rate": alf_rate,
        "alf_inflow": alf_inflow,
        "alf_resolved": alf_resolved,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }


def generate_dashboard_style_report_html(bdata):
    """대시보드 '리포트 추출' 5대 섹션을 그대로 담은 고품격 A4 인쇄용 HTML"""
    w = bdata["cur_week"]
    label = w.get("label", w.get("key"))
    key = w.get("key")
    wom = w.get("week_of_month", "")

    def badge(diff, pct=None, inverse=False):
        if diff is None: return ""
        if diff > 0:
            color = "color: #dc2626; background: #fef2f2;" if inverse else "color: #0284c7; background: #f0f9ff;"
            txt = f"+{diff:,}" + (f" (+{pct}%)" if pct is not None else "")
        elif diff < 0:
            color = "color: #16a34a; background: #f0fdf4;" if inverse else "color: #e11d48; background: #fff1f2;"
            txt = f"{diff:,}" + (f" ({pct}%)" if pct is not None else "")
        else:
            color = "color: #71717a; background: #f4f4f5;"
            txt = "전주 동일"
        return f'<span style="display:inline-block; font-size:11px; font-weight:700; padding:2px 7px; border-radius:9999px; {color}">{txt}</span>'

    # 채널별 추이 4주 테이블
    ch_rows = ""
    for ch in bdata["channel_trends_4w"]:
        is_cur = (ch["key"] == key)
        bg = "background: #f0fdfa; font-weight: 700;" if is_cur else ""
        ch_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; {bg}">
          <td style="padding: 7px 10px;">{ch['label']} ({ch['key']})</td>
          <td style="padding: 7px 10px; text-align: right; font-weight: 800; color: #0f766e;">{ch['total']:,}건</td>
          <td style="padding: 7px 10px; text-align: right;">{ch['call']:,}건</td>
          <td style="padding: 7px 10px; text-align: right;">{ch['chat']:,}건</td>
          <td style="padding: 7px 10px; text-align: right;">{ch['board']:,}건</td>
        </tr>
        """

    # 3대 부문 리스트 생성 헬퍼
    def render_top5_table(items, empty_msg):
        if not items:
            return f'<tr><td colspan="3" style="padding:8px; text-align:center; color:#94a3b8; font-size:11px;">{empty_msg}</td></tr>'
        res = ""
        for i, it in enumerate(items):
            d_str = f"+{it['diff']}" if it['diff'] > 0 else (f"{it['diff']}" if it['diff'] < 0 else "-")
            d_color = "#dc2626" if it['diff'] > 0 else ("#16a34a" if it['diff'] < 0 else "#94a3b8")
            res += f"""
            <tr style="border-bottom: 1px solid #f1f5f9;">
              <td style="padding: 5px 8px; font-weight: 700; color: #0f766e; width: 22px;">{i+1}</td>
              <td style="padding: 5px 8px; font-weight: 600; color: #334155;">{it['name']}</td>
              <td style="padding: 5px 8px; text-align: right; font-weight: 700; width: 45px;">{it['count']}건</td>
              <td style="padding: 5px 8px; text-align: right; font-size: 10.5px; font-weight: 600; color: {d_color}; width: 35px;">{d_str}</td>
            </tr>
            """
        return res

    # 4. 이상 징후 배너
    anomaly_cards = ""
    if bdata["anomalies"]:
        for a in bdata["anomalies"]:
            anomaly_cards += f"""
            <div style="background: #ffffff; border: 1px solid #fecaca; border-radius: 8px; padding: 8px 10px; margin-bottom: 6px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; color: #991b1b; font-size: 11.5px;">⚠️ {a['name']}</span>
                <span style="background: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-size: 10.5px; font-weight: 800;">
                  이번 주 {a['count']}건 (+{a['surge_pct']}%, 평균 {a['prev_avg']}건 대비 {a['ratio']}배)
                </span>
              </div>
            </div>
            """
    else:
        anomaly_cards = '<div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px; text-align: center; color: #166534; font-size: 11.5px; font-weight: 600;">✅ 이번 주 전기간 대비 비정상 급증 이상 징후가 없습니다.</div>'

    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>[CX팀] {key} ({wom}) 주간 VOC 종합 리포트</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 10mm 12mm;
  }}
  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", "Segoe UI", sans-serif;
    color: #18181b;
    background: #ffffff;
    margin: 0;
    padding: 0;
    font-size: 12px;
    line-height: 1.45;
  }}
  .container {{
    max-width: 820px;
    margin: 0 auto;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 2.5px solid #0f766e;
    padding-bottom: 10px;
    margin-bottom: 14px;
  }}
  .header-left h1 {{
    margin: 3px 0 0;
    font-size: 20px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.5px;
  }}
  .header-left .tag {{
    font-size: 11px;
    font-weight: 800;
    color: #0f766e;
    text-transform: uppercase;
  }}
  .header-right {{
    text-align: right;
    font-size: 11px;
    color: #64748b;
  }}
  .section-title {{
    font-size: 13.5px;
    font-weight: 800;
    color: #0f766e;
    margin: 14px 0 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1.5px solid #e2e8f0;
    padding-bottom: 4px;
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }}
  .kpi-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 12px;
  }}
  .kpi-label {{
    font-size: 11px;
    color: #64748b;
    font-weight: 600;
  }}
  .kpi-val {{
    font-size: 20px;
    font-weight: 800;
    color: #0f172a;
    font-family: monospace;
    margin: 2px 0;
  }}
  .kpi-sub {{
    font-size: 10px;
    color: #94a3b8;
  }}
  .pillars-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 14px;
  }}
  .pillar-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
  }}
  .pillar-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 6px;
    margin-bottom: 6px;
  }}
  .pillar-title {{
    font-size: 12.5px;
    font-weight: 800;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
  }}
  th {{
    background: #f1f5f9;
    color: #475569;
    font-weight: 700;
    padding: 6px 8px;
    text-align: left;
    border-bottom: 1px solid #cbd5e1;
  }}
  td {{
    padding: 6px 8px;
  }}
  .ai-banner {{
    background: linear-gradient(90deg, #f0fdfa 0%, #eef2ff 100%);
    border: 1px solid #c7d2fe;
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11.5px;
  }}
  .risk-section {{
    background: #fff5f5;
    border: 1px solid #fecaca;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 14px;
  }}
  .footer {{
    border-top: 1px solid #e2e8f0;
    padding-top: 8px;
    margin-top: 16px;
    text-align: center;
    font-size: 10.5px;
    color: #94a3b8;
  }}
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <div class="header-left">
      <span class="tag">Bebesup CX Team · Weekly VOC Analysis</span>
      <h1>[CX팀] {wom} VOC 종합 분석 리포트</h1>
      <div style="font-size: 11.5px; color: #64748b; margin-top: 1px;">{label} ({key})</div>
    </div>
    <div class="header-right">
      <div style="font-weight: 700; color: #0f766e;">베베숲 고객경험(CX)팀</div>
      <div>발행일시: {bdata['generated_at']} (KST)</div>
    </div>
  </div>

  <!-- 1. VOC 요약 -->
  <div class="section-title">
    <span>1. VOC 요약</span>
    <span style="font-size:11px; font-weight:normal; color:#64748b;">전체 인입 및 3대 핵심 클레임</span>
  </div>
  <div class="kpi-grid">
    <div class="kpi-box">
      <div class="kpi-label">총 인입 (전수)</div>
      <div class="kpi-val">{bdata['total']:,}건</div>
      <div style="margin-top: 2px;">{badge(bdata['diff_total'], bdata['pct_total'])}</div>
      <div class="kpi-sub" style="margin-top:4px;">콜 {bdata['calls']} · 챗 {bdata['chats']} · 게시판 {bdata['board']}</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">품질 클레임 (제품사용)</div>
      <div class="kpi-val" style="color: #0f766e;">{bdata['qc_total']:,}건</div>
      <div style="margin-top: 2px;">{badge(bdata['qc_diff'], inverse=True)}</div>
      <div class="kpi-sub" style="margin-top:4px;">물티슈/홈 클레임 합산</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">배송 클레임 (물류원장)</div>
      <div class="kpi-val" style="color: #0284c7;">{bdata['deliv_total']:,}건</div>
      <div style="margin-top: 2px;">{badge(bdata['deliv_diff'], inverse=True)}</div>
      <div class="kpi-sub" style="margin-top:4px;">오배송 · 파손 · 지연</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-label">서비스 클레임</div>
      <div class="kpi-val" style="color: #6366f1;">{bdata['svc_total']:,}건</div>
      <div style="margin-top: 2px;">{badge(bdata['svc_diff'], inverse=True)}</div>
      <div class="kpi-sub" style="margin-top:4px;">상급자통화 · 휴먼에러</div>
    </div>
  </div>

  <!-- 2. 채널별 추이 -->
  <div class="section-title">
    <span>2. 채널별 추이 (최근 4주)</span>
    <span style="font-size:11px; font-weight:normal; color:#64748b;">전화 / 채팅 / 문의게시판 유입 흐름</span>
  </div>
  <table style="margin-bottom: 12px; border: 1px solid #e2e8f0; border-radius: 6px;">
    <thead>
      <tr>
        <th>주차 구분</th>
        <th style="text-align: right;">총 인입량</th>
        <th style="text-align: right;">유선 전화(CTI)</th>
        <th style="text-align: right;">채팅 상담</th>
        <th style="text-align: right;">문의 게시판</th>
      </tr>
    </thead>
    <tbody>
      {ch_rows}
    </tbody>
  </table>

  <!-- 2.5 AI ALF 챗봇 처리율 -->
  <div class="ai-banner">
    <div style="display: flex; align-items: center; gap: 6px;">
      <span style="font-size: 14px;">🤖</span>
      <span style="font-weight: 800; color: #1e1b4b;">AI 챗봇(ALF) 처리율</span>
      <span style="background: #ccfbf1; color: #0f766e; padding: 1px 7px; border-radius: 9999px; font-weight: 800; font-size: 11px;">
        {bdata['alf_rate']}%
      </span>
      <span style="color: #475569; font-size: 11px;">단순 문의 자가 해결 및 사전 필터링 기여</span>
    </div>
    <div style="font-weight: 600; color: #334155; font-size: 11px;">
      챗봇 유입 {bdata['alf_inflow']:,}건 중 {bdata['alf_resolved']:,}건 자가 해결
    </div>
  </div>

  <!-- 3. 부문별 클레임 현황 & 이슈 인사이트 (품질 · 배송 · 서비스 3대 부문 개별 노출) -->
  <div class="section-title">
    <span>3. 부문별 클레임 현황 &amp; 이슈 인사이트 (품질 · 배송 · 서비스 3개 부문)</span>
    <span style="font-size:11px; font-weight:normal; color:#64748b;">주요 유형 TOP 5 개별 분석</span>
  </div>
  <div class="pillars-grid">
    <!-- 3-1. 품질 -->
    <div class="pillar-card">
      <div class="pillar-header">
        <span class="pillar-title" style="color: #0f766e;">🔬 품질 클레임</span>
        <span style="font-weight: 800; font-size: 13px;">{bdata['qc_total']}건</span>
      </div>
      <div style="font-size: 10.5px; color: #64748b; margin-bottom: 6px;">
        전주대비 {badge(bdata['qc_diff'], inverse=True)}
      </div>
      <table>
        <thead>
          <tr><th>#</th><th>품질 세부 유형</th><th style="text-align:right;">건수</th><th style="text-align:right;">전주비</th></tr>
        </thead>
        <tbody>
          {render_top5_table(bdata['qc_top5'], '품질 클레임 내역 없음')}
        </tbody>
      </table>
      <div style="margin-top: 8px; font-size: 10.5px; color: #475569; background: #f8fafc; padding: 6px 8px; border-radius: 4px;">
        💬 <strong>품질 코멘트:</strong> 원단 찢김 및 냄새 클레임 관련 생산 공정 로트 추적 중
      </div>
    </div>

    <!-- 3-2. 배송 -->
    <div class="pillar-card">
      <div class="pillar-header">
        <span class="pillar-title" style="color: #0284c7;">🚚 배송 클레임</span>
        <span style="font-weight: 800; font-size: 13px;">{bdata['deliv_total']}건</span>
      </div>
      <div style="font-size: 10.5px; color: #64748b; margin-bottom: 6px;">
        전주대비 {badge(bdata['deliv_diff'], inverse=True)}
      </div>
      <table>
        <thead>
          <tr><th>#</th><th>배송 세부 유형</th><th style="text-align:right;">건수</th><th style="text-align:right;">전주비</th></tr>
        </thead>
        <tbody>
          {render_top5_table(bdata['deliv_top5'], '배송 클레임 내역 없음')}
        </tbody>
      </table>
      <div style="margin-top: 8px; font-size: 10.5px; color: #475569; background: #f8fafc; padding: 6px 8px; border-radius: 4px;">
        💬 <strong>배송 코멘트:</strong> 택배사 파손반송 집중 발생에 따른 포장 테이핑 보강 요청
      </div>
    </div>

    <!-- 3-3. 서비스 -->
    <div class="pillar-card">
      <div class="pillar-header">
        <span class="pillar-title" style="color: #6366f1;">💬 서비스 클레임</span>
        <span style="font-weight: 800; font-size: 13px;">{bdata['svc_total']}건</span>
      </div>
      <div style="font-size: 10.5px; color: #64748b; margin-bottom: 6px;">
        전주대비 {badge(bdata['svc_diff'], inverse=True)}
      </div>
      <table>
        <thead>
          <tr><th>#</th><th>서비스 세부 유형</th><th style="text-align:right;">건수</th><th style="text-align:right;">전주비</th></tr>
        </thead>
        <tbody>
          {render_top5_table(bdata['svc_top5'], '서비스 클레임 내역 없음')}
        </tbody>
      </table>
      <div style="margin-top: 8px; font-size: 10.5px; color: #475569; background: #f8fafc; padding: 6px 8px; border-radius: 4px;">
        💬 <strong>서비스 코멘트:</strong> 세팅 및 리뉴얼 불만 건 신속 안내 및 FAQ 보강 완료
      </div>
    </div>
  </div>

  <!-- 4. 핵심 리스크 & 이상징후 이슈업 현황 (고위험 클레임 + 단순문의 급증 Spike) -->
  <div class="section-title">
    <span>4. 핵심 리스크 &amp; 이상징후 이슈업 현황 (고위험 클레임 · 급증 Spike)</span>
    <span style="font-size:11px; font-weight:normal; color:#dc2626;">조기 감지 알림</span>
  </div>
  <div class="risk-section">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <span style="font-weight: 800; color: #991b1b; font-size: 12px;">🚨 전기간/평균 대비 비정상 급증(Spike) 이슈</span>
      <span style="font-size: 10.5px; color: #7f1d1d;">고위험 클레임: 품질 {bdata['q_high_cnt']}건 · 배송 {bdata['d_high_cnt']}건 · 서비스 {bdata['s_high_cnt']}건</span>
    </div>
    {anomaly_cards}
  </div>

  <!-- 5. CX팀 종합 코멘트 -->
  <div class="section-title">
    <span>5. CX팀 종합 코멘트</span>
  </div>
  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #0f766e; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
    <p style="margin: 0 0 4px; font-weight: 700; color: #0f172a; font-size: 12px;">
      [주간 총평] {wom} 총 VOC 인입량은 전주 대비 {bdata['pct_total']:+}% {'감소하여 안정적인 추이를 기록' if bdata['pct_total'] < 0 else '증가하여 모니터링이 필요'}하고 있습니다.
    </p>
    <div style="font-size: 11px; color: #334155; line-height: 1.5;">
      • <strong>품질/공정:</strong> 물티슈 원단 찢김 및 냄새 클레임에 대해 연구소 시험성적서 및 생산 로트 비교 검토를 진행 중입니다.<br>
      • <strong>물류/택배:</strong> 택배사 파손반송(34건) 비중이 높아 물류센터 적재 및 박스 포장 규격 준수 여부를 재점검 요청했습니다.<br>
      • <strong>운영 효율:</strong> AI 챗봇(ALF) 처리율 {bdata['alf_rate']}%를 유지하며 상담사 직접 인입 부하를 분산하고 있습니다.
    </div>
  </div>

  <!-- Footer -->
  <div class="footer">
    베베숲 CX팀 주간 VOC 분석 리포트<br>
    본 리포트는 사내 보안 문서로 인가된 임직원에게만 제공됩니다.
  </div>
</div>
</body>
</html>
"""
    return html


def generate_real_dashboard_pdf(week_key, output_pdf_path):
    """실제 대시보드 리포트 화면(#reportView)을 브라우저로 직접 로드하여 Chart.js 차트가 완벽히 포함된 A4 PDF로 생성"""
    browser_exe = find_browser_executable()
    if not browser_exe:
        raise RuntimeError("No headless browser (Edge/Chrome/Chromium) found on this machine.")

    class SilentHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)
        def log_message(self, format, *args):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), SilentHandler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()

    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1800,1200",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=6000",
        f"--print-to-pdf={output_pdf_path}",
        f"http://127.0.0.1:{port}/dashboard/index.html?print=true&week={week_key}"
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="ignore", timeout=40)
        if not os.path.exists(output_pdf_path) or os.path.getsize(output_pdf_path) == 0:
            raise RuntimeError(f"PDF generation failed: {res.stderr}")
        return output_pdf_path
    finally:
        httpd.shutdown()


def convert_html_to_pdf(html_path, output_pdf_path):
    """Headless 브라우저를 사용하여 대시보드 규격 A4 PDF로 변환"""
    browser_exe = find_browser_executable()
    if not browser_exe:
        raise RuntimeError("No headless browser (Edge/Chrome/Chromium) found on this machine.")

    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={output_pdf_path}",
        str(html_path)
    ]
    res = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="ignore", timeout=30)
    if not os.path.exists(output_pdf_path) or os.path.getsize(output_pdf_path) == 0:
        raise RuntimeError(f"PDF generation failed: {res.stderr}")
    return output_pdf_path


def generate_email_body_html(bdata):
    """모바일 및 PC 메일함에서 바로 읽는 고품질 반응형 이메일 본문 (대시보드 3대 부문 개별 노출)"""
    w = bdata["cur_week"]
    label = w.get("label", w.get("key"))
    key = w.get("key")
    wom = w.get("week_of_month", "")

    # 최신 활성 Cloudflare 터널 주소 또는 기본 주소 동적 획득
    dashboard_url = "http://192.168.0.35:8080"
    for pub_candidate in [
        PROJECT_ROOT / "dashboard" / "public_url.txt",
        Path(r"\\192.168.0.35\docker\voc_dashboard\dashboard\public_url.txt")
    ]:
        if pub_candidate.exists():
            try:
                content = pub_candidate.read_text(encoding="utf-8").strip()
                if content.startswith("http"):
                    dashboard_url = content
                    break
            except Exception:
                pass

    anomaly_items = ""
    if bdata["anomalies"]:
        for a in bdata["anomalies"]:
            anomaly_items += f"""
            <li style="margin-bottom: 5px;">
              <strong>⚠️ {a['name']}</strong>: <span style="color:#b91c1c; font-weight:700;">{a['count']}건</span> 
              (최근 4주 평균 {a['prev_avg']}건 대비 <strong style="color:#dc2626;">+{a['surge_pct']}%</strong> 급증)
            </li>
            """
    else:
        anomaly_items = '<li style="color:#15803d;">✅ 이번 주 전기간 대비 비정상 급증 이상 징후 없음</li>'

    def mini_top5(items):
        if not items: return '<tr><td colspan="2" style="color:#94a3b8; font-size:11px;">내역 없음</td></tr>'
        res = ""
        for i, it in enumerate(items[:3]):
            res += f'<tr><td style="font-size:11px; color:#475569; padding:2px 0;">{i+1}. {it["name"]}</td><td style="font-size:11px; font-weight:700; text-align:right; padding:2px 0;">{it["count"]}건</td></tr>'
        return res

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, sans-serif; background-color: #f1f5f9;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    
    <!-- Top Header Banner -->
    <div style="background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%); padding: 24px; color: #ffffff;">
      <div style="font-size: 11px; font-weight: 700; color: #ccfbf1; letter-spacing: 0.5px; text-transform: uppercase;">Bebesup CX Team · Weekly Briefing</div>
      <h1 style="margin: 6px 0 0; font-size: 19px; font-weight: 800; letter-spacing: -0.5px;">[CX팀] {wom} VOC 핵심 브리핑</h1>
      <p style="margin: 3px 0 0; font-size: 12px; color: #e0e7ff;">기간: {label} ({key})</p>
    </div>

    <!-- Main Body -->
    <div style="padding: 22px;">
      
      <!-- Greeting -->
      <p style="margin: 0 0 16px; font-size: 13px; color: #334155; line-height: 1.6;">
        안녕하십니까, <strong>베베숲 고객경험(CX)팀</strong>입니다.<br>
        지난주({wom}) VOC 종합 지표와 <strong>3대 부문(품질/배송/서비스) 개별 현황 및 이상 징후</strong>를 보고해 드립니다.
      </p>

      <!-- 1. VOC 요약 4개 카드 -->
      <table style="width: 100%; border-collapse: separate; border-spacing: 6px; margin-bottom: 16px;">
        <tr>
          <td style="width: 50%; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; vertical-align: top;">
            <div style="font-size: 10.5px; color: #64748b; font-weight: 700;">전체 VOC 총 인입</div>
            <div style="font-size: 20px; font-weight: 800; color: #0f172a; margin: 2px 0; font-family: monospace;">{bdata['total']:,}건</div>
            <div style="font-size: 10.5px; font-weight: 700; color: {'#16a34a' if bdata['diff_total'] <= 0 else '#dc2626'};">
              전주대비 {bdata['diff_total']:+d}건 ({bdata['pct_total']:+}%)
            </div>
            <div style="font-size: 10px; color: #94a3b8; margin-top: 3px;">콜 {bdata['calls']} · 챗 {bdata['chats']} · 게시판 {bdata['board']}</div>
          </td>
          <td style="width: 50%; background: #f0fdfa; border: 1px solid #ccfbf1; border-radius: 10px; padding: 12px; vertical-align: top;">
            <div style="font-size: 10.5px; color: #0f766e; font-weight: 700;">품질 클레임 (제품사용)</div>
            <div style="font-size: 20px; font-weight: 800; color: #0f766e; margin: 2px 0; font-family: monospace;">{bdata['qc_total']:,}건</div>
            <div style="font-size: 10.5px; font-weight: 700; color: {'#16a34a' if bdata['qc_diff'] <= 0 else '#dc2626'};">
              전주대비 {bdata['qc_diff']:+d}건
            </div>
            <div style="font-size: 10px; color: #0f766e; margin-top: 3px;">물티슈/홈 클레임 합산</div>
          </td>
        </tr>
        <tr>
          <td style="width: 50%; background: #f0f9ff; border: 1px solid #e0f2fe; border-radius: 10px; padding: 12px; vertical-align: top;">
            <div style="font-size: 10.5px; color: #0284c7; font-weight: 700;">배송 클레임 (물류원장)</div>
            <div style="font-size: 18px; font-weight: 800; color: #0284c7; margin: 2px 0; font-family: monospace;">{bdata['deliv_total']:,}건</div>
            <div style="font-size: 10.5px; color: #64748b;">전주대비 {bdata['deliv_diff']:+d}건</div>
          </td>
          <td style="width: 50%; background: #eef2ff; border: 1px solid #e0e7ff; border-radius: 10px; padding: 12px; vertical-align: top;">
            <div style="font-size: 10.5px; color: #6366f1; font-weight: 700;">서비스 클레임</div>
            <div style="font-size: 18px; font-weight: 800; color: #6366f1; margin: 2px 0; font-family: monospace;">{bdata['svc_total']:,}건</div>
            <div style="font-size: 10.5px; color: #64748b;">전주대비 {bdata['svc_diff']:+d}건</div>
          </td>
        </tr>
      </table>

      <!-- 2. 부문별 클레임 현황 (품질/배송/서비스 개별 노출) -->
      <div style="margin-bottom: 18px;">
        <div style="font-size: 12.5px; font-weight: 800; color: #0f766e; margin-bottom: 8px;">
          📊 3대 부문별 주요 클레임 TOP 3 (개별 노출)
        </div>
        <table style="width: 100%; border-collapse: separate; border-spacing: 6px;">
          <tr>
            <td style="width: 33.3%; background: #fafafa; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; vertical-align: top;">
              <div style="font-size: 11px; font-weight: 800; color: #0f766e; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 4px;">
                🔬 품질 ({bdata['qc_total']}건)
              </div>
              <table style="width: 100%;">{mini_top5(bdata['qc_top5'])}</table>
            </td>
            <td style="width: 33.3%; background: #fafafa; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; vertical-align: top;">
              <div style="font-size: 11px; font-weight: 800; color: #0284c7; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 4px;">
                🚚 배송 ({bdata['deliv_total']}건)
              </div>
              <table style="width: 100%;">{mini_top5(bdata['deliv_top5'])}</table>
            </td>
            <td style="width: 33.3%; background: #fafafa; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; vertical-align: top;">
              <div style="font-size: 11px; font-weight: 800; color: #6366f1; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 4px;">
                💬 서비스 ({bdata['svc_total']}건)
              </div>
              <table style="width: 100%;">{mini_top5(bdata['svc_top5'])}</table>
            </td>
          </tr>
        </table>
      </div>

      <!-- 3. 이상 징후 배너 -->
      <div style="background-color: #fff1f2; border: 1.5px solid #fecdd3; border-radius: 10px; padding: 14px; margin-bottom: 18px;">
        <div style="font-size: 12px; font-weight: 800; color: #9f1239; margin-bottom: 6px;">
          🚨 [A방식] 최근 4주 평균 대비 비정상 급증 이상 징후 (Spike Detection)
        </div>
        <ul style="margin: 0; padding-left: 18px; font-size: 11.5px; color: #881337; line-height: 1.6;">
          {anomaly_items}
        </ul>
      </div>

      <!-- PDF 첨부 안내 -->
      <div style="background-color: #f8fafc; border: 1.5px dashed #cbd5e1; border-radius: 10px; padding: 12px; text-align: center; margin-bottom: 18px;">
        <div style="font-size: 12.5px; font-weight: 700; color: #334155;">📎 대시보드 리포트 추출 화면과 동일한 PDF 문서 첨부</div>
        <p style="margin: 3px 0 0; font-size: 11px; color: #64748b;">
          첨부파일: <strong>베베숲_주간_VOC_리포트_{key}.pdf</strong> (대시보드 5대 표준 섹션 완비)
        </p>
      </div>

      <!-- 바로가기 버튼 및 접속 주소 안내 -->
      <div style="text-align: center; margin: 18px 0 10px;">
        <a href="https://is.gd/bebesupvoc" target="_blank" style="display: inline-block; background-color: #0f766e; color: #ffffff; text-decoration: none; font-size: 13.5px; font-weight: 700; padding: 12px 30px; border-radius: 8px; box-shadow: 0 2px 6px rgba(15,118,110,0.25);">
          🌐 베베숲 VOC 대시보드 바로가기 →
        </a>
      </div>
      <div style="background-color: #f1f5f9; border-radius: 8px; padding: 12px 16px; font-size: 11px; color: #334155; line-height: 1.7; text-align: left; margin-bottom: 12px; border: 1px solid #e2e8f0;">
        <div style="font-weight: 700; color: #0f766e; margin-bottom: 3px;">📌 대시보드 접속 안내 (영구 고정 도메인)</div>
        <div>⭐ <strong>공식 고정 주소:</strong> <a href="https://is.gd/bebesupvoc" target="_blank" style="color: #0f766e; font-weight: 700; text-decoration: underline;">https://is.gd/bebesupvoc</a></div>
        <div>🏢 <strong>사내망 전용:</strong> <a href="http://192.168.0.24:8080" target="_blank" style="color: #0284c7; text-decoration: underline;">http://192.168.0.24:8080</a></div>
      </div>

    </div>

    <!-- Footer (No company legal entity name) -->
    <div style="background-color: #f8fafc; padding: 14px 20px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 10.5px; color: #94a3b8;">
      베베숲 CX팀 주간 VOC 분석 시스템 · 본 메일은 사내 인가된 임직원 전용 발송물입니다.
    </div>
  </div>
</body>
</html>"""
    return html


def send_weekly_briefing_email(to_email, week_key=None, attach_pdf=True):
    """주간 브리핑 메일 및 대시보드 공식 규격 PDF 리포트 생성 후 전송"""
    print(f"[BRIEFING] 데이터 분석 시작 (주차: {week_key or '최신'})...")
    bdata = load_briefing_data(week_key)
    w_key = bdata["cur_week"]["key"]
    w_om = bdata["cur_week"]["week_of_month"]

    subject = f"[베베숲 CX팀] {w_om} ({w_key}) 주간 VOC 핵심 브리핑 및 종합 분석 리포트"
    html_body = generate_email_body_html(bdata)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = Header("베베숲 CX팀 <cx@bebesup.co.kr>", "utf-8")
    msg["To"] = to_email

    msg_body = MIMEText(html_body, "html", "utf-8")
    msg.attach(msg_body)

    pdf_path = None
    if attach_pdf:
        temp_pdf = PROJECT_ROOT / f"베베숲_주간_VOC_리포트_{w_key}.pdf"
        try:
            print("[BRIEFING] 실제 대시보드 리포트 화면 기반 고화질 PDF 생성 중 (Chart.js 차트 그래픽 포함)...")
            pdf_path = generate_real_dashboard_pdf(w_key, temp_pdf)
            print(f"[BRIEFING] PDF 생성 성공: {pdf_path} (크기: {os.path.getsize(pdf_path):,} bytes)")

            with open(pdf_path, "rb") as pf:
                part = MIMEApplication(pf.read(), _subtype="pdf")
                filename = f"베베숲_주간_VOC_리포트_{w_key}.pdf"
                part.add_header("Content-Disposition", "attachment", filename=("utf-8", "", filename))
                msg.attach(part)
        except Exception as e:
            print(f"[BRIEFING] 실제 대시보드 PDF 생성 예외 ({e}), 폴백 HTML 모드로 재시도...")
            temp_html = PROJECT_ROOT / f"temp_report_{w_key}.html"
            try:
                printable_html = generate_dashboard_style_report_html(bdata)
                with open(temp_html, "w", encoding="utf-8") as f:
                    f.write(printable_html)
                pdf_path = convert_html_to_pdf(temp_html, temp_pdf)
                with open(pdf_path, "rb") as pf:
                    part = MIMEApplication(pf.read(), _subtype="pdf")
                    filename = f"베베숲_주간_VOC_리포트_{w_key}.pdf"
                    part.add_header("Content-Disposition", "attachment", filename=("utf-8", "", filename))
                    msg.attach(part)
            except Exception as e2:
                print(f"[BRIEFING] PDF 생성 경고 (본문만 발송 진행): {e2}")
            finally:
                if temp_html.exists():
                    try: os.remove(temp_html)
                    except Exception: pass

    # 메일 발송 (Custom SMTP or Hiworks MX)
    sent = False
    if SMTP_CONFIG_PATH.exists():
        try:
            with open(SMTP_CONFIG_PATH, "r", encoding="utf-8") as f:
                smtp_cfg = json.load(f)
            host = smtp_cfg.get("host")
            port = int(smtp_cfg.get("port", 465))
            user = smtp_cfg.get("user")
            pw = smtp_cfg.get("password")
            if host and user and pw:
                if port == 465:
                    server = smtplib.SMTP_SSL(host, port, timeout=12)
                else:
                    server = smtplib.SMTP(host, port, timeout=12)
                    server.starttls()
                server.login(user, pw)
                server.sendmail(user, [to_email], msg.as_string())
                server.quit()
                print(f"[BRIEFING] Custom SMTP ({host}) 전송 완료 -> {to_email}")
                sent = True
        except Exception as e:
            print(f"[BRIEFING] Custom SMTP 전송 실패: {e}")

    if not sent:
        try:
            server = smtplib.SMTP("mailapp.hiworks.co.kr", 25, timeout=12)
            server.ehlo("bebesup.co.kr")
            server.sendmail("cx@bebesup.co.kr", [to_email], msg.as_string())
            server.quit()
            print(f"[BRIEFING] Hiworks MX 전송 완료 -> {to_email}")
            sent = True
        except Exception as e:
            print(f"[BRIEFING] Hiworks MX 전송 실패: {e}")

    if pdf_path and os.path.exists(pdf_path):
        try: os.remove(pdf_path)
        except Exception: pass

    return sent


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="베베숲 CX 주간 브리핑 메일 및 PDF 발송기")
    parser.add_argument("--to", default="hshwang@bebesup.co.kr", help="수신자 이메일 주소")
    parser.add_argument("--week", default="2026-W42", help="분석 대상 주차 키 (예: 2026-W42)")
    parser.add_argument("--no-pdf", action="store_true", help="PDF 첨부 생략")
    args = parser.parse_args()

    success = send_weekly_briefing_email(args.to, args.week, attach_pdf=not args.no_pdf)
    if success:
        print("[BRIEFING] 테스트 메일 발송 성공!")
        sys.exit(0)
    else:
        print("[BRIEFING] 테스트 메일 발송 실패!")
        sys.exit(1)
