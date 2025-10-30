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

### 4. Webhook Payload 커스터마이징

- Annotation 이벤트 webhook에 사용자 정보 자동 추가
- `completed_by_info` 필드로 사용자 상세 정보 제공
- `is_superuser` 플래그로 관리자/일반 사용자 구분
- MLOps 시스템에서 별도 API 호출 없이 사용자 정보 확인 가능

### 5. Admin User Management API

- **Superuser 생성 API**: Admin 권한으로 프로그래밍 방식으로 Superuser 생성 가능
- **Superuser 승격 API**: 기존 일반 사용자를 Superuser로 승격
- REST API 기반으로 자동화 및 스크립팅 지원
- Organization 멤버십 자동 추가 및 API 토큰 자동 생성

### 6. Project model_version 유효성 검증 우회

- **문제**: Label Studio 1.20.0에서 Project 수정 시 `model_version` 필드에 대한 과도한 검증
  - Project 생성 시: model_version 자유롭게 저장 가능 ✅
  - Project 수정 시: "Model version doesn't exist either as live model or as static predictions" 오류 ❌
- **해결**: ProjectSerializer를 커스터마이징하여 `validate_model_version` 메서드 오버라이드
- **목적**: 외부 MLOps 시스템의 모델 버전 ID를 Project에 저장하여 성능 계산 시 참조
- **효과**: PATCH `/api/projects/{id}/` 요청 시 어떤 model_version 값도 자유롭게 저장 가능

### 7. Custom Export API (MLOps 통합)

- **목적**: MLOps 시스템의 모델 학습 및 성능 계산을 위한 필터링된 Task Export
- **구현 방식**: Label Studio 1.20.0 오리지널 Serializer 사용
  - `PredictionSerializer` - 표준 prediction 형식
  - `AnnotationSerializer` - 표준 annotation 형식
  - `completed_by_info` enrichment 추가 (MLOps 커스텀)
- **주요 기능**:
  - 날짜 범위 필터링 (`task.data.source_created_dt`)
  - 모델 버전 필터링 (`prediction.model_version`)
  - 승인자 필터링 (`annotation.completed_by` - Super User만)
  - 선택적 페이징 지원 (기본: 전체 반환)
  - N+1 쿼리 최적화
- **엔드포인트**: `POST /api/custom/export/`
- **용도**: 모델 학습 데이터 수집, 모델 성능 계산
- **버전**: v1.20.0-sso.10 (최초), v1.20.0-sso.11 (오리지널 Serializer 적용)
- **문서**: [Custom Export API Guide](docs/CUSTOM_EXPORT_API_GUIDE.md)

## Quick Start

### Docker Hub에서 사용

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:13.18
    environment:
      POSTGRES_DB: labelstudio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres

  labelstudio:
    image: ghcr.io/aidoop/label-studio-custom:1.20.0-sso.18

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

| 변수                | 설명                                        | 기본값        |
| ------------------- | ------------------------------------------- | ------------- |
| `DJANGO_DB`         | 데이터베이스 타입 (`default` 또는 `sqlite`) | `default`     |
| `POSTGRE_HOST` / `POSTGRES_HOST`     | PostgreSQL 호스트 (POSTGRE_* 우선 사용)                           | `postgres`    |
| `POSTGRE_DB` / `POSTGRES_DB`       | PostgreSQL 데이터베이스명 (POSTGRE_* 우선 사용)                   | `labelstudio` |
| `POSTGRE_USER` / `POSTGRES_USER`     | PostgreSQL 사용자명 (POSTGRE_* 우선 사용)                         | `postgres`    |
| `POSTGRE_PASSWORD` / `POSTGRES_PASSWORD` | PostgreSQL 비밀번호 (POSTGRE_* 우선 사용)                         | -             |
| `POSTGRE_PORT` / `POSTGRES_PORT` | PostgreSQL 포트 (POSTGRE_* 우선 사용)                         | `5432`             |

**참고**: v1.20.0-sso.18부터 `POSTGRE_*` 환경변수를 우선적으로 사용하며, 없을 경우 `POSTGRES_*`를 폴백으로 사용합니다.

### SSO 설정

| 변수                           | 설명                       | 기본값          |
| ------------------------------ | -------------------------- | --------------- |
| `JWT_SSO_NATIVE_USER_ID_CLAIM` | JWT 토큰의 사용자 ID claim | `user_id`       |
| `JWT_SSO_COOKIE_NAME`          | JWT 토큰 쿠키 이름         | `ls_auth_token` |
| `JWT_SSO_TOKEN_PARAM`          | JWT 토큰 URL 파라미터      | `token`         |
| `SSO_TOKEN_EXPIRY`             | 토큰 만료 시간(초)         | `600`           |
| `SSO_AUTO_CREATE_USERS`        | 사용자 자동 생성 여부      | `true`          |

