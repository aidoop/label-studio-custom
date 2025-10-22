# Label Studio Custom - SSO Edition

> Label Studio 1.20.0 기반 커스텀 Docker 이미지
> SSO 인증, hideHeader, Annotation 소유권 제어 기능 포함

[![Docker Image](https://img.shields.io/badge/docker-label--studio--custom-blue)](https://github.com/orgs/community/packages)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 개요

이 프로젝트는 [Label Studio](https://github.com/HumanSignal/label-studio) 1.20.0을 기반으로 SSO 인증 및 추가 기능을 포함한 커스텀 Docker 이미지를 제공합니다.

## 주요 기능

### 1. SSO 인증 (Native JWT)
- **label-studio-sso v6.0.7** 통합 (커스텀 빌드)
- JWT 토큰 기반 초기 인증
- **JWT → Django Session 전환**: 성능 최적화
  - JWT 인증 성공 시 Django Session 생성
  - JWT 쿠키 자동 삭제 (이후 Session만 사용)
  - 최초 1회만 JWT 검증, 이후 Session 기반 빠른 인증
- **사용자 전환 우선순위**: JWT가 기존 Session보다 우선
  - 미들웨어 수정: JWT 토큰 있으면 기존 세션 무시
  - 원활한 사용자 전환 (세션 충돌 없음)
- 쿠키 및 URL 파라미터 지원
- 사용자 자동 생성

### 2. hideHeader 기능
- iframe 임베딩 시 헤더 완전 제거
- URL 파라미터 `?hideHeader=true` 지원
- JavaScript로 CSS 변수 강제 적용
- 전체 화면 활용 (100vh)

### 3. Annotation 소유권 제어
- 사용자는 자신의 annotation만 수정/삭제 가능
- Django REST Framework permission 기반
- API 레벨 보안 (Postman, curl 등 직접 호출 차단)
- Admin 계정은 모든 annotation 접근 가능

## Quick Start

### Docker Hub에서 사용

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:13.18
    environment:
      POSTGRES_DB: labelstudio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres

  labelstudio:
    image: ghcr.io/aidoop/label-studio-custom:1.20.0-sso.5

    depends_on:
      - postgres

    environment:
      # Database
      DJANGO_DB: default
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: labelstudio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres

      # SSO Configuration
      JWT_SSO_NATIVE_USER_ID_CLAIM: user_id
      JWT_SSO_COOKIE_NAME: ls_auth_token
      JWT_SSO_TOKEN_PARAM: token
      SSO_TOKEN_EXPIRY: 600
      SSO_AUTO_CREATE_USERS: true

      # Cookie Domain (for subdomain sharing)
      SESSION_COOKIE_DOMAIN: .yourdomain.com
      CSRF_COOKIE_DOMAIN: .yourdomain.com

      # Label Studio
      LABEL_STUDIO_HOST: http://localhost:8080

    ports:
      - "8080:8080"

    volumes:
      - labelstudio_data:/label-studio/data

volumes:
  labelstudio_data:
```

### 직접 빌드

```bash
# 저장소 클론
git clone https://github.com/your-org/label-studio-custom.git
cd label-studio-custom

# 이미지 빌드
docker build -t label-studio-custom:local .

# 실행
docker run -p 8080:8080 \
  -e JWT_SSO_COOKIE_NAME=ls_auth_token \
  -e SSO_AUTO_CREATE_USERS=true \
  label-studio-custom:local
```

## 환경 변수

### 필수 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DJANGO_DB` | 데이터베이스 타입 (`default` 또는 `sqlite`) | `default` |
| `POSTGRES_HOST` | PostgreSQL 호스트 | `postgres` |
| `POSTGRES_DB` | PostgreSQL 데이터베이스명 | `labelstudio` |
| `POSTGRES_USER` | PostgreSQL 사용자명 | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL 비밀번호 | - |

### SSO 설정

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `JWT_SSO_NATIVE_USER_ID_CLAIM` | JWT 토큰의 사용자 ID claim | `user_id` |
| `JWT_SSO_COOKIE_NAME` | JWT 토큰 쿠키 이름 | `ls_auth_token` |
| `JWT_SSO_TOKEN_PARAM` | JWT 토큰 URL 파라미터 | `token` |
| `SSO_TOKEN_EXPIRY` | 토큰 만료 시간(초) | `600` |
| `SSO_AUTO_CREATE_USERS` | 사용자 자동 생성 여부 | `true` |

### 쿠키 설정 (서브도메인 공유)

| 변수 | 설명 | 예시 |
|------|------|------|
| `SESSION_COOKIE_DOMAIN` | 세션 쿠키 도메인 | `.nubison.localhost` |
| `CSRF_COOKIE_DOMAIN` | CSRF 쿠키 도메인 | `.nubison.localhost` |

### 선택 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DEBUG` | 디버그 모드 | `false` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |
| `LABEL_STUDIO_HOST` | Label Studio 호스트 URL | `http://localhost:8080` |

## 커스터마이징 상세

### hideHeader 기능

URL 파라미터로 헤더를 숨길 수 있습니다:

```
http://label.yourdomain.com:8080/projects/1?hideHeader=true
```

**구현 방식**:
- `custom-templates/base.html`에서 JavaScript로 CSS 변수 강제 설정
- `--header-height: 0px` 100ms마다 5초간 적용 (React SPA 대응)

### Annotation 소유권 제어

**Permission 클래스**: `custom-permissions/permissions.py`

```python
class IsAnnotationOwnerOrReadOnly(BasePermission):
    """
    - 읽기: 모든 인증 사용자
    - 생성: 모든 인증 사용자
    - 수정/삭제: 소유자 또는 Admin만 가능
    """
```

**API Override**: `custom-api/annotations.py`

```python
class AnnotationAPI(AnnotationOwnershipMixin, BaseAnnotationAPI):
    pass
```

### SSO 인증 흐름

```
Frontend → Backend → Label Studio API
  ↓           ↓              ↓
사용자 선택  JWT 요청    JWT 토큰 발급
              ↓
          기존 세션 쿠키 삭제 (sessionid, csrftoken)
              ↓
          JWT 쿠키 설정 (ls_auth_token)
              ↓
          iframe 재생성 (:key="props.email")
              ↓
     Label Studio 첫 접근 (JWTAutoLoginMiddleware)
              ↓
          JWT 검증 → Django Session 생성
              ↓
          ls_auth_token 쿠키 자동 삭제
              ↓
          이후 모든 요청: sessionid만 사용 (빠름!)
```

**성능 최적화**:
- **첫 요청**: JWT 검증 + Session 생성 + JWT 삭제
- **이후 요청**: Session만 사용 (JWT 검증 불필요)
- **사용자 전환**: 새 JWT → iframe 재생성 → 새 Session

## 디렉토리 구조

```
label-studio-custom/
├── Dockerfile                      # 멀티스테이지 빌드
│
├── config/                         # Django 설정
│   ├── label_studio.py            # SSO 통합 설정
│   └── urls_simple.py             # URL 라우팅
│
├── custom-permissions/             # Annotation 소유권 제어
│   ├── __init__.py
│   ├── apps.py
│   ├── permissions.py
│   ├── mixins.py
│   └── tests.py
│
├── custom-api/                     # API 오버라이드
│   ├── __init__.py
│   ├── annotations.py
│   └── urls.py
│
├── custom-templates/               # 템플릿 커스터마이징
│   └── base.html                  # hideHeader 기능
│
├── scripts/                        # 초기화 스크립트
│   ├── create_initial_users.py
│   └── init_users.sh
│
├── tests/                          # 통합 테스트
│   └── test_integration.py
│
├── docs/                           # 상세 문서
│   ├── FEATURES.md
│   ├── DEPLOYMENT.md
│   └── CUSTOMIZATION_GUIDE.md
│
└── .github/workflows/              # CI/CD
    ├── build-image.yml
    └── publish-image.yml
```

## 개발 가이드

### 로컬 테스트

```bash
# docker-compose.test.yml로 테스트
docker compose -f docker-compose.test.yml up -d

# 로그 확인
docker compose -f docker-compose.test.yml logs -f labelstudio

# 테스트 실행
docker compose -f docker-compose.test.yml exec labelstudio pytest tests/
```

### 이미지 빌드 및 배포

```bash
# 이미지 빌드
docker build -t ghcr.io/aidoop/label-studio-custom:1.20.0-sso.5 .

# GitHub Container Registry 로그인
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 이미지 푸시
docker push ghcr.io/aidoop/label-studio-custom:1.20.0-sso.5

# latest 태그 추가
docker tag ghcr.io/aidoop/label-studio-custom:1.20.0-sso.5 \
           ghcr.io/aidoop/label-studio-custom:latest
docker push ghcr.io/aidoop/label-studio-custom:latest
```

## 버전 관리

### 태그 규칙

- `1.20.0-sso.1` - Label Studio 1.20.0 기반, SSO 커스터마이징 버전 1
- `1.20.0-sso.2` - Label Studio 1.20.0 기반, SSO 커스터마이징 버전 2 (bugfix)
- `1.20.0-sso.5` - Label Studio 1.20.0 기반, JWT → Session 전환 (현재 버전)
- `1.21.0-sso.1` - Label Studio 1.21.0 업그레이드 (미래)

### 브랜치 전략

- `main` - 안정 버전 (프로덕션)
- `develop` - 개발 버전
- `feature/*` - 기능 개발
- `upgrade/*` - Label Studio 업그레이드

## 샘플 애플리케이션

이 커스텀 이미지를 사용하는 샘플 애플리케이션은 [label-studio-sso-app](https://github.com/aidoop/label-studio-sso-app)을 참고하세요.

## 라이선스

MIT License

## 기여

버그 리포트 및 기능 제안은 Issues에 등록해주세요.

## 참고

- [Label Studio 공식 문서](https://labelstud.io/guide/)
- [label-studio-sso v6.0.7](https://pypi.org/project/label-studio-sso/6.0.7/)
- [Label Studio GitHub](https://github.com/HumanSignal/label-studio)
