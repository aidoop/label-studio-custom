# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.20.0-sso.35] - 2025-11-14

### Fixed

#### User Deletion API
- **문제**: 사용자 삭제 시 "Method DELETE not allowed" 오류 발생
- **원인**: v1.20.0-sso.19에서 추가된 `custom-api/users.py`가 GET, PATCH만 구현하여 DELETE 메서드가 누락됨
- **수정**:
  - `@api_view` 데코레이터에 DELETE 추가
  - DELETE 메서드 구현:
    - 관리자 전용 권한 (admin-only)
    - 자기 자신 삭제 방지 (self-deletion prevention)
    - HTTP 204 No Content 응답
- **영향**: 사용자 삭제 기능 복원
- **파일**: `custom-api/users.py` (lines 36, 96-115)

## [1.20.0-sso.34] - 2025-11-14

### Added

#### AIV Prefix for Prediction Model Version
- **목적**: UI에서 AI 예측 기반 annotation과 사용자 직접 annotation을 시각적으로 구별
- **기능**:
  - Prediction 조회 시 `model_version` 필드에 "AIV " 프리픽스 자동 추가
  - 예: `"model_version": "139"` → `"model_version": "AIV 139"`
  - UI 표시: "139 #1" → "AIV 139 #1"
- **구현 방식**: Backend Serializer Override
  ```python
  # PredictionSerializer.to_representation() 오버라이드
  def to_representation(self, instance):
      ret = super().to_representation(instance)
      if ret.get('model_version'):
          ret['model_version'] = f"AIV {ret['model_version']}"
      return ret
  ```
- **영향 범위**:
  - ✅ GET 요청 (조회): API 응답에 "AIV " 프리픽스 추가
  - ❌ POST/PUT/PATCH (생성/수정): 데이터베이스에는 원본 그대로 저장
  - ❌ 데이터베이스: 실제 저장된 값은 변경 없음 (display-only)
- **잠재적 영향**:
  - Export: JSON/CSV export 시 "AIV " 프리픽스 포함될 수 있음
  - API 클라이언트: 외부 시스템이 model_version 값을 파싱하는 경우 영향 받을 수 있음
- **파일**:
  - `scripts/patch_prediction_serializer.py` (새로 추가)
  - `Dockerfile` (line 39-41: 패치 스크립트 실행)

### Technical Details

- **패치 적용 시점**: Docker 이미지 빌드 시 자동 실행
- **패치 대상**: `/label-studio/label_studio/tasks/serializers.py`
- **패치 방법**: `PredictionSerializer` 클래스에 `to_representation()` 메서드 추가
- **중복 패치 방지**: "AIV prefix patch" 주석으로 이미 패치된 경우 건너뛰기

## [1.20.0-sso.33] - 2025-11-13

### Fixed

#### Media Upload - Array and File Object Handling
- **문제**: 프론트엔드에서 배열 형식 및 File 객체로 전송된 media가 처리되지 않음
- **해결**: 배열 및 File 객체 형식 모두 처리하도록 수정
- **파일**: `custom-api/media.py`

## [1.20.0-sso.32] - 2025-11-07

### Changed

#### Version API - Release Field Override
- **목적**: UI에서 커스텀 버전이 표시되도록 `release` 필드 자체를 오버라이드
- **문제**:
  - v1.20.0-sso.31에서 `custom_version` 필드만 추가했으나 UI는 `release` 필드를 읽음
  - 결과: UI 하단에 "v1.20.0"으로 표시 (커스텀 버전 미표시)
- **해결**:
  - `/api/version` 응답에서 `release` 필드를 커스텀 버전으로 오버라이드
  - 원본 버전은 `base_release` 필드에 백업
- **구현**:
  ```python
  # custom-api/version.py
  base_response['base_release'] = base_response.get('release', '1.20.0')  # 백업
  base_response['release'] = custom_version  # 오버라이드 (UI에서 사용)
  base_response['custom_version'] = custom_version  # 추가 필드 (API용)
  ```
- **결과**:
  - UI 하단: "v1.20.0-sso.32" 표시 예상
  - API 응답: `release`, `custom_version`, `base_release` 모두 포함

### Technical Details

- **파일**: `custom-api/version.py` (CustomVersionAPI.get)
- **API Response**:
  ```json
  {
    "release": "1.20.0-sso.32",
    "base_release": "1.20.0",
    "custom_version": "1.20.0-sso.32",
    "custom_edition": "Community + SSO Custom"
  }
  ```
- **하위 호환성**: `custom_version` 필드도 유지하여 이전 로직과 호환

## [1.20.0-sso.31] - 2025-11-07

### Changed

#### Admin User Creation - Auto Organization Assignment
- **목적**: 사용자 생성 시 자동으로 생성자의 organization에 추가
- **문제 해결**:
  - 기존: `add_to_organization` 파라미터를 명시하지 않으면 organization 미할당
  - 결과: active_organization이 null이 되어 로그인 불가
  - 개선: 생성자의 active_organization을 기본값으로 사용
