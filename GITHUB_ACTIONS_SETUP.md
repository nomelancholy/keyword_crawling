# GitHub Actions 설정 가이드

이 프로젝트는 GitHub Actions를 사용하여 주기적으로 크롤링 작업을 실행합니다.

## 설정 방법

### 1. GitHub Secrets 설정

GitHub 저장소의 **Settings > Secrets and variables > Actions**에서 다음 Secret을 추가하세요:

```
DATABASE_URL=postgresql://user:password@host:port/database
```

#### 데이터베이스 옵션

**옵션 A: Supabase (무료 플랜 제공)**
1. [supabase.com](https://supabase.com)에서 프로젝트 생성
2. Settings > Database에서 연결 문자열 복사
3. `postgres://`를 `postgresql://`로 변경하여 Secret에 추가

**옵션 B: Neon (무료 플랜 제공)**
1. [neon.tech](https://neon.tech)에서 프로젝트 생성
2. 연결 문자열을 Secret에 추가

**옵션 C: Railway (무료 크레딧 제공)**
1. [railway.app](https://railway.app)에서 PostgreSQL 생성
2. 연결 문자열을 Secret에 추가

**옵션 D: Render (무료 플랜 제공)**
1. [render.com](https://render.com)에서 PostgreSQL 생성
2. 연결 문자열을 Secret에 추가

### 2. Cron 스케줄 수정 (선택사항)

`.github/workflows/cron.yml` 파일에서 실행 주기를 변경할 수 있습니다:

```yaml
schedule:
  - cron: '*/30 * * * *'  # 30분마다
```

다른 스케줄 예시:
- `*/5 * * * *` - 5분마다
- `*/30 * * * *` - 30분마다
- `0 * * * *` - 매시간
- `0 */6 * * *` - 6시간마다

**참고**: GitHub Actions의 무료 플랜은 월 2,000분의 실행 시간을 제공합니다.
- 10분마다 실행: 월 약 4,320분 (무료 플랜 초과)
- 30분마다 실행: 월 약 1,440분 (무료 플랜 내)
- 1시간마다 실행: 월 약 720분 (무료 플랜 내)

### 3. 워크플로우 테스트

1. **수동 실행**: GitHub 저장소의 **Actions** 탭에서 "Keyword Monitoring Cron Job" 워크플로우를 선택하고 "Run workflow" 클릭

2. **로그 확인**: 실행 후 로그를 확인하여 정상 작동 여부 확인

## 웹 서버 배포 (선택사항)

크롤링은 GitHub Actions에서 실행되지만, 웹 인터페이스를 사용하려면 웹 서버를 별도로 배포해야 합니다.

### 추천 플랫폼

1. **Railway** (railway.app)
   - 무료 크레딧 제공
   - 간단한 배포
   - PostgreSQL 포함

2. **Render** (render.com)
   - 무료 플랜 제공
   - 자동 배포

3. **Fly.io** (fly.io)
   - 무료 플랜 제공
   - 글로벌 배포

4. **Heroku** (heroku.com)
   - 유료 플랜만 제공 (2022년 이후)

### 배포 시 주의사항

- 웹 서버와 GitHub Actions가 같은 데이터베이스를 사용해야 합니다
- `DATABASE_URL` 환경 변수를 동일하게 설정하세요

## 문제 해결

### GitHub Actions가 실행되지 않음

- 저장소가 Private인 경우: GitHub Pro 플랜이 필요할 수 있습니다
- Cron 스케줄 확인: GitHub Actions는 최소 5분 간격으로만 실행됩니다
- 저장소 설정 확인: Actions가 활성화되어 있는지 확인

### 데이터베이스 연결 오류

- `DATABASE_URL` Secret이 올바르게 설정되었는지 확인
- PostgreSQL 데이터베이스가 실행 중인지 확인
- 방화벽 설정 확인 (외부 데이터베이스 사용 시)
- 연결 문자열 형식 확인: `postgresql://`로 시작해야 합니다

### 크롤링 실패

- 타임아웃: GitHub Actions는 최대 6시간 실행 가능
- 네트워크 오류: 대상 웹사이트의 robots.txt 확인
- 로그 확인: GitHub Actions의 실행 로그에서 상세 오류 확인

## 모니터링

GitHub Actions의 실행 내역은 **Actions** 탭에서 확인할 수 있습니다:
- 실행 시간
- 성공/실패 여부
- 상세 로그

## 비용

- **GitHub Actions**: 무료 플랜은 월 2,000분 제공
- **데이터베이스**: 선택한 플랫폼의 무료 플랜 사용 가능
- **웹 서버**: 선택한 플랫폼의 무료 플랜 사용 가능

## 보안

- `DATABASE_URL`은 절대 코드에 커밋하지 마세요
- GitHub Secrets를 사용하여 민감한 정보 보호
- 필요시 API 키를 추가하여 `/api/cron/check-tasks` 엔드포인트 보호
