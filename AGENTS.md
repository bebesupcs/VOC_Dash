# AGENTS.md - Antigravity & AI Agent Instruction Manual

이 문서는 베베숲(Bebesup) VOC 대시보드 프로젝트에서 AI 코딩 어시스턴트(Antigravity 등)가 작업을 이어받아 수행할 때 반드시 준수해야 하는 시스템 환경 명세 및 운영 규칙입니다.

---

## 1. 프로젝트 개요 & 인프라 정보

- **프로젝트 명**: 베베숲 VOC 대시보드 & 옴니채널 분석 시스템
- **작업 디렉토리**: `D:\dev\VOC리포트`
- **GitHub 원격 저장소**: `https://github.com/bebesupcs/VOC_Dash.git` (기본 브랜치: `main`)
- **NAS Git 백업**: `X:\_개발소스_백업\VOC리포트.git` (remote 이름: `nas`)
- **실운영 서버**: Synology DS716+ NAS (`192.168.0.12`) Docker 컨테이너 (`voc-dashboard`)
- **사내망 접속 주소**: `http://192.168.0.12:8080` (HTTP)
- **외부 공식 고정 주소 (DDNS)**: `http://bebesup-voc.synology.me:8080` (※ HTTPS 기본 포트 443 접속 금지, 반드시 `:8080` 명시)

---

## 2. 주요 스토리지 & 데이터 경로

| 용도 | 경로 | 설명 |
| :--- | :--- | :--- |
| **Live 메인 DB** | `X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\db\channeltalk_voc.db` | 실운영 SQLite 데이터베이스 (74MB+) |
| **게시판 엑셀 원본** | `X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\raw\게시판 데이터 원본\게시판_통합운영.xlsx` | 구글 시트 연동 원본 파일 (서식 100% 보존 필수) |
| **클레임 사진 원본** | `X:\9. 클레임 사진\2026` | 7,800여 장의 클레임 사진 마스터 보관소 |
| **로컬 2차 백업** | `D:\VOC_SHARE` | DB, 엑셀, 클레임 사진 단일 통합 미러링 경로 |
| **소스 코드 NAS 백업**| `X:\_개발소스_백업\최신소스` 및 `VOC리포트.git` | 소스 코드 비상 백업 |

---

## 3. 핵심 아키텍처 및 주요 스크립트

- **`scripts/fast_unified_sync.py`**: 배송, 게시판, 채널톡, DB 갱신, `data.js` 내보내기, 백업까지 한 번에 실행하는 메인 동기화 파이프라인.
- **`scripts/sync_gdrive_board.py`**: 구글 스프레드시트 수기접수 데이터를 가져와서 `templates/게시판_통합운영_template.xlsx`의 폰트/너비/테두리/수식을 보존하며 셀 데이터만 갱신.
- **`scripts/run_dashboard_server.py`**: 포트 8080 웹 서버 및 REST API (인증, 동기화, 리포트 출력, 감사 로그).
- **`scripts/export_dashboard_data.py`**: SQLite DB에서 대시보드 프론트엔드 캐시(`data.js`, `data.json`) 고속 추출.
- **`scripts/generate_report_excel.py`**: 공식 보고용 다중 시트 종합 엑셀 리포트 생성기.
- **`scripts/backup_source_code.py`**: `git push nas main` 및 `git push origin main`, 파일 미러링 수행.

---

## 4. AI 에이전트 작업 절대 원칙 (Constraints)

1. **운영 엑셀 서식 파괴 금지**:
   - `게시판_통합운영.xlsx`를 갱신할 때는 절대 일반 CSV 덤프나 스타일 없는 Workbook 생성을 하지 말 것. 반드시 `sync_gdrive_board.py`의 템플릿 기반 정밀 셀 업데이트 방식을 유지할 것.
2. **운영주차(목~수) 계산 기준**:
   - 베베숲의 모든 주간 통계는 **목요일 17:00 ~ 차주 수요일 17:00** 기준임.
3. **단일 백업 경로 준수**:
   - 로컬 백업 경로는 무조건 `D:\VOC_SHARE` 단일 폴더를 사용하며, 과거 분산 백업 폴더를 재생성하지 말 것.
4. **코드 배포 후 빌드**:
   - 도커 컨테이너 내부 코드를 갱신한 경우, NAS Container Manager에서 프로젝트 [빌드] 또는 `docker-compose.yml` 재빌드를 통해 반영해야 함.
5. **3중 백업 동기화**:
   - 주요 작업 완료 후에는 항상 `git push origin main`과 `git push nas main`을 실행하여 로컬, GitHub, NAS 세 곳의 코드를 일치시킬 것.