- **구현 방식**: CreateSuperuserAPI 수정
  ```python
  # custom-api/admin_users.py
  org_id = request.data.get('add_to_organization')

  # 기본값: 생성자의 active_organization 사용
  if org_id is None and request.user.active_organization:
      org_id = request.user.active_organization.id
  ```
- **동작 방식**:
  - `add_to_organization` 미지정 → 생성자의 organization에 자동 추가
  - `add_to_organization: 5` 지정 → Organization 5에 추가 (명시적 지정 우선)
  - 생성자가 organization 없음 → 추가 안 됨 (기존 동작 유지)
- **장점**:
  - Multi-tenancy 친화적 (같은 팀에 자동 추가)
  - 로그인 불가 문제 방지
  - 다른 organization에 추가하려면 명시적 지정 필요 (보안 강화)

### Technical Details

- **파일**: `custom-api/admin_users.py` (CreateSuperuserAPI.post)
- **Signal 연동**: Organization 추가 시 active_organization 자동 설정 (v1.20.0-sso.27)
- **하위 호환성**: 명시적으로 지정한 경우 기존 동작 유지

## [1.20.0-sso.30] - 2025-11-07

### Added

#### Custom Version API Override
- **목적**: UI에서 커스텀 버전 정보 표시 (v1.20.0-sso.30 등)
- **문제 해결**:
  - 기존: Label Studio UI는 기본 버전만 표시 (v1.20.0)
  - 개선: 커스텀 빌드 버전 및 추가 기능 정보 표시
- **구현 방식**: `/api/version` API 오버라이드
  ```python
  # GET /api/version
  class CustomVersionAPI(APIView):
      permission_classes = []  # Public API

      def get(self, request):
          # 기존 Label Studio 버전 정보 가져오기
          # 커스텀 필드 추가
          base_response['custom_version'] = '1.20.0-sso.30'
          base_response['custom_edition'] = 'Community + SSO Custom'
          base_response['custom_features'] = [...]
  ```
- **주요 기능**:
  - 기존 Label Studio 버전 정보 유지
  - 커스텀 버전, 에디션, 릴리스 날짜 추가
  - 커스텀 기능 목록 표시
  - JSON 및 HTML 응답 지원
- **파일**:
  - `custom-api/version.py` (CustomVersionAPI 신규 추가)
  - `custom-api/urls.py` (version URL 패턴 등록)
  - `config/urls_simple.py` (API 오버라이드 설정)
- **환경 변수**:
  - `CUSTOM_VERSION`: 커스텀 버전 번호 (기본값: 1.20.0-sso.30)
  - `CUSTOM_RELEASE_DATE`: 릴리스 날짜 (기본값: 2025-11-07)

### Technical Details

- **URL 라우팅**: urls_simple.py에서 기본 version URL보다 먼저 등록
- **하위 호환성**: 기존 Label Studio 버전 정보 모두 포함
- **API 응답 예시**:
  ```json
  {
    "release": "1.20.0",
    "custom_version": "1.20.0-sso.30",
    "custom_edition": "Community + SSO Custom",
    "custom_release_date": "2025-11-07",
    "custom_features": [
      "Admin User List API with Superuser Info",
      "Admin User Management (Create/Promote/Demote Superuser)",
      "Active Organization Signal (Auto-set on membership)",
      "Custom Export API with Date Filtering",
      "SSO Token Validation API",
      "Custom SSO Login Page for iframe",
      "Enhanced Security (CSRF, CSP, X-Frame-Options)"
    ]
  }
  ```

## [1.20.0-sso.29] - 2025-11-07

### Added

#### Admin User List API with Superuser Information
- **목적**: 사용자 목록 조회 시 is_superuser 필드 포함
- **문제 해결**:
  - 기존: Label Studio 기본 `/api/users/` API는 보안상 is_superuser 필드를 null로 반환
  - 문제점: 테스트 환경에서 사용자 목록 조회 시 superuser 여부 확인 불가
- **구현 방식**: Custom Admin API 추가
  ```python
  # GET /api/admin/users/list
  class ListUsersAPI(APIView):
      permission_classes = [IsAdminUser]

      def get(self, request):
          users = User.objects.all().order_by('-id')
          # is_superuser, is_staff, is_active 등 포함
  ```
- **주요 기능**:
  - Admin 권한 사용자만 접근 가능
  - 모든 사용자 정보 조회 (is_superuser, is_staff, is_active 포함)
  - active_organization ID 반환 (ForeignKey를 int로 변환)
- **파일**:
  - `custom-api/admin_users.py` (ListUsersAPI 추가)
  - `custom-api/urls.py` (URL 패턴 등록)

### Fixed

#### Active Organization Serialization Error
- JSON 직렬화 시 ForeignKey 객체를 int로 변환하도록 수정
- 500 에러 방지

### Technical Details

