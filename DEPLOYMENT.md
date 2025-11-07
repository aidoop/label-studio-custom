# Label Studio Custom Image - 배포 가이드

## 목차
- [로컬 빌드 및 테스트](#로컬-빌드-및-테스트)
- [GitHub Container Registry 배포](#github-container-registry-배포)
- [HTTPS 프로덕션 배포](#https-프로덕션-배포) ⭐ **중요**
- [배포 방법](#배포-방법)

---

## HTTPS 프로덕션 배포

### 필수 환경 변수 설정

HTTPS 환경(개발서버, 프로덕션)에서는 다음 설정이 **반드시** 필요합니다:

```yaml
version: "3.8"

services:
  labelstudio:
    image: ghcr.io/aidoop/label-studio-custom:1.20.0-sso.22

    environment:
      # ================================================================
      # ⚠️ HTTPS 필수 설정
      # ================================================================

      # 1. HTTPS 쿠키 보안
      SESSION_COOKIE_SECURE: "true"        # ← 반드시 true!
      CSRF_COOKIE_SECURE: "true"           # ← 반드시 true!

      # 2. 쿠키 도메인 (서브도메인 공유)
      SESSION_COOKIE_DOMAIN: .nubison.io   # 점(.) 필수
      CSRF_COOKIE_DOMAIN: .nubison.io      # 점(.) 필수

      # 3. Label Studio URL (HTTPS)
      LABEL_STUDIO_HOST: https://label-dev.nubison.io

      # ================================================================
      # 데이터베이스 설정
      # ================================================================
      DJANGO_DB: default
      POSTGRES_HOST: postgres
      POSTGRES_DB: labelstudio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secure_password_here

      # ================================================================
      # SSO 설정
      # ================================================================
      JWT_SSO_COOKIE_NAME: ls_auth_token
      # 참고: SSO_AUTO_CREATE_USERS는 False로 고정 (v1.20.0-sso.24+)

      # ================================================================
      # iframe 보안 헤더 (선택)
      # ================================================================
      CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io"
      X_FRAME_OPTIONS: "SAMEORIGIN"
```

### 배포 체크리스트

#### ✅ **필수 설정**
```
[ ] SESSION_COOKIE_SECURE=true 설정
[ ] CSRF_COOKIE_SECURE=true 설정
[ ] SESSION_COOKIE_DOMAIN=.yourdomain.com (점 포함)
[ ] CSRF_COOKIE_DOMAIN=.yourdomain.com (점 포함)
[ ] LABEL_STUDIO_HOST=https://... (HTTPS URL)
[ ] POSTGRES_PASSWORD 강력한 비밀번호 설정
```

#### ✅ **배포 후 확인**
```
[ ] 브라우저 개발자 도구 → Application → Cookies 확인
    - ls_sessionid 쿠키의 Secure 플래그 확인 (✓ 있어야 함)
    - ls_csrftoken 쿠키의 Secure 플래그 확인 (✓ 있어야 함)
    - Domain이 .yourdomain.com으로 설정되었는지 확인
    - ls_csrftoken의 HttpOnly는 없어야 함 (JavaScript 접근 필요)
[ ] Label Studio 로그인 테스트
[ ] iframe 임베딩 테스트 (console → label studio)
[ ] 사용자 전환 테스트
```

### HTTP vs HTTPS 설정 비교

| 설정 | HTTP (로컬) | HTTPS (프로덕션) |
|------|-------------|------------------|
| `SESSION_COOKIE_SECURE` | `false` (기본값) | `true` ⚠️ **필수** |
| `CSRF_COOKIE_SECURE` | `false` (기본값) | `true` ⚠️ **필수** |
| `SESSION_COOKIE_DOMAIN` | `.localhost` | `.yourdomain.com` |
| `CSRF_COOKIE_DOMAIN` | `.localhost` | `.yourdomain.com` |
| `LABEL_STUDIO_HOST` | `http://...` | `https://...` |
| 브라우저 Secure 플래그 | 없음 | ✓ 있음 |

### 일반적인 문제

#### 문제 1: 로그인 후에도 로그인 페이지가 계속 표시됨
**원인**: `SESSION_COOKIE_SECURE=true`가 설정되지 않음

**해결**:
```yaml
environment:
  SESSION_COOKIE_SECURE: "true"  # 추가
  CSRF_COOKIE_SECURE: "true"     # 추가
```

#### 문제 2: iframe에서 쿠키가 전달되지 않음
**원인**: 쿠키 도메인이 서브도메인 공유 형식이 아님

**해결**:
```yaml
environment:
  SESSION_COOKIE_DOMAIN: .nubison.io  # 점(.) 추가
  CSRF_COOKIE_DOMAIN: .nubison.io     # 점(.) 추가
```

#### 문제 3: SSO 인증 후 세션이 생성되지 않음
**원인**: JWT 쿠키가 iframe에 전달되지 않음 (Secure 플래그 문제)

**진단**:
```bash
# Label Studio 로그 확인
docker logs label-studio-container -f | grep -i "jwt\|session"

# 정상:
[SSO Middleware] JWT token found in cookie 'ls_auth_token'
[SSO Middleware] User auto-logged in via JWT: user@example.com

# 문제:
[SSO Middleware] No JWT token found in cookies
```

**해결**:
```yaml
environment:
  SESSION_COOKIE_SECURE: "true"  # Label Studio에 설정
  CSRF_COOKIE_SECURE: "true"     # Label Studio에 설정
```

그리고 SSO Backend(누비슨 시스템)에서:
```javascript
// JWT 쿠키 설정 시
res.cookie("ls_auth_token", token, {
  domain: ".nubison.io",
  secure: true,        // ← HTTPS에서 필수!
  httpOnly: false,
  sameSite: "lax",
  maxAge: 600 * 1000
});
```

#### 문제 4: CSRF 토큰 관련 주의사항

**Q: ls_csrftoken 쿠키의 HttpOnly가 설정 안 되어 있는데 괜찮나요?**

**A: 괜찮습니다. 오히려 httpOnly=False가 정상입니다!**

CSRF 토큰은 JavaScript에서 읽어서 POST/PUT/DELETE 요청 시 `X-CSRFToken` 헤더에 포함해야 합니다. httpOnly=True로 설정하면 JavaScript가 읽을 수 없어 CSRF 보호가 작동하지 않습니다.

**쿠키별 httpOnly 설정:**

| 쿠키 | httpOnly | 이유 |
|------|----------|------|
| `ls_sessionid` | `true` ✅ | XSS 공격 방지, JavaScript 접근 불필요 |
| `ls_csrftoken` | `false` ✅ | JavaScript가 읽어서 헤더에 포함해야 함 |

**하지만 HTTPS 환경에서는 Secure 플래그는 필요합니다:**

```yaml
environment:
  CSRF_COOKIE_SECURE: "true"  # HTTPS에서 필수!
```

**배포 후 확인:**
- `ls_csrftoken` 쿠키의 Secure 플래그: ✓ 있어야 함
- `ls_csrftoken` 쿠키의 HttpOnly 플래그: 없어야 함 (JavaScript 접근 필요)

---

## 로컬 빌드 및 테스트

### 1. 이미지 빌드

```bash
cd /Users/super/Documents/GitHub/label-studio-custom

# 로컬 테스트용 이미지 빌드
docker build -t label-studio-custom:local .

# 특정 버전으로 빌드
docker build -t label-studio-custom:1.20.0-sso.5 .

# 빌드 확인
docker images | grep label-studio-custom
```

### 2. 로컬 테스트

```bash
# docker-compose.test.yml로 테스트
docker compose -f docker-compose.test.yml up -d

# 로그 확인
docker compose -f docker-compose.test.yml logs -f labelstudio

# 헬스체크
curl http://localhost:8081/health

# 종료
docker compose -f docker-compose.test.yml down -v
```

---

## GitHub Container Registry 배포

### 사전 준비

#### 1. GitHub Personal Access Token 생성

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 선택:
   - ✅ `write:packages` (패키지 업로드)
   - ✅ `read:packages` (패키지 다운로드)
   - ✅ `delete:packages` (패키지 삭제, 선택사항)
4. 토큰 생성 및 복사 (재표시 안됨)

#### 2. GitHub Container Registry 로그인

```bash
# 토큰을 환경변수로 설정
export GITHUB_TOKEN=<your-personal-access-token>

# 로그인
echo $GITHUB_TOKEN | docker login ghcr.io -u <your-github-username> --password-stdin

# 로그인 확인
# Successfully logged in to ghcr.io
```

---

## 배포 방법

### Option 1: 수동 배포 (빠른 테스트)

```bash
cd /Users/super/Documents/GitHub/label-studio-custom

# 1. 이미지 빌드
docker build -t label-studio-custom:local .

# 2. GitHub Container Registry 태그 추가
# 형식: ghcr.io/<github-username>/<image-name>:<version>
docker tag label-studio-custom:local ghcr.io/aidoop/label-studio-custom:1.20.0-sso.5

# 3. latest 태그도 추가
docker tag label-studio-custom:local ghcr.io/aidoop/label-studio-custom:latest

# 4. 이미지 푸시
docker push ghcr.io/aidoop/label-studio-custom:1.20.0-sso.5
docker push ghcr.io/aidoop/label-studio-custom:latest

# 5. 푸시 확인
# https://github.com/aidoop?tab=packages
```

#### 이미지 Public으로 설정

1. GitHub → Packages → label-studio-custom 클릭
2. "Package settings" → "Change visibility" → "Public"
3. 패키지 이름 입력하여 확인

---

### Option 2: GitHub Actions 자동 배포 (권장)

#### 준비사항

1. **GitHub 저장소 생성**:
   ```bash
   cd /Users/super/Documents/GitHub/label-studio-custom

   # GitHub에서 저장소 생성 후
   git remote add origin https://github.com/aidoop/label-studio-custom.git
   git branch -M main
   git push -u origin main
   ```

2. **GitHub Actions 권한 설정**:
   - Repository → Settings → Actions → General
   - "Workflow permissions" → "Read and write permissions" 선택

#### 배포 프로세스

##### 1. 개발/테스트 (PR/Push)

```bash
# feature 브랜치 생성 및 작업
git checkout -b feature/new-feature
# ... 코드 수정 ...
git add .
git commit -m "feat: Add new feature"
git push origin feature/new-feature

# Pull Request 생성
# → GitHub Actions가 자동으로 빌드 및 테스트 실행 (.github/workflows/build-and-test.yml)
```

##### 2. 릴리스 배포 (Tag Push)

```bash
cd /Users/super/Documents/GitHub/label-studio-custom

# 1. 코드 변경사항 커밋
git add .
git commit -m "feat: Release v1.20.0-sso.5"

# 2. 태그 생성
git tag v1.20.0-sso.5

# 3. 태그 푸시
git push origin v1.20.0-sso.5

# → GitHub Actions가 자동으로:
#    - 이미지 빌드
#    - ghcr.io에 푸시
#    - GitHub Release 생성
```

#### GitHub Actions Workflow 확인

**.github/workflows/publish-image.yml**가 자동으로:
1. `v*.*.*-sso.*` 태그 감지
2. Docker 이미지 빌드
3. GitHub Container Registry에 푸시:
   - `ghcr.io/aidoop/label-studio-custom:1.20.0-sso.5`
   - `ghcr.io/aidoop/label-studio-custom:latest`
4. GitHub Release 생성

---

## 버전 관리 전략

### 태그 규칙

```
v<label-studio-version>-sso.<custom-version>

예시:
- v1.20.0-sso.1  → Label Studio 1.20.0 기반, 첫 번째 SSO 커스터마이징
- v1.20.0-sso.5  → Label Studio 1.20.0 기반, JWT → Session 전환 (현재 버전)
- v1.21.0-sso.1  → Label Studio 1.21.0 업그레이드 (미래)
```

### 릴리스 체크리스트

- [ ] CHANGELOG.md 업데이트
- [ ] 버전 태그 확인
- [ ] 로컬 테스트 완료
- [ ] 태그 푸시
- [ ] GitHub Actions 빌드 성공 확인
- [ ] GitHub Packages에서 이미지 확인
- [ ] 이미지 Public 설정
- [ ] 샘플 앱에서 새 이미지 테스트

---

## 배포된 이미지 사용

### Pull 이미지

```bash
# Public 이미지 pull (최신 버전)
docker pull ghcr.io/aidoop/label-studio-custom:1.20.0-sso.7

# 또는 latest
docker pull ghcr.io/aidoop/label-studio-custom:latest
```

### Docker Compose에서 사용

```yaml
services:
  labelstudio:
    # 특정 버전 사용 (권장)
    image: ghcr.io/aidoop/label-studio-custom:1.20.0-sso.7

    # 또는 latest (개발용)
    # image: ghcr.io/aidoop/label-studio-custom:latest

    environment:
      POSTGRES_HOST: postgres
      POSTGRES_DB: labelstudio
      JWT_SSO_COOKIE_NAME: ls_auth_token
      # ... 기타 환경변수
```

---

## 멀티 플랫폼 빌드 (선택사항)

Linux AMD64 + ARM64 지원:

```bash
# Docker Buildx 설정
docker buildx create --use

# 멀티 플랫폼 빌드 및 푸시
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/aidoop/label-studio-custom:1.20.0-sso.5 \
  --push \
  .
```

**참고**: GitHub Actions workflow는 이미 멀티 플랫폼 빌드를 지원합니다.

---

## Private Registry 사용 (선택사항)

### Docker Hub

```bash
# Docker Hub 로그인
docker login

# 태그 및 푸시
docker tag label-studio-custom:local heartyoh/label-studio-custom:1.20.0-sso.5
docker push heartyoh/label-studio-custom:1.20.0-sso.5
```

### AWS ECR

```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com

# 태그 및 푸시
docker tag label-studio-custom:local \
  <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/label-studio-custom:1.20.0-sso.5
docker push <account-id>.dkr.ecr.ap-northeast-2.amazonaws.com/label-studio-custom:1.20.0-sso.5
```

---

## 문제 해결

### 푸시 권한 오류

```bash
# 에러: denied: permission_denied
# 해결: GitHub Token 권한 확인 (write:packages)

# 토큰 재생성 후 재로그인
echo $NEW_GITHUB_TOKEN | docker login ghcr.io -u aidoop --password-stdin
```

### 이미지가 표시되지 않음

1. GitHub → Packages 확인
2. 이미지 visibility 확인 (Private → Public)
3. Organization 패키지인 경우 organization packages 페이지 확인

### GitHub Actions 실패

```bash
# 로컬에서 workflow 테스트
act -j build  # act 도구 설치 필요

# 또는 로그 확인
# GitHub → Actions → 실패한 workflow → 로그 확인
```

---

## 다음 단계

1. ✅ 로컬 빌드 및 테스트
2. ✅ GitHub Container Registry에 첫 배포
3. ✅ 샘플 앱에서 배포된 이미지 테스트
4. ✅ CHANGELOG.md 업데이트
5. ✅ GitHub Release 생성
6. ✅ README.md에 이미지 주소 업데이트

---

## 참고 링크

- [GitHub Container Registry 문서](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Buildx 문서](https://docs.docker.com/buildx/working-with-buildx/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
