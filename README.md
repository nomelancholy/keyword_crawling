# 웹사이트 키워드 모니터링 시스템

웹사이트에서 특정 키워드를 주기적으로 모니터링하고 발견 시 알림을 제공하는 FastAPI 기반 애플리케이션입니다.

## 주요 기능

- 🔍 **키워드 모니터링**: 지정한 웹사이트에서 특정 키워드를 주기적으로 검색
- ⏰ **스케줄링**: APScheduler를 사용한 자동 주기적 체크
- 📊 **작업 관리**: 웹 인터페이스를 통한 모니터링 작업 추가/삭제
- 🔔 **알림 기록**: 키워드 발견 시 컨텍스트와 함께 알림 저장
- 💾 **데이터베이스**: SQLite를 사용한 작업 및 알림 데이터 저장

## 기술 스택

- **FastAPI**: 웹 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **BeautifulSoup4**: 웹 스크래핑
- **APScheduler**: 백그라운드 작업 스케줄링
- **Jinja2**: 템플릿 엔진
- **SQLite**: 데이터베이스

## 설치 방법

1. 저장소 클론 또는 다운로드

2. 의존성 패키지 설치:

```bash
pip install -r requirements.txt
```

## 실행 방법

1. 애플리케이션 시작:

```bash
uvicorn main:app --reload
```

2. 웹 브라우저에서 접속:

```
http://localhost:8000
```

## 사용 방법

1. **모니터링 작업 추가**

   - 웹 인터페이스에서 URL, 키워드, 모니터링 주기(분)를 입력
   - "모니터링 시작" 버튼 클릭

2. **작업 목록 확인**

   - 등록된 모든 모니터링 작업을 테이블 형태로 확인
   - 마지막 확인 시간 확인 가능

3. **알림 확인**

   - 키워드가 발견되면 "최근 발견 알림" 섹션에 표시
   - 발견된 키워드 주변 컨텍스트 확인 가능

4. **작업 삭제**
   - 각 작업의 "삭제" 버튼을 클릭하여 모니터링 중지

## 프로젝트 구조

```
keyword_crawling/
├── main.py              # FastAPI 애플리케이션 메인 파일
├── database.py          # 데이터베이스 설정
├── models.py            # SQLAlchemy 모델 (Task, Alert)
├── requirements.txt     # Python 패키지 의존성
├── templates/
│   └── index.html      # 웹 인터페이스 템플릿
└── monitoring.db        # SQLite 데이터베이스 (자동 생성)
```

## 데이터베이스 모델

### Task (작업)

- `id`: 작업 고유 ID
- `url`: 모니터링할 웹사이트 URL
- `keyword`: 검색할 키워드
- `interval_minutes`: 모니터링 주기 (분)
- `is_active`: 활성 상태
- `last_checked`: 마지막 확인 시간
- `created_at`: 생성 시간

### Alert (알림)

- `id`: 알림 고유 ID
- `task_id`: 관련 작업 ID
- `found_at`: 키워드 발견 시간
- `context`: 키워드 발견 위치의 컨텍스트 스니펫

## API 엔드포인트

- `GET /`: 메인 페이지 (작업 목록 및 알림 표시)
- `POST /tasks/add`: 새 모니터링 작업 추가
- `POST /tasks/{task_id}/delete`: 작업 삭제

## Vercel 배포

이 프로젝트는 Vercel에 배포할 수 있습니다. 자세한 배포 가이드는 [VERCEL_DEPLOY.md](./VERCEL_DEPLOY.md)를 참조하세요.

### 빠른 배포 가이드

1. **Vercel Postgres 설정**

   - Vercel 대시보드에서 Storage > Postgres 추가
   - `DATABASE_URL` 환경 변수가 자동 설정됩니다

2. **Git 저장소에 푸시**

   ```bash
   git add .
   git commit -m "Prepare for Vercel"
   git push
   ```

3. **Vercel에 배포**
   - [vercel.com](https://vercel.com)에서 프로젝트 import
   - 자동으로 배포됩니다

### 주요 변경사항 (Vercel용)

- **APScheduler 제거**: 서버리스 환경 대응을 위해 Vercel Cron Jobs 사용
- **PostgreSQL 지원**: SQLite 대신 PostgreSQL 사용 (환경 변수로 자동 전환)
- **Cron 엔드포인트**: `/api/cron/check-tasks` (10분마다 자동 실행)

## 주의사항

- 웹사이트의 robots.txt 및 이용약관을 확인하세요
- 과도한 요청은 IP 차단을 유발할 수 있습니다
- 타임아웃은 10초로 설정되어 있습니다
- **로컬 환경**: APScheduler 사용 (SQLite)
- **Vercel 환경**: Vercel Cron Jobs 사용 (PostgreSQL)

## 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.
