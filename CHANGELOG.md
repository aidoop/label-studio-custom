# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