- **권한 체크**: IsAdminUser permission class 사용
- **정렬**: 최신 사용자부터 조회 (order_by('-id'))
- **응답 형식**:
  ```json
  {
    "success": true,
    "count": 10,
    "users": [
      {
        "id": 1,
        "email": "user@example.com",
        "is_superuser": true,
        "is_staff": true,
        "active_organization": 1
      }
    ]
  }
  ```

## [1.20.0-sso.27] - 2025-11-07

### Added

#### Automatic active_organization Setting via Django Signals
- **목적**: 사용자가 Organization에 추가될 때 active_organization 자동 설정
- **문제 해결**:
  - 기존: 사용자가 Organization에 추가되어도 active_organization은 None
  - 문제점: active_organization이 None인 사용자가 다른 사용자를 생성하려고 하면 500 에러 발생
    ```python
    # /label-studio/label_studio/users/api.py
    def perform_create(self, serializer):
        instance = serializer.save()
        self.request.user.active_organization.add_user(instance)  # active_organization이 None이면 에러
    ```
- **구현 방식**: Django Signal을 사용한 자동화
  ```python
  @receiver(post_save, sender=OrganizationMember)
  def set_active_organization_on_membership(sender, instance, created, **kwargs):
      if created and instance.user.active_organization is None:
          instance.user.active_organization = instance.organization
          instance.user.save(update_fields=['active_organization'])
  ```
- **주요 기능**:
  - OrganizationMember 생성 시 자동으로 active_organization 설정
  - 이미 active_organization이 있는 경우는 변경하지 않음
  - 수동 설정 없이 완전 자동화
- **영향**:
  - API로 사용자 생성 시 더 이상 500 에러 발생하지 않음
  - 사용자 경험 개선 (수동 설정 불필요)
  - 데이터 일관성 향상
- **파일**:
  - `custom-api/signals.py` (새로 추가)
  - `custom-api/apps.py` (새로 추가 - Signal 등록)
  - `config/label_studio.py` (CustomApiConfig 등록)
  - `Dockerfile` (버전 업데이트: 1.20.0-sso.27)

### Technical Details

- **Signal 등록**: AppConfig의 `ready()` 메서드에서 자동 로드
- **로깅**: active_organization 설정 시 INFO 레벨 로그 출력
- **성능**: post_save 시그널이므로 최소한의 오버헤드
- **안전성**: 이미 active_organization이 있는 경우 건너뛰어 기존 설정 보호

## [1.20.0-sso.26] - 2025-11-07

### Changed

#### Simplified SSO Architecture - Removed Custom SSO API
- **목적**: 중복 코드 제거 및 아키텍처 단순화
- **변경 내용**:
  - `custom-api/sso.py` 파일 제거 (Custom SSO Token Validation API)
  - `label-studio-sso` v6.0.8로 업그레이드
  - 기본 SSO API(`/api/sso/token`) 사용으로 통합
- **이유**:
  - `label-studio-sso`도 우리가 관리하는 저장소
  - Custom API를 별도로 만들 필요 없이 직접 수정 가능
  - 중복 코드 제거로 유지보수성 향상
- **Breaking Changes**:
  - Custom SSO API 엔드포인트 제거:
    - ~~`POST /api/custom/sso/token`~~ → `POST /api/sso/token`
    - ~~`POST /api/custom/sso/batch-token`~~ (제거)
  - 클라이언트는 `/api/sso/token` 엔드포인트 사용 필요

### Dependencies

- **label-studio-sso**: 6.0.7 → 6.0.8
  - `SSO_AUTO_CREATE_USERS` 기능 완전 제거
  - 사용자가 없으면 422 에러 반환 (JSON)
  - Django DEBUG=False에서도 정상 동작

## [1.20.0-sso.25] - 2025-11-07

### Fixed

#### Custom SSO Token API - DEBUG=False 환경에서 JSON 응답 오류 수정
- **문제**: `DEBUG=False` 환경에서 사용자 미존재 시 HTML 404 페이지가 반환됨
  - Custom SSO Token API가 JSON을 반환해야 하는데 Django가 HTML로 변환
  - 프로덕션 환경(`DEBUG=False`)에서만 발생
- **원인**: Django가 HTTP 404 응답을 가로채서 HTML 템플릿으로 렌더링
- **수정**: HTTP 상태 코드를 404 → 422 Unprocessable Entity로 변경
  - Django는 404만 HTML로 변환하고, 422는 정상적으로 JSON 반환
  - 의미적으로도 적합: "요청은 이해했지만 처리할 수 없음 (사용자 없음)"
- **파일**: `custom-api/sso.py` (line 144)
- **테스트**:
  ```bash
  # 존재하지 않는 사용자 (422) - JSON 반환
  curl -X POST 'http://localhost:8080/api/custom/sso/token' \
    -H 'Authorization: Token YOUR_TOKEN' \
    -H 'Content-Type: application/json' \
    -d '{"email":"nonexistent@example.com"}'

  # 응답 (422): {"success": false, "error": "User not found: ...", "error_code": "USER_NOT_FOUND"}
  ```

## [1.20.0-sso.24] - 2025-11-07

### Changed