### 쿠키 설정 (서브도메인 공유)

| 변수                    | 설명             | 예시                 |
| ----------------------- | ---------------- | -------------------- |
| `SESSION_COOKIE_DOMAIN` | 세션 쿠키 도메인 | `.nubison.localhost` |
| `CSRF_COOKIE_DOMAIN`    | CSRF 쿠키 도메인 | `.nubison.localhost` |

### iframe 임베딩 보안 헤더 설정

| 변수                      | 설명                                  | 기본값 | 예시                                                    |
| ------------------------- | ------------------------------------- | ------ | ------------------------------------------------------- |
| `CSP_FRAME_ANCESTORS`     | CSP frame-ancestors 설정 (권장)      | 없음   | `'self' https://console-dev.nubison.io`                 |
| `CONTENT_SECURITY_POLICY` | 전체 CSP 정책 설정 (고급)            | 없음   | `frame-ancestors 'self' https://console.nubison.io;`    |
| `X_FRAME_OPTIONS`         | X-Frame-Options 설정 (구형 브라우저) | 없음   | `DENY`, `SAMEORIGIN`, `ALLOW-FROM https://example.com` |

**권장 설정 (Content-Security-Policy):**

```yaml
environment:
  # 특정 도메인만 iframe 허용 (권장)
  CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io https://console.nubison.io"

  # 구형 브라우저 지원 (폴백)
  X_FRAME_OPTIONS: "SAMEORIGIN"
```

**사용 예시:**

```yaml
# 개발 환경 - 여러 도메인 허용
environment:
  CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io http://localhost:4000"
  X_FRAME_OPTIONS: "SAMEORIGIN"

# 운영 환경 - 프로덕션 도메인만 허용
environment:
  CSP_FRAME_ANCESTORS: "'self' https://console.nubison.io"
  X_FRAME_OPTIONS: "SAMEORIGIN"

# 테스트 환경 - 모든 도메인 허용 (비권장)
environment:
  CSP_FRAME_ANCESTORS: "*"
  # 또는
  X_FRAME_OPTIONS: SAMEORIGIN  # 같은 도메인에서만 허용
```

### 선택 환경 변수

| 변수                | 설명                    | 기본값                  |
| ------------------- | ----------------------- | ----------------------- |
| `DEBUG`             | 디버그 모드             | `false`                 |
| `LOG_LEVEL`         | 로그 레벨               | `INFO`                  |
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

### Webhook Payload 커스터마이징

Label Studio의 webhook payload에 **사용자 상세 정보**를 자동으로 추가합니다.

#### 구현 방식

**patch_webhooks.py 스크립트**가 Docker 빌드 시 Label Studio 소스 코드를 직접 패치:

```dockerfile
COPY patch_webhooks.py /tmp/patch_webhooks.py
RUN python3 /tmp/patch_webhooks.py
```

- **패치 대상**: `label_studio/webhooks/utils.py` → `run_webhook_sync()` 함수
- **추가 필드**: `annotation.completed_by_info`
- **적용 이벤트**: `ANNOTATION_CREATED`, `ANNOTATION_UPDATED`, `ANNOTATIONS_DELETED`

#### Payload 비교

**기본 Label Studio**:

```json
{
  "action": "ANNOTATION_CREATED",
  "annotation": {
    "id": 17,
    "completed_by": 1, // ID만 제공
    "task": 19
  }
}
```

**패치 적용 후**:

```json
{
  "action": "ANNOTATION_CREATED",
  "annotation": {
    "id": 17,
    "completed_by": 1,
    "completed_by_info": {
      // ✨ 자동 추가
      "id": 1,
      "email": "user@example.com",
      "username": "user1",
      "is_superuser": false
    },
    "task": 19
  }
}
```

#### MLOps 활용 예시

```python
# Superuser만 모델 성능 측정에 사용
def handle_annotation_webhook(request):
    payload = request.json
    user_info = payload['annotation'].get('completed_by_info', {})

    if user_info.get('is_superuser'):
        # Superuser annotation은 처리
        calculate_model_performance(payload)
    else:
        # Regular user annotation은 무시
        return {"status": "skipped"}
```

**주요 이점**:

- ✅ **API 호출 불필요**: User 정보가 payload에 포함
- ✅ **실시간 필터링**: superuser 여부로 즉시 구분
- ✅ **성능 향상**: 별도 네트워크 요청 없음

### Admin User Management API

Label Studio의 기본 API로는 보안상 이유로 superuser를 생성할 수 없습니다. 이 커스텀 이미지는 Admin 권한을 가진 사용자만 접근 가능한 Superuser 관리 API를 제공합니다.

