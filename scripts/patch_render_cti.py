# -*- coding: utf-8 -*-
import sys

def patch():
    with open('dashboard/render.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update KPI card for phone in channel tab
    old_kpi = '''      kpiCard("전화 (콜 / CTI)", `${curPhoneTotal.toLocaleString()}건`, E.delta(curPhoneTotal, prevPhoneTotal), {
        alert: curPhoneTotal > 500,
        subText: `인바운드(수신) ${curPhoneIn.toLocaleString()}건 / 아웃바운드(발신) ${curPhoneOut.toLocaleString()}건`
      })'''

    new_kpi = '''      kpiCard("전화 (실통화)", `${curPhoneTotal.toLocaleString()}건`, E.delta(curPhoneTotal, prevPhoneTotal), {
        alert: curPhoneTotal > 500,
        subText: curCti ? `수신 ${curPhoneIn.toLocaleString()}건 · 발신 ${curPhoneOut.toLocaleString()}건 (부재: 업무시간 내 ${curCti.inOpMissed}건 / 야간·주말 ${curCti.inOffMissed}건 별도)` : `수신 ${curPhoneIn.toLocaleString()}건 · 발신 ${curPhoneOut.toLocaleString()}건`
      })'''

    # 2. Update labels in channelMixChart
    old_mix = 'labels: ["전화 (콜)", "상담사챗", "챗봇 (셀프처리)"],'
    new_mix = 'labels: ["전화 (실통화)", "상담사챗", "챗봇 (셀프처리)"],'

    # 3. Update labels in channelShareChart
    old_share = '["전화 (CTI)", "상담사챗", "챗봇 (셀프처리)", "게시판(스마트스토어/몰)"]'
    new_share = '["전화 (실통화)", "상담사챗", "챗봇 (셀프처리)", "게시판(스마트스토어/몰)"]'

    # 4. Update table row name in channelMetricTableBody
    old_row_name = 'name: "전화 (Call / CTI)",'
    new_row_name = 'name: "전화 (실통화 / CTI)",'

    # 5. Update CTI KPI cards
    old_cti_kpi1 = 'kpiCard("총 CTI 통화 처리량", `${cur.totalCalls.toLocaleString()}건`'
    new_cti_kpi1 = 'kpiCard("총 실통화 완료 건수", `${cur.totalCalls.toLocaleString()}건`'

    old_cti_kpi2 = 'kpiCard("인바운드 실질 응답률", `${cur.answerRate.toFixed(1)}%`'
    new_cti_kpi2 = 'kpiCard("운영시간 내 실질 응답률", `${cur.answerRate.toFixed(1)}%`'

    # Apply replacements
    for o, n in [
        (old_kpi, new_kpi),
        (old_mix, new_mix),
        (old_share, new_share),
        (old_row_name, new_row_name),
        (old_cti_kpi1, new_cti_kpi1),
        (old_cti_kpi2, new_cti_kpi2),
    ]:
        if o in content:
            content = content.replace(o, n)
            print(f"Replaced: {o[:30]}...")
        else:
            print(f"WARN: Not found: {o[:30]}...")

    with open('dashboard/render.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: render.js updated!")

if __name__ == '__main__':
    patch()