#### SSO_AUTO_CREATE_USERS 기능 제거
- **목적**: Custom SSO Token Validation API 사용으로 불필요
- **변경 내용**:
  - `SSO_AUTO_CREATE_USERS` 환경변수 제거
  - `config/label_studio.py`에서 `False`로 고정
  - 사전 등록된 사용자만 접근 가능 (폐쇄형 시스템)
- **이유**:
  - Custom SSO Token API는 사용자 존재 여부를 먼저 검증
  - 사용자가 없으면 `USER_NOT_FOUND` 에러 반환
  - 자동 생성 기능이 의미 없어짐
- **영향**: 기본 SSO API(`/api/sso/token`)를 직접 사용하는 경우에만 영향

## [1.20.0-sso.23] - 2025-11-07

### Added

#### Custom SSO Token Validation API
- **목적**: 존재하지 않는 사용자에 대한 JWT 토큰 발급 방지 및 사전 검증
- **문제 해결**:
  - 기본 SSO API는 `SSO_AUTO_CREATE_USERS=true` 시 존재하지 않는 사용자도 자동 생성
  - 폐쇄형 시스템에서는 사전 등록된 사용자만 접근 허용 필요
- **주요 기능**:
  - **사전 사용자 검증**: 토큰 발급 전 사용자 존재 여부 확인
  - **명확한 에러 코드**: `USER_NOT_FOUND` (404), `USER_INACTIVE` (403), `INVALID_REQUEST` (400)
  - **배치 처리**: 여러 사용자에 대한 토큰 일괄 발급
  - **Admin 전용**: `IsAdminUser` 권한으로 보안 강화
- **엔드포인트**:
  - `POST /api/custom/sso/token` - 단일 사용자 토큰 발급 (사용자 검증 포함)
  - `POST /api/custom/sso/batch-token` - 여러 사용자 일괄 토큰 발급
- **파일**:
  - `custom-api/sso.py` (새로 추가)
  - `custom-api/urls.py` (엔드포인트 등록)
  - `custom-api/tests.py` (24개 테스트 케이스 추가)
  - `docs/CUSTOM_SSO_TOKEN_API.md` (완전한 API 가이드)
  - `Makefile` (test-sso 명령어 추가)

#### SSO 전용 로그인 페이지
- **목적**: iframe 통합 시 Label Studio 직접 로그인 차단, SSO 전용 접근 유도
- **문제 해결**: iframe에서 잘못된 JWT 토큰 사용 시 일반 로그인 폼 대신 SSO 안내 페이지 표시
- **주요 기능**:
  - **iframe 환경** (`?hideHeader=true`): SSO 전용 안내 페이지 표시
    - postMessage로 부모 창에 인증 오류 알림
    - 간단한 메시지와 iframe 특화 UI
  - **일반 브라우저**: 원래 Label Studio 로그인 폼 (이메일/비밀번호)
  - 자동 환경 감지, 추가 설정 불필요
- **파일**:
  - `custom-templates/sso_login.html` (새로 추가)
  - `custom-api/sso_views.py` (새로 추가)
  - `config/urls_simple.py` (`/user/login/` URL 오버라이드)

### Changed

#### 코드 품질 개선
- **하드코딩 제거**: lambda __import__ 방식 → 정상 import 방식으로 변경
- **범용성 향상**: 특정 회사명 제거, 범용적인 설명으로 변경
- **단순화**: 불필요한 환경변수 및 복잡한 로직 제거

## [1.20.0-sso.22] - 2025-11-04

### Added

#### Custom Export API - 동적 날짜 필드 필터링
- **목적**: `task.data` JSONB 필드 내의 다양한 날짜 필드로 검색 가능하도록 개선
- **기능**:
  - 새로운 파라미터: `search_date_field` (옵션, 기본값: `source_created_at`)
  - `task.data` 내의 모든 날짜 필드명 지정 가능
  - 예: `mesure_at` (센서 계측일시), `original_created_at` (원본 생성일) 등
- **하위 호환성**: `search_date_field` 생략 시 기존 동작 유지 (`source_created_at` 사용)
- **보안**:
  - SQL Injection 방지: 정규식 검증 (`^[a-zA-Z_][a-zA-Z0-9_]*$`)
  - 필드명 길이 제한 (최대 64자)
  - 파라미터화된 쿼리로 이중 방어
- **파일**:
  - `custom-api/export_serializers.py` (line 36-67)
  - `custom-api/export.py` (line 81, 101, 140-180)
  - `docs/CUSTOM_EXPORT_API_GUIDE.md` (업데이트)
  - `README.md` (업데이트)

### Changed

#### Custom Export API 보안 강화
- **변경**: SQL Injection 취약점 제거
- **이전**: f-string으로 필드명 직접 삽입 (`f"(data->>'{search_date_field}') >= %s"`)
- **현재**: 파라미터화된 쿼리 (`where=["(data->>%s) >= %s"]`, `params=[search_date_field, ...]`)
- **효과**: SQL Injection 공격 원천 차단

## [1.20.0-sso.21] - 2025-10-31