#### 1. Superuser 생성

**Endpoint**: `POST /api/admin/users/create-superuser`

**권한**: Admin 사용자만 접근 가능 (IsAdminUser)

**Request Body**:

```json
{
  "email": "newadmin@example.com",
  "password": "secure_password123",
  "username": "newadmin", // optional, defaults to email
  "first_name": "Admin", // optional
  "last_name": "User", // optional
  "create_token": true, // optional, defaults to true
  "add_to_organization": 1 // optional, organization ID
}
```

**Response**:

```json
{
  "success": true,
  "user": {
    "id": 4,
    "email": "newadmin@example.com",
    "username": "newadmin",
    "first_name": "Admin",
    "last_name": "User",
    "is_superuser": true,
    "is_staff": true,
    "is_active": true
  },
  "token": "58d3d3017db87d056db45620160c329c5a40b21d",
  "organization": {
    "id": 1,
    "title": "Default Organization"
  }
}
```

**사용 예시**:

```bash
curl -X POST "http://labelstudio.yourdomain.com/api/admin/users/create-superuser" \
  -H "Authorization: Token YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newadmin@example.com",
    "password": "secure_password123",
    "first_name": "New",
    "last_name": "Admin",
    "create_token": true,
    "add_to_organization": 1
  }'
```

#### 2. 기존 사용자를 Superuser로 승격

**Endpoint**: `POST /api/admin/users/<user_id>/promote-to-superuser`

**권한**: Admin 사용자만 접근 가능 (IsAdminUser)

**Response**:

```json
{
  "success": true,
  "user": {
    "id": 2,
    "email": "user@example.com",
    "username": "user",
    "is_superuser": true,
    "is_staff": true
  }
}
```

**사용 예시**:

```bash
curl -X POST "http://labelstudio.yourdomain.com/api/admin/users/2/promote-to-superuser" \
  -H "Authorization: Token YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

#### 3. Superuser 권한 해제

**Endpoint**: `POST /api/admin/users/<user_id>/demote-from-superuser`

**권한**: Admin 사용자만 접근 가능 (IsAdminUser)

**Response**:

```json
{
  "success": true,
  "user": {
    "id": 3,
    "email": "user@example.com",
    "username": "user",
    "is_superuser": false,
    "is_staff": false
  }
}
```

**사용 예시**:

```bash
curl -X POST "http://labelstudio.yourdomain.com/api/admin/users/3/demote-from-superuser" \
  -H "Authorization: Token YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

**보안 기능**:

- ⚠️ **자기 자신 해제 불가**: 자신의 Superuser 권한은 해제할 수 없음
- ✅ **실수 방지**: 마지막 Admin이 실수로 권한을 잃는 것을 방지

**활용 시나리오**:

- CI/CD 파이프라인에서 자동으로 Admin 계정 생성
- 프로비저닝 스크립트에서 초기 사용자 설정
- 사용자 관리 자동화 워크플로우
- Infrastructure as Code (IaC) 통합

### Project model_version 수정 API

외부 MLOps 시스템의 모델 버전 정보를 Project에 저장하여 모델 성능 계산 시 참조할 수 있습니다.

#### 문제 상황 (Label Studio 1.20.0 기본 동작)

**Project 생성 시**: ✅ 정상 작동

```bash
curl -X POST "http://localhost:8080/api/projects/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Project",
    "model_version": "aiver03"
  }'
```

**Project 수정 시**: ❌ 오류 발생

```bash
curl -X PATCH "http://localhost:8080/api/projects/11/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_version": "aiver03"
  }'

# 응답:
{
  "id": "e1d51fd6-64ec-4365-9989-3a43b0e94bce",
  "status_code": 400,
  "version": "1.20.0",
  "detail": "Validation error",
  "exc_info": null,
  "validation_errors": {
    "model_version": [
      "Model version doesn't exist either as live model or as static predictions."
    ]
  }
}
```

#### 해결 방법 (커스텀 이미지)

이 커스텀 이미지는 `ProjectSerializer`의 `validate_model_version` 메서드를 오버라이드하여 검증을 우회합니다.

**Project 수정 시**: ✅ 정상 작동

```bash
curl -X PATCH "http://localhost:8080/api/projects/11/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_version": "aiver03"
  }'

# 응답:
{
  "id": 11,
  "title": "My Project",
  "model_version": "aiver03",
  ...
}
```

**주요 이점**:

- ✅ **일관된 동작**: 생성과 수정 시 동일한 규칙 적용
- ✅ **외부 시스템 연동**: Label Studio에 없는 모델 버전 ID도 저장 가능
- ✅ **MLOps 통합**: 모델 성능 추적 시 Project 단위 버전 관리

