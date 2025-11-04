# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