### Fixed

#### Custom Export API 날짜 필터링 수정
- **문제**: `source_created_at` 필드로 날짜 필터링이 동작하지 않음
- **원인**:
  - 코드는 `source_created_dt` 필드를 검색했으나 실제 데이터는 `source_created_at` 사용
  - 타임존을 고려한 복잡한 비교 로직으로 인한 혼란
- **수정**:
  - 필드명을 `source_created_dt` → `source_created_at`으로 통일
  - 타임존 고려 제거, 단순 문자열 비교로 변경
  - `::timestamptz` 캐스팅 제거하고 `YYYY-MM-DD HH:MI:SS` 형식 문자열 직접 비교
- **영향**: Custom Export API의 날짜 범위 필터링 정상 동작
- **파일**:
  - `custom-api/export.py` (line 36, 144-145, 155-170)
  - `custom-api/export_serializers.py` (line 27, 33)

## [1.20.0-sso.20] - 2025-10-31

### Fixed

#### ModuleNotFoundError 수정
- **문제**: v1.20.0-sso.19에서 `ModuleNotFoundError: No module named 'config'` 발생
- **원인**:
  - `config/security_middleware.py` 파일이 Dockerfile에서 컨테이너로 복사되지 않음
  - `config/label_studio.py`에서 `config.security_middleware` 모듈을 import하려고 시도
- **수정**:
  - Dockerfile에 `COPY config/security_middleware.py /label-studio/label_studio/core/settings/security_middleware.py` 추가
  - `config/label_studio.py`의 import 경로를 `config.security_middleware` → `core.settings.security_middleware`로 수정
- **영향**: Label Studio 컨테이너가 정상적으로 시작되지 못하는 치명적 버그 해결
- **파일**:
  - `Dockerfile` (line 25)
  - `config/label_studio.py` (line 216-217)

## [1.20.0-sso.19] - 2025-10-30

### Added

#### Content-Security-Policy 환경변수 지원
- **목적**: iframe 임베딩 보안 헤더를 환경변수로 유연하게 설정
- **기능**:
  - `CSP_FRAME_ANCESTORS` - CSP frame-ancestors 간편 설정 (권장)
  - `CONTENT_SECURITY_POLICY` - 전체 CSP 정책 고급 설정
  - `X_FRAME_OPTIONS` - X-Frame-Options 설정 (구형 브라우저 지원)
- **특징**:
  - 서버(nginx) 설정이 우선 적용됨 (이중 설정 방지)
  - 최신 브라우저는 CSP 우선, 구형 브라우저는 X-Frame-Options 사용
  - 개발/운영 환경별 설정 가능
- **사용 예시**:
  ```yaml
  CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io https://console.nubison.io"
  X_FRAME_OPTIONS: "SAMEORIGIN"
  ```
- **파일**:
  - `config/security_middleware.py` (신규)
  - `config/label_studio.py` (line 208-253)
  - `docs/IFRAME_SECURITY_HEADERS.md` (신규)

#### 누비슨 시스템 연동 지원
- **목적**: 누비슨 시스템의 이메일 관리 정책과 Label Studio 연동
- **문제**: 누비슨은 서비스별로 같은 이메일 사용 가능, Label Studio는 이메일 unique 제약
- **해결**: 이메일 포맷팅 방식 (`{서비스ID}_{이메일}`)
- **기능**:
  - User Update API - 이메일 수정 가능
  - User 조회 API (이메일 기반)
  - JWT는 user_id 기반이라 이메일 변경과 무관
- **API 엔드포인트**:
  - `PATCH /api/users/{id}/` - User 정보 업데이트 (이메일 수정 가능)
  - `GET /api/users/by-email/?email={email}` - 이메일로 User 조회
- **파일**:
  - `custom-api/users.py` (신규)
  - `custom-api/urls.py` (업데이트)
  - `docs/NUBISON_INTEGRATION_GUIDE.md` (신규)

### Changed

#### iframe 보안 헤더 설정 개선
- X-Frame-Options 설정을 더 유연하게 개선
- Django 기본 XFrameOptionsMiddleware를 커스텀 미들웨어로 대체
- 환경변수 미설정 시 헤더를 추가하지 않음 (기존: 자동 허용)

## [1.20.0-sso.18] - 2025-10-30

### Changed

#### PostgreSQL 환경변수명 유연화
- **목적**: 개발서버와 운영서버의 환경변수명 차이로 인한 배포 시 코드 수정 문제 해결
- **변경 사항**:
  - `POSTGRE_*` 환경변수를 우선적으로 사용
  - 기존 `POSTGRES_*` 환경변수도 폴백으로 지원 (하위 호환성 유지)
- **지원 환경변수**:
  - `POSTGRE_DB` (폴백: `POSTGRES_DB`)
  - `POSTGRE_USER` (폴백: `POSTGRES_USER`)
  - `POSTGRE_PASSWORD` (폴백: `POSTGRES_PASSWORD`)
  - `POSTGRE_HOST` (폴백: `POSTGRES_HOST`)
  - `POSTGRE_PORT` (폴백: `POSTGRES_PORT`)
