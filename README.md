# 웹사이트 키워드 모니터링 시스템

웹사이트에서 특정 키워드를 주기적으로 모니터링하고 발견 시 알림을 제공하는 FastAPI 기반 애플리케이션입니다.

## 주요 기능

- 🔍 **키워드 모니터링**: 지정한 웹사이트에서 특정 키워드를 주기적으로 검색
- ⏰ **스케줄링**: GitHub Actions를 사용한 자동 주기적 체크 (무료 플랜 지원)
- 📊 **작업 관리**: 웹 인터페이스를 통한 모니터링 작업 추가/삭제
- 🔔 **알림 기록**: 키워드 발견 시 컨텍스트와 함께 알림 저장
- 💾 **데이터베이스**: PostgreSQL 또는 SQLite 사용 (환경에 따라 자동 전환)

## 기술 스택

- **FastAPI**: 웹 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **BeautifulSoup4**: 웹 스크래핑
- **GitHub Actions**: 크롤링 작업 스케줄링 (무료 플랜 지원)
- **Jinja2**: 템플릿 엔진
- **PostgreSQL/SQLite**: 데이터베이스 (환경에 따라 자동 전환)

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
├── main.py                      # FastAPI 애플리케이션 메인 파일
├── cron_job.py                  # GitHub Actions에서 실행할 크롤링 스크립트
├── database.py                  # 데이터베이스 설정
├── models.py                    # SQLAlchemy 모델 (Task, Alert)
├── requirements.txt             # Python 패키지 의존성
├── templates/
│   └── index.html              # 웹 인터페이스 템플릿
├── .github/
│   └── workflows/
│       └── cron.yml            # GitHub Actions 워크플로우
└── monitoring.db                # SQLite 데이터베이스 (로컬 개발용)
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

## GitHub Actions 설정 (권장)

크롤링 작업은 GitHub Actions에서 실행됩니다. 무료 플랜에서도 사용 가능합니다.

### 빠른 설정 가이드

1. **GitHub Secrets 설정**

   - 저장소의 **Settings > Secrets and variables > Actions**로 이동
   - `DATABASE_URL` Secret 추가 (PostgreSQL 연결 문자열)
   - 예: `postgresql://user:password@host:port/database`

2. **데이터베이스 생성** (무료 옵션)

   - [Supabase](https://supabase.com) - 무료 플랜 제공
   - [Neon](https://neon.tech) - 무료 플랜 제공
   - [Railway](https://railway.app) - 무료 크레딧 제공
   - [Render](https://render.com) - 무료 플랜 제공

3. **자동 실행**
   - GitHub에 코드를 푸시하면 자동으로 워크플로우가 활성화됩니다
   - 기본 설정: 30분마다 자동 실행
   - 수동 실행: **Actions** 탭에서 "Run workflow" 클릭

### Cron 스케줄 수정

`.github/workflows/cron.yml` 파일에서 실행 주기를 변경할 수 있습니다:

```yaml
schedule:
  - cron: "*/30 * * * *" # 30분마다
```

**참고**: GitHub Actions 무료 플랜은 월 2,000분 제공

- 10분마다: 월 약 4,320분 (무료 플랜 초과)
- 30분마다: 월 약 1,440분 (무료 플랜 내) ✅
- 1시간마다: 월 약 720분 (무료 플랜 내) ✅

자세한 설정 가이드는 [GITHUB_ACTIONS_SETUP.md](./GITHUB_ACTIONS_SETUP.md)를 참조하세요.

## 웹 서버 배포 (선택사항)

크롤링은 GitHub Actions에서 실행되지만, 웹 인터페이스를 사용하려면 웹 서버를 별도로 배포해야 합니다.

### 추천 플랫폼

- **Railway** (railway.app) - 무료 크레딧 제공
- **Render** (render.com) - 무료 플랜 제공
- **Fly.io** (fly.io) - 무료 플랜 제공

Render 배포 가이드: [docs/RENDER_DEPLOY.md](./docs/RENDER_DEPLOY.md)

웹 서버와 GitHub Actions가 같은 데이터베이스를 사용해야 합니다.

## 주의사항

- 웹사이트의 robots.txt 및 이용약관을 확인하세요
- 과도한 요청은 IP 차단을 유발할 수 있습니다
- 타임아웃은 30초로 설정되어 있습니다 (GitHub Actions)
- **로컬 환경**: SQLite 사용 (환경 변수 없을 때)
- **GitHub Actions**: PostgreSQL 사용 (DATABASE_URL Secret 필요)
- GitHub Actions 무료 플랜은 월 2,000분 실행 시간 제공

## 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.
