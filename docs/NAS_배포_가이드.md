# Synology DS716+ VOC 대시보드 무중단 배포 가이드

## 1. 사전 구성 완료 내역
모든 배포 파일이 NAS 내 `/volume1/docker/voc_dashboard` 경로에 이미 복사 완료되었습니다:
- `docker-compose.yml` (포트: 8080)
- `Dockerfile` (Python 3.11 + Cloudflared)
- `requirements.txt`
- `dashboard/` (프론트엔드 및 데이터셋)
- `scripts/` (백엔드 서버 및 엑셀 리포트 생성기)

## 2. Container Manager에서 프로젝트 1분 생성 방법
1. Synology DSM 웹 관리도구 접속 (`http://192.168.0.35:5000`)
2. **Container Manager** (컨테이너 매니저) 앱 실행
3. 좌측 메뉴에서 **`프로젝트`** 클릭 ➔ 상단 **`[생성]`** 버튼 클릭
4. 설정값 확인:
   - **프로젝트 이름**: `voc_dashboard`
   - **경로**: `/docker/voc_dashboard` 선택
   - **원본**: `기존 docker-compose.yml 사용` (자동 선택됨)
5. **[다음] ➔ [완료]** 클릭
   - 이미지가 자동 빌드되고 컨테이너가 백그라운드로 실행됩니다 (약 1~2분 소요).

## 3. 접속 주소 (사내 24시간 상시 접속)
- 사내 PC / 모바일 접속: **`http://192.168.0.35:8080`**
- 사용자 PC 전원이 꺼져 있어도 사내 모든 직원이 24시간 접속 가능합니다.