**활용 시나리오**:

```python
# MLOps 시스템에서 모델 학습 완료 후 Project에 버전 기록
import requests

def update_project_model_version(project_id: int, model_version: str):
    """모델 학습 완료 후 Label Studio Project에 버전 정보 업데이트"""
    response = requests.patch(
        f"http://labelstudio.example.com/api/projects/{project_id}/",
        headers={"Authorization": f"Token {LABELSTUDIO_TOKEN}"},
        json={"model_version": model_version}
    )
    return response.json()

# 모델 학습 파이프라인
train_model()  # 모델 학습
model_version = "aiver04"  # 새 버전
update_project_model_version(project_id=11, model_version=model_version)
```

**구현 상세**:

- **파일**: `custom-api/projects.py`
- **방식**: `ProjectSerializer` 상속 후 `validate_model_version()` 오버라이드
- **URL**: `api/projects/<int:pk>/` (Label Studio 기본 URL과 동일)
- **우선순위**: `config/urls_simple.py`에서 `projects.urls`보다 먼저 등록하여 오버라이드

## 디렉토리 구조

```
label-studio-custom/
├── Dockerfile                      # 멀티스테이지 빌드
├── Makefile                        # 개발/테스트 편의 명령어
├── docker-compose.test.yml         # 테스트 환경 설정
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
│   └── tests.py                   # 권한 관련 테스트
│
├── custom-api/                     # API 오버라이드 및 확장
│   ├── __init__.py
│   ├── export.py                  # Custom Export API
│   ├── export_serializers.py      # Export Serializers
│   ├── annotations.py             # Annotation 소유권 API
│   ├── projects.py                # Project model_version 검증 우회
│   ├── admin_users.py             # Admin User Management API
│   ├── tests.py                   # API 테스트 (17개)
│   └── urls.py
│
├── custom-templates/               # 템플릿 커스터마이징
│   └── base.html                  # hideHeader 기능
│
├── scripts/                        # 스크립트 모음
│   ├── patch_webhooks.py          # Webhook payload enrichment 패치
│   ├── run_tests.sh               # 전체 테스트 실행
│   ├── run_quick_test.sh          # 빠른 테스트 실행
│   ├── create_initial_users.py    # 초기 사용자 생성
│   └── init_users.sh              # 사용자 초기화
│
├── docs/                           # 상세 문서
│   ├── CUSTOM_EXPORT_API_GUIDE.md # Custom Export API 가이드
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

#### Makefile 사용 (권장)

```bash
# 사용 가능한 명령어 확인
make help

# 전체 테스트 실행 (환경 시작부터)
make test

# 환경이 이미 실행 중일 때 빠른 테스트
make test-quick

# 특정 테스트만 실행
make test-date      # 날짜 필터 테스트
make test-timezone  # 타임존 테스트
make test-kst       # KST 타임존 테스트

# Docker 관리
make up             # 환경 시작
make down           # 환경 중지
make logs           # 로그 확인
make clean          # 모든 컨테이너/볼륨 삭제
```

#### 직접 실행

```bash
# 전체 테스트 실행
bash scripts/run_tests.sh

# 특정 테스트만 실행
bash scripts/run_quick_test.sh test_export_with_date_filter

# 모든 테스트 목록 확인
bash scripts/run_quick_test.sh
```

#### 수동 테스트

```bash
# 환경 시작
docker compose -f docker-compose.test.yml up -d

# 로그 확인
docker compose -f docker-compose.test.yml logs -f labelstudio

# 테스트 실행
docker compose -f docker-compose.test.yml exec labelstudio \
  bash -c "cd /label-studio/label_studio && python manage.py test custom_api.tests.CustomExportAPITest --verbosity=2"
```

### 이미지 빌드 및 배포

```bash
# 이미지 빌드
docker build -t ghcr.io/aidoop/label-studio-custom:1.20.0-sso.11 .

# GitHub Container Registry 로그인
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 이미지 푸시
docker push ghcr.io/aidoop/label-studio-custom:1.20.0-sso.11

# latest 태그 추가
docker tag ghcr.io/aidoop/label-studio-custom:1.20.0-sso.11 \
           ghcr.io/aidoop/label-studio-custom:latest
docker push ghcr.io/aidoop/label-studio-custom:latest
```

## 버전 관리

### 태그 규칙

- `1.20.0-sso.1` - Label Studio 1.20.0 기반, SSO 커스터마이징 버전 1
- `1.20.0-sso.2` - Label Studio 1.20.0 기반, SSO 커스터마이징 버전 2 (bugfix)
- `1.20.0-sso.11` - Label Studio 1.20.0 기반, Custom Export API 오리지널 Serializer 적용 (현재 버전)
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