- **효과**:
  - 쿠버네티스 환경변수 변경 없이 `POSTGRE_*` 변수 사용 가능
  - 배포 시 코드 수정 불필요
  - 기존 환경과의 완전한 호환성 유지
- **파일**: `config/label_studio.py` (line 36-40)

## [1.20.0-sso.17] - 2025-10-29

### Fixed

#### Font Preload 제거
- **문제**: 브라우저 경고 "preload not used within a few seconds from the window's load event"
- **원인**: Figtree 폰트를 preload했지만 React SPA 로드 후에야 사용되어 브라우저가 불필요한 preload로 판단
- **해결**: `<link rel="preload">` 태그 제거 (폰트는 CSS를 통해 필요할 때 자동 로드)
- **효과**: 브라우저 콘솔 경고 제거, 기능에는 영향 없음
- **파일**: `custom-templates/base.html` (line 19-21 삭제)

## [1.20.0-sso.16] - 2025-10-29

### Fixed

#### Font Preload Link 속성 수정
- **문제**: 브라우저 경고 "<link rel=preload> must have a valid `as` value"
- **원인**: `type="font"` 사용, `as` 속성 누락
- **해결**: `as="font" type="font/ttf"` 형식으로 수정
- **파일**: `custom-templates/base.html` (line 20-21)

## [1.20.0-sso.15] - 2025-10-29

### Changed

#### hideHeader Fix 디버그 로그 제거
- **목적**: 프로덕션 환경에서 브라우저 콘솔 출력 깔끔하게 유지
- **변경 사항**: hideHeader Fix 스크립트에서 6개 console.log 제거
- **영향**: hideHeader 기능은 그대로 유지, 로그만 제거
- **파일**: `custom-templates/base.html`

## [1.20.0-sso.14] - 2025-10-29

### Fixed

#### Service Worker 파일 라우팅 수정
- **문제**: sw.js, sw-fallback.js 파일 500 Internal Server Error
- **원인**: URL 라우팅에서 잘못된 경로 사용 (`js/sw.js`)
- **실제 위치**: `static_build/js/sw.js`
- **해결**: `config/urls_simple.py`에서 정확한 경로로 수정
- **파일**: `config/urls_simple.py` (line 20-24)

## [1.20.0-sso.13] - 2025-10-29

### Changed

#### 쿠키 이름 충돌 방지
- **목적**: 같은 도메인에서 여러 Django 애플리케이션 실행 시 쿠키 충돌 방지
- **변경 사항**:
  - Session 쿠키: `sessionid` → `ls_sessionid`
  - CSRF 쿠키: `csrftoken` → `ls_csrftoken`
- **설정 방법**: 환경변수로 커스터마이징 가능
  - `SESSION_COOKIE_NAME` (기본값: `ls_sessionid`)
  - `CSRF_COOKIE_NAME` (기본값: `ls_csrftoken`)
- **호환성**: 기존 세션은 자동으로 만료되고 새 쿠키로 재생성
- **파일**:
  - `config/label_studio.py` (line 129-130 추가)
  - `label-studio-sso-app/backend/server.js` (clearSessionCookies 함수 업데이트)

## [1.20.0-sso.12] - 2025-10-29

### Fixed

#### Static Files Collection 추가
- **문제**: 빌드 시 정적 파일 수집(`collectstatic`)이 누락되어 `sw.js`, `main.js` 등 JavaScript 파일 404 오류 발생
- **해결**: Dockerfile에 `python manage.py collectstatic --noinput` 단계 추가
- **영향**: Label Studio 웹 인터페이스 정상 작동
- **수집된 파일**: 349개 정적 파일 (JavaScript, CSS, images, fonts)
- **파일**: `Dockerfile` (line 38-42)

#### Custom Export API 날짜 필터 타임존 처리
- **문제**: `search_from`, `search_to` 필터가 작동하지 않음
- **원인**:
  - Serializer가 `CharField` 사용 (타임존 정보 손실)
  - PostgreSQL 쿼리에서 `::timestamp` 사용 (타임존 무시)
- **해결**:
  - `DateTimeField`로 변경하여 ISO 8601 타임존 정보 보존
  - `::timestamptz` 사용으로 정확한 타임존 비교
  - `.isoformat()` 메서드로 타임존 정보 포함한 문자열 생성
- **지원 형식**:
  - ISO 8601 with timezone: `2025-01-15T10:30:45+09:00` (권장)
  - ISO 8601 without timezone: `2025-01-15T10:30:45` (UTC로 간주)
- **테스트**: 5개 타임존 테스트 추가 (총 17개 테스트 통과)
- **파일**:
  - `custom-api/export_serializers.py` (line 24-34)
  - `custom-api/export.py` (line 155-173)
  - `custom-api/tests.py` (5개 타임존 테스트 추가)
  - `docs/CUSTOM_EXPORT_API_GUIDE.md` (타임존 처리 문서화)

