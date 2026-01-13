# Vercel 배포 가이드

이 프로젝트를 Vercel에 배포하는 방법을 안내합니다.

## 사전 준비사항

1. **Vercel 계정 생성**: [vercel.com](https://vercel.com)에서 계정 생성
2. **Vercel CLI 설치** (선택사항):
   ```bash
   npm i -g vercel
   ```

## 배포 단계

### 1. 데이터베이스 설정

Vercel은 SQLite를 지원하지 않으므로 PostgreSQL을 사용해야 합니다.

#### 옵션 A: Vercel Postgres 사용 (권장)

1. Vercel 대시보드에서 프로젝트 생성 후
2. **Storage** 탭에서 **Postgres** 추가
3. 자동으로 `POSTGRES_URL` 환경 변수가 설정됩니다

#### 옵션 B: 외부 PostgreSQL 사용

- Supabase, Neon, Railway 등에서 PostgreSQL 데이터베이스 생성
- 연결 문자열을 환경 변수로 설정

### 2. 환경 변수 설정

Vercel 대시보드의 **Settings > Environment Variables**에서 다음을 설정:

```
DATABASE_URL=postgresql://user:password@host:port/database
```

또는 Vercel Postgres를 사용하는 경우 자동으로 설정됩니다.

### 3. Git 저장소에 푸시

```bash
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### 4. Vercel에 배포

#### 방법 A: Vercel 웹 대시보드 사용

1. [vercel.com](https://vercel.com)에 로그인
2. **Add New Project** 클릭
3. GitHub/GitLab/Bitbucket 저장소 연결
4. 프로젝트 선택 후 **Deploy** 클릭
5. 빌드 설정은 자동으로 감지됩니다

#### 방법 B: Vercel CLI 사용

```bash
vercel
```

처음 배포 시:
- 프로젝트 설정 확인
- 환경 변수 설정 (선택사항)

프로덕션 배포:
```bash
vercel --prod
```

## 주요 변경사항

### 서버리스 환경 대응

1. **APScheduler 제거**: 서버리스 환경에서는 백그라운드 스케줄러가 작동하지 않습니다.
2. **Vercel Cron Jobs 사용**: `vercel.json`에 cron 설정이 포함되어 있습니다.
   - 현재 설정: 10분마다 `/api/cron/check-tasks` 호출
   - 필요시 `vercel.json`에서 스케줄 수정 가능

3. **데이터베이스 변경**: SQLite → PostgreSQL
   - `database.py`가 환경 변수 `DATABASE_URL`을 자동으로 감지합니다.

## Cron 스케줄 수정

`vercel.json` 파일에서 cron 스케줄을 수정할 수 있습니다:

```json
{
  "crons": [
    {
      "path": "/api/cron/check-tasks",
      "schedule": "*/10 * * * *"  // 10분마다
    }
  ]
}
```

다른 스케줄 예시:
- `*/5 * * * *` - 5분마다
- `*/30 * * * *` - 30분마다
- `0 * * * *` - 매시간

## 문제 해결

### 데이터베이스 연결 오류

- `DATABASE_URL` 환경 변수가 올바르게 설정되었는지 확인
- PostgreSQL 데이터베이스가 실행 중인지 확인
- 방화벽 설정 확인 (외부 데이터베이스 사용 시)

### Cron이 작동하지 않음

- Vercel Pro 플랜이 필요할 수 있습니다 (무료 플랜에서는 제한적)
- `vercel.json`의 cron 설정 확인
- Vercel 대시보드의 **Crons** 탭에서 실행 로그 확인

### 빌드 오류

- `requirements.txt`의 모든 패키지가 올바른지 확인
- Python 버전 확인 (Vercel은 Python 3.9+ 지원)

## 로컬 개발

로컬에서 개발할 때는 SQLite를 계속 사용할 수 있습니다:

```bash
# 환경 변수 설정하지 않으면 자동으로 SQLite 사용
uvicorn main:app --reload
```

PostgreSQL을 로컬에서 사용하려면:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/monitoring"
uvicorn main:app --reload
```

## 추가 기능

### 수동 체크 엔드포인트

특정 작업을 즉시 체크하려면:
```
POST /tasks/{task_id}/check-now
```

### Cron 엔드포인트 직접 호출

테스트 목적으로:
```
GET /api/cron/check-tasks
```

## 참고사항

- Vercel의 서버리스 함수는 **10초 타임아웃**이 있습니다 (Pro 플랜은 60초)
- 많은 작업을 동시에 체크하면 타임아웃이 발생할 수 있습니다
- 필요시 작업을 배치로 나누어 처리하도록 코드 수정이 필요할 수 있습니다
