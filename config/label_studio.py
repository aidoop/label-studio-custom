"""
Label Studio 설정 파일 (SSO 통합)

이 파일은 Label Studio의 기본 설정을 확장하여 label-studio-sso를 통합합니다.
원본 Label Studio 1.20.0의 설정을 기반으로 SSO 관련 설정을 추가했습니다.
"""

import json

from core.settings.base import *  # noqa
from core.utils.secret_key import generate_secret_key_if_missing

# ==============================================================================
# 보안 설정
# ==============================================================================

# Django SECRET_KEY 자동 생성
# 프로덕션 환경에서는 환경변수로 설정하는 것을 권장
SECRET_KEY = generate_secret_key_if_missing(BASE_DATA_DIR)

# ==============================================================================
# 데이터베이스 설정
# ==============================================================================

# 데이터베이스 타입 선택 (환경변수로 제어)
# - 'default': PostgreSQL
# - 'sqlite': SQLite (개발용)
DJANGO_DB = get_env('DJANGO_DB', DJANGO_DB_SQLITE)

# PostgreSQL 설정을 환경변수로부터 직접 구성
if DJANGO_DB == 'default':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': get_env('POSTGRES_DB', 'labelstudio'),
            'USER': get_env('POSTGRES_USER', 'postgres'),
            'PASSWORD': get_env('POSTGRES_PASSWORD', 'postgres'),
            'HOST': get_env('POSTGRES_HOST', 'postgres'),
            'PORT': get_env('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {'default': DATABASES_ALL[DJANGO_DB]}

# ==============================================================================
# SSO 설정 (label-studio-sso)
# ==============================================================================

# INSTALLED_APPS에 SSO 관련 앱 추가
# 주의: rest_framework와 rest_framework.authtoken은 Label Studio에 이미 포함되어 있음
INSTALLED_APPS += [
    'label_studio_sso',           # SSO 인증 앱
    'custom_permissions',         # 커스텀 권한 관리 (Annotation 소유권)
]

# 인증 백엔드 설정
# JWTAuthenticationBackend를 최우선으로 설정하여 SSO 인증을 먼저 시도
AUTHENTICATION_BACKENDS = [
    'label_studio_sso.backends.JWTAuthenticationBackend',  # SSO JWT 인증
    'rules.permissions.ObjectPermissionBackend',           # 권한 관리
    'django.contrib.auth.backends.ModelBackend',           # 기본 인증
]

# ==============================================================================
# 미들웨어 설정
# ==============================================================================

# 기본 미들웨어 추가
MIDDLEWARE.append('organizations.middleware.DummyGetSessionMiddleware')
MIDDLEWARE.append('core.middleware.UpdateLastActivityMiddleware')

# 비활성 세션 타임아웃 (설정된 경우)
if INACTIVITY_SESSION_TIMEOUT_ENABLED:
    MIDDLEWARE.append('core.middleware.InactivitySessionTimeoutMiddleWare')

# SSO 자동 로그인 미들웨어 추가
# 이 미들웨어는 JWT 토큰(쿠키 또는 URL 파라미터)을 감지하고 자동으로 로그인 처리
MIDDLEWARE.append('label_studio_sso.middleware.JWTAutoLoginMiddleware')

# ==============================================================================
# SSO JWT 설정
# ==============================================================================

# JWT 토큰에서 사용자 ID를 추출할 claim 이름
JWT_SSO_NATIVE_USER_ID_CLAIM = get_env('JWT_SSO_NATIVE_USER_ID_CLAIM', 'user_id')

# JWT 토큰을 전달할 쿠키 이름 (권장 방식)
# HttpOnly 쿠키로 전달하여 XSS 공격 방지
JWT_SSO_COOKIE_NAME = get_env('JWT_SSO_COOKIE_NAME', 'ls_auth_token')

# 쿠키 경로 설정 (기본값: 모든 경로)
JWT_SSO_COOKIE_PATH = get_env('JWT_SSO_COOKIE_PATH', '/')

# JWT 토큰을 전달할 URL 파라미터 이름 (폴백 방식)
# 예: http://labelstudio.com?token=eyJhbGc...
JWT_SSO_TOKEN_PARAM = get_env('JWT_SSO_TOKEN_PARAM', 'token')

# SSO 토큰 만료 시간 (초 단위)
# 기본값: 600초 (10분)
SSO_TOKEN_EXPIRY = int(get_env('SSO_TOKEN_EXPIRY', '600'))

# SSO API를 통한 사용자 자동 생성 활성화
# True: 존재하지 않는 사용자는 자동으로 생성
# False: 이미 존재하는 사용자만 로그인 가능
SSO_AUTO_CREATE_USERS = get_bool_env('SSO_AUTO_CREATE_USERS', True)

# ==============================================================================
# 기타 Label Studio 설정
# ==============================================================================

# ML 백엔드 자동 추가 비활성화
ADD_DEFAULT_ML_BACKENDS = False

# 로그 레벨 설정 (환경변수로 제어)
LOGGING['root']['level'] = get_env('LOG_LEVEL', 'WARNING')

# 디버그 모드 (개발 환경에서만 True)
DEBUG = get_bool_env('DEBUG', False)

# 디버그 예외 전파 설정
DEBUG_PROPAGATE_EXCEPTIONS = get_bool_env('DEBUG_PROPAGATE_EXCEPTIONS', False)

# ==============================================================================
# 세션 및 쿠키 설정
# ==============================================================================

# HTTPS 환경에서만 세션 쿠키 전송
SESSION_COOKIE_SECURE = get_bool_env('SESSION_COOKIE_SECURE', False)

# 세션 엔진 설정 (서명된 쿠키 사용)
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

# ==============================================================================
# 서브도메인 기반 쿠키 공유 설정
# ==============================================================================

# 쿠키 도메인 설정 (서브도메인 간 세션 공유)
# 예: .nubison.localhost 로 설정하면
#     - http://nubison.localhost
#     - http://label.nubison.localhost
#     - http://api.nubison.localhost
#     모두 같은 세션 쿠키 공유 가능
SESSION_COOKIE_DOMAIN = get_env('SESSION_COOKIE_DOMAIN', None)
CSRF_COOKIE_DOMAIN = get_env('CSRF_COOKIE_DOMAIN', None)

# 쿠키 SameSite 설정
# - Lax: 일반적인 서브도메인 간 공유 (권장)
# - Strict: 완전히 같은 도메인만 (서브도메인 간 공유 불가)
# - None: 모든 cross-site 요청 허용 (HTTPS + Secure 필수)
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# ==============================================================================
# Sentry 에러 추적 설정 (선택사항)
# ==============================================================================

SENTRY_DSN = get_env('SENTRY_DSN', 'https://68b045ab408a4d32a910d339be8591a4@o227124.ingest.sentry.io/5820521')
SENTRY_ENVIRONMENT = get_env('SENTRY_ENVIRONMENT', 'opensource')

FRONTEND_SENTRY_DSN = get_env(
    'FRONTEND_SENTRY_DSN', 'https://5f51920ff82a4675a495870244869c6b@o227124.ingest.sentry.io/5838868'
)
FRONTEND_SENTRY_ENVIRONMENT = get_env('FRONTEND_SENTRY_ENVIRONMENT', 'opensource')

# ==============================================================================
# 에디터 설정
# ==============================================================================

EDITOR_KEYMAP = json.dumps(get_env('EDITOR_KEYMAP'))

# Sentry 초기화
from label_studio import __version__
from label_studio.core.utils import sentry

sentry.init_sentry(release_name='label-studio', release_version=__version__)

# 버전 정보 수집
from label_studio.core.utils.common import collect_versions

versions = collect_versions()

# ==============================================================================
# Feature Flags 설정
# ==============================================================================

# Community 버전에서는 모든 feature flag가 기본적으로 ON
FEATURE_FLAGS_DEFAULT_VALUE = True

# 오프라인 모드 사용 (외부 서비스 없이 로컬 파일 사용)
FEATURE_FLAGS_OFFLINE = get_bool_env('FEATURE_FLAGS_OFFLINE', True)

# Feature flags 파일 경로
FEATURE_FLAGS_FILE = get_env('FEATURE_FLAGS_FILE', 'feature_flags.json')
FEATURE_FLAGS_FROM_FILE = True

try:
    from core.utils.io import find_node
    find_node('label_studio', FEATURE_FLAGS_FILE, 'file')
except IOError:
    FEATURE_FLAGS_FROM_FILE = False

# ==============================================================================
# 스토리지 설정
# ==============================================================================

# 스토리지 영속성 활성화
STORAGE_PERSISTENCE = get_bool_env('STORAGE_PERSISTENCE', True)