### Changed

#### 프로젝트 파일 구조 개선
- **목적**: 스크립트 파일 통합 및 개발 편의성 향상
- **변경 사항**:
  - 모든 스크립트를 `scripts/` 디렉토리로 이동
  - `Makefile` 추가 (테스트 명령어 간소화)
  - `README.md` 업데이트 (새로운 디렉토리 구조 및 테스트 방법)
- **이동된 파일**:
  - `run_tests.sh` → `scripts/run_tests.sh`
  - `run_quick_test.sh` → `scripts/run_quick_test.sh`
  - `patch_webhooks.py` → `scripts/patch_webhooks.py`
- **새로운 명령어**: `make test`, `make test-quick`, `make test-date`, `make test-timezone` 등

## [1.20.0-sso.11] - 2025-10-28

### Changed

#### Custom Export API 리팩토링
- **목적**: Label Studio 오리지널 구현 패턴 준수
- **변경 사항**:
  - Label Studio 오리지널 `PredictionSerializer` 사용
  - Label Studio 오리지널 `AnnotationSerializer` 사용
  - 수동 직렬화 코드 제거 (29줄 감소)
- **장점**:
  - Label Studio 1.20.0 표준 Serializer 사용으로 호환성 향상
  - 모든 필드 자동 포함 (`created_ago`, `created_username` 등)
  - 코드 유지보수성 향상
  - MLOps 커스텀 기능 유지 (`completed_by_info` enrichment)
- **파일**: `custom-api/export.py`

## [1.20.0-sso.10] - 2025-10-28

### Added

#### Custom Export API (MLOps 통합)
- **목적**: MLOps 시스템의 모델 학습 및 성능 계산을 위한 필터링된 Task Export API
- **엔드포인트**: `POST /api/custom/export/`
- **주요 기능**:
  - 날짜 범위 필터링 (`task.data.source_created_dt`)
  - 모델 버전 필터링 (`prediction.model_version`)
  - 승인자 필터링 (`annotation.completed_by` - Super User만)
  - 선택적 페이징 지원 (기본: 전체 반환)
  - N+1 쿼리 최적화 (Prefetch)
- **사용 시나리오**:
  - 모델 학습 데이터 수집
  - 모델 성능 계산 (예측 vs 승인 라벨 비교)
- **파일**:
  - `custom-api/export.py` (새로 추가)
  - `custom-api/export_serializers.py` (새로 추가)
  - `custom-api/urls.py` (라우팅 추가)
  - `docs/CUSTOM_EXPORT_API_GUIDE.md` (API 가이드 문서)

### Changed
- README.md: "7. Custom Export API (MLOps 통합)" 섹션 추가
- README.md: Custom Export API 문서 링크 추가

## [1.20.0-sso.9] - 2025-10-28

### Added

#### iframe 임베딩 X-Frame-Options 설정
- **기본값 변경**: 환경변수 미설정 시 iframe 임베딩 자동 허용 (Django 기본 SAMEORIGIN 제약 제거)
- 환경변수로 X-Frame-Options 제어 가능
  - 설정 안함: 모든 도메인에서 iframe 임베딩 허용 (기본값, 권장)
  - `X_FRAME_OPTIONS=DENY`: iframe 임베딩 완전 차단
  - `X_FRAME_OPTIONS=SAMEORIGIN`: 같은 도메인에서만 허용
- 다른 도메인에서 Label Studio를 iframe으로 임베드할 때 발생하는 문제 해결
- 파일: `config/label_studio.py` (X-Frame-Options 설정 추가)

### Changed
- README.md: iframe 임베딩 설정 섹션 추가
- README.md: X-Frame-Options 환경변수 설명 추가

## [1.20.0-sso.8] - 2025-10-28

### Added

#### Project model_version 검증 우회
- Project 수정 API에서 `model_version` 필드 유효성 검증을 우회
- 외부 MLOps 시스템의 모델 버전 ID를 자유롭게 저장 가능
- `ProjectSerializer`의 `validate_model_version()` 메서드 오버라이드
- 생성/수정 시 일관된 동작 제공 (일관성 개선)
- 파일:
  - `custom-api/projects.py` (새로 추가)
  - `custom-api/projects_urls.py` (새로 추가)
  - `custom-api/urls.py` (리팩토링)
  - `config/urls_simple.py` (Project API 오버라이드 라우팅)

### Changed
- README.md: 주요 기능 섹션에 "6. Project model_version 유효성 검증 우회" 추가
- README.md: Project model_version 수정 API 사용 예시 및 활용 시나리오 추가
- README.md: 디렉토리 구조에 `projects.py` 추가

### Fixed
- Django URL 라우팅 오류 수정 (project_urlpatterns를 별도 파일로 분리)

## [1.20.0-sso.7] - 2025-10-XX

### Added

