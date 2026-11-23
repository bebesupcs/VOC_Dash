# 베베숲(Bebesup) VOC 종합 분석 대시보드 시스템

베베숲 CX팀의 고객 문의(채널톡 채팅/CTI 전화), 배송 클레임(CJ대한통운, 풀필먼트), 판매처별 수기 게시판 문의 데이터를 실시간으로 자동 수집·분류·가공하여 경영진 및 실무진에게 제공하는 올인원 웹 대시보드 시스템입니다.

---

## 📌 주요 특징 및 기능

1. **옴니채널 데이터 자동 통합 ETL 파이프라인**
   - **채널톡(Channel.io)**: Open API v5 기반 실시간 상담 데이터 수집 및 과거 원장 엑셀 자동 증분 적재
   - **CTI 전화**: 통화 상세 원장 연동, 상담원별 응대율 및 부재중 통화(Missed Call) 정밀 매칭
   - **배송 클레임**: CJ대한통운 및 풀필먼트 오발송/파손 일지 자동 취합
   - **게시판 수기접수**: 구글 스프레드시트와 실시간 연동, **사내 원본 엑셀 서식 100% 보존** 동기화
2. **사내 표준 분류 및 운영 체계**
   - 168개 사내 표준 태그 마스터 기준 VOC 원인(품질, 배송, 성분, 용기, 캡 등) 자동 분류
   - 베베숲 고유의 **목요일~수요일 운영주차(17:00 마감)** 및 월간/분기/연도 메타데이터 자동 산출
3. **독립된 24시간 실가동 서버 (Synology NAS Docker)**
   - PC 전원이 꺼져 있어도 사내외 어디서나 24시간 대시보드 접속 가능
   - 도커 컨테이너 자체에서 백그라운드 데이터 갱신 및 보안 감사 로그(Audit Trail) 기록
4. **원터치 공식 보고서 생성**
   - 공식 주간/월간 엑셀 리포트(`[CX팀]_VOC_분석종합리포트.xlsx`) 원터치 생성
   - 경영진 보고용 고품질 PDF 리포트 출력 지원
5. **사내 임직원 보안 인증 체계**
   - 사내 임직원 명부 실시간 연동 및 이메일 OTP(일회용 인증번호) 2단계 인증
   - 직무별 화면 권한 제어 및 엑셀 다운로드 보안 감사 로그 영구 보관

---

## 📂 폴더 구조 안내

```text
D:\dev\VOC리포트 (GitHub: bebesupcs/VOC_Dash)
├── dashboard/               # 웹 대시보드 프론트엔드 UI 화면 (HTML, Vanilla JS, CSS)
│   ├── index.html           # 대시보드 메인 페이지
│   ├── render.js            # 화면 렌더링 및 UI 이벤트 핸들러
│   ├── engine.js            # 데이터 필터링, 차트 연산 및 집계 엔진
│   ├── data.js              # 대시보드 실데이터 캐시 (JS 객체 형태)
│   └── data.json            # 대시보드 실데이터 JSON
├── scripts/                 # 데이터 처리 및 서버 백엔드 파이썬 스크립트
│   ├── run_dashboard_server.py # 24시간 항시 가동 웹 서버 및 REST API 라우터
│   ├── fast_unified_sync.py    # 전체 옴니채널 통합 고속 동기화 오케스트레이터
│   ├── sync_channeltalk_api.py # 채널톡 Open API v5 연동 모듈
│   ├── sync_gdrive_board.py    # 구글 스프레드시트 게시판 수기접수 연동 모듈
│   ├── export_dashboard_data.py# SQLite DB -> data.js / data.json 고속 추출기
│   ├── generate_report_excel.py# 공식 VOC 종합 엑셀 리포트 생성기
│   ├── employee_auth.py        # 사내 임직원 OTP 인증 및 보안 감사 로그 모듈
│   └── backup_source_code.py   # 소스 코드 NAS 및 GitHub 자동 백업 모듈
├── templates/               # 원본 서식 디자인 엑셀 템플릿 보관소
│   └── 게시판_통합운영_template.xlsx
├── config/                  # 시스템 연동 설정 파일 (임직원 명부, 채널톡 설정)
├── tools/                   # 사외 접속 보안 유틸리티 (cloudflared 등)
├── Dockerfile               # Synology NAS 도커 컨테이너 빌드 명세서
├── docker-compose.yml       # 도커 컨테이너 실행 및 볼륨 마운트 설정
├── requirements.txt         # 파이썬 의존성 패키지 목록
└── start_dashboard.bat      # 로컬 PC 간편 테스트 실행 스크립트
```

---

## 🛠️ 인수인계 및 개발/수정 가이드

### 1. 코드 다운로드 (환경 셋업)
새로운 담당자나 PC에서 작업을 이어갈 때는 아래 명령어로 즉시 작업 환경을 구성할 수 있습니다:
```bash
git clone https://github.com/bebesupcs/VOC_Dash.git
cd VOC_Dash
pip install -r requirements.txt
```

### 2. 로컬 PC에서 테스트 실행
```bash
# 윈도우 환경에서 배치파일 더블클릭 또는:
python scripts/run_dashboard_server.py
```
브라우저에서 `http://localhost:8080` 접속하여 수정 사항을 바로 확인할 수 있습니다.

### 3. 데이터 동기화 수동 실행
```bash
python scripts/fast_unified_sync.py
```
- 채널톡, CTI, 배송, 구글 시트 게시판을 순차 점검하여 변경분을 DB에 반영하고 화면 데이터를 새로고침합니다.
- 동기화 완료 후 GitHub 및 NAS로 소스 코드가 자동 백업됩니다.

### 4. NAS 서버 반영 (운영 배포)
코드를 수정하여 GitHub에 푸시한 후, Synology NAS에 반영할 때는:
1. **Container Manager** 접속
2. **프로젝트** ➔ `voc-dashboard` 선택
3. **[작업] ➔ [빌드]** (또는 중지 후 재시작) 클릭
컨테이너가 최신 코드를 즉시 로드하여 서비스에 반영합니다.

---

## 💾 백업 체계

- **실서버 (Live)**: Synology NAS 본체 (`http://192.168.0.12:8080`, DDNS: `http://bebesup-voc.synology.me:8080`)
- **DB 및 원본 데이터 (NAS)**: `X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db`
- **로컬 2차 백업**: `D:\VOC_SHARE` (DB, 엑셀, 클레임 사진 미러링)
- **개발 소스 코드 3중 백업**:
  - 로컬 작업실: `D:\dev\VOC리포트`
  - GitHub: `https://github.com/bebesupcs/VOC_Dash.git`
  - NAS 저장소: `X:\_개발소스_백업\VOC리포트.git` 및 `최신소스/`
