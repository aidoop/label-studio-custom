# Label Studio Custom Image - 배포 가이드

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