#### Webhook Payload 커스터마이징
- Annotation 이벤트 webhook에 `completed_by_info` 필드 자동 추가
- 사용자 ID, 이메일, 사용자명, superuser 여부 포함
- MLOps 시스템에서 별도 API 호출 없이 사용자 정보 확인 가능
- Monkey patching 방식으로 Label Studio webhook 함수 확장
- 파일:
  - `custom-webhooks/__init__.py`
  - `custom-webhooks/apps.py`
  - `custom-webhooks/utils.py`
  - `custom-webhooks/signals.py`
  - `custom-webhooks/tests.py`

### Changed
- `config/label_studio.py`: `custom_webhooks` 앱 추가
- `Dockerfile`: custom-webhooks 디렉토리 복사 추가

## [1.20.0-sso.1] - 2025-10-22

### Added

#### SSO 인증 (Native JWT)
- label-studio-sso v6.0.7 통합
- JWT 토큰 기반 인증 시스템
- 쿠키 및 URL 파라미터로 토큰 전달 지원
- 사용자 자동 생성 기능
- 파일: `config/label_studio.py`

#### hideHeader 기능
- iframe 임베딩 시 Label Studio 헤더 완전 제거
- URL 파라미터 `?hideHeader=true` 지원
- JavaScript로 `--header-height` CSS 변수 강제 0px 설정
- 100ms 간격으로 5초간 CSS 변수 강제 적용 (React SPA 대응)
- 파일: `custom-templates/base.html`

#### Annotation 소유권 제어
- 사용자가 자신의 annotation만 수정/삭제할 수 있도록 제한
- `IsAnnotationOwnerOrReadOnly` permission 클래스 구현
- `AnnotationOwnershipMixin` 구현으로 기존 View 확장
- API 레벨 보안 강화 (Postman, curl 등 직접 API 호출도 차단)
- 파일:
  - `custom-permissions/__init__.py`
  - `custom-permissions/apps.py`
  - `custom-permissions/permissions.py`
  - `custom-permissions/mixins.py`
  - `custom-api/__init__.py`
  - `custom-api/urls.py`
  - `custom-api/annotations.py`

#### 초기화 스크립트
- 자동 사용자 생성 스크립트
- 파일:
  - `scripts/create_initial_users.py`
  - `scripts/init_users.sh`

### Changed

#### 설정 파일
- Django settings with SSO integration
- URL routing with custom API override
- 파일:
  - `config/label_studio.py`
  - `config/urls_simple.py`

### Security

#### API 보안
- Annotation API에 소유권 기반 접근 제어 추가
- 403 Forbidden 응답으로 권한 없는 수정/삭제 차단
- Admin 계정은 모든 annotation 접근 가능

## Version History

### v1.20.0-sso.1 (2025-10-22)
- Initial release
- Based on Label Studio 1.20.0
- SSO authentication (Native JWT)
- hideHeader functionality
- Annotation ownership control

## Base Label Studio Version

이 커스텀 이미지는 다음 버전을 기반으로 합니다:
- Label Studio: 1.20.0
- label-studio-sso: 6.0.7

## Migration Notes

### From Label Studio 1.20.0 (Vanilla)

#### 환경 변수 추가 필요

```bash
# SSO 설정
JWT_SSO_NATIVE_USER_ID_CLAIM=user_id
JWT_SSO_COOKIE_NAME=ls_auth_token
JWT_SSO_TOKEN_PARAM=token
SSO_TOKEN_EXPIRY=600
SSO_AUTO_CREATE_USERS=true

# 쿠키 도메인 (서브도메인 공유 시)
SESSION_COOKIE_DOMAIN=.yourdomain.com
CSRF_COOKIE_DOMAIN=.yourdomain.com
```

#### 볼륨 마운트 (선택사항)

```yaml
volumes:
  - labelstudio_data:/label-studio/data
```

## Known Issues

### v1.20.0-sso.1

#### Frontend Read-Only UI
- 프론트엔드에서 다른 사용자의 annotation 수정 버튼이 자동으로 비활성화되지 않음
- 현재는 수정 시도 시 403 에러로 차단됨
- 향후 버전에서 프론트엔드 UI 레벨 비활성화 추가 예정

#### Browser Cache
- hideHeader 기능 변경 시 브라우저 캐시로 인해 즉시 반영되지 않을 수 있음
- 해결: Hard Refresh (Cmd/Ctrl + Shift + R)

## Roadmap

### v1.20.0-sso.2 (Planned)
- [ ] Frontend read-only UI for non-owner annotations
- [ ] Additional SSO providers (SAML, OAuth2)
- [ ] Performance improvements

### v1.21.0-sso.1 (Future)
- [ ] Upgrade to Label Studio 1.21.0
- [ ] Maintain SSO and custom features compatibility

## Support

For questions or issues:
- GitHub Issues: [Report a bug or request a feature]
- Documentation: See README.md and docs/

## Contributors

- heartyoh@hatiolab.com - Project owner and requirements
- Claude (AI Assistant) - Implementation and documentation

---

**Note**: This project is based on Label Studio open source project.
- Label Studio: https://github.com/HumanSignal/label-studio
- label-studio-sso: https://pypi.org/project/label-studio-sso/
