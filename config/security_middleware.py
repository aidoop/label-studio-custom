"""
Security Middleware for Label Studio Custom

Provides configurable security headers for iframe embedding control:
- X-Frame-Options
- Content-Security-Policy (frame-ancestors)
"""

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    """
    Content-Security-Policy 미들웨어

    환경변수를 통해 frame-ancestors를 설정하여 iframe 임베딩을 제어합니다.

    환경변수:
        CONTENT_SECURITY_POLICY: CSP 헤더 전체 값
        CSP_FRAME_ANCESTORS: frame-ancestors 지시문만 설정 (간편 모드)

    사용 예시:
        # 전체 CSP 설정
        CONTENT_SECURITY_POLICY="frame-ancestors 'self' https://console-dev.nubison.io"

        # frame-ancestors만 설정 (권장)
        CSP_FRAME_ANCESTORS="'self' https://console-dev.nubison.io https://console.nubison.io"

        # 모든 도메인 허용
        CSP_FRAME_ANCESTORS="*"

        # 완전 차단
        CSP_FRAME_ANCESTORS="'none'"

    참고:
        - CSP는 X-Frame-Options보다 우선순위가 높음 (최신 브라우저)
        - 서버(nginx 등)에서 설정된 경우 앱 설정은 무시됨
    """

    def process_response(self, request, response):
        # 환경변수에서 CSP 설정 읽기
        csp_full = getattr(settings, 'CONTENT_SECURITY_POLICY', None)
        csp_frame_ancestors = getattr(settings, 'CSP_FRAME_ANCESTORS', None)

        # 이미 CSP 헤더가 설정되어 있으면 스킵 (서버 설정 우선)
        if 'Content-Security-Policy' in response:
            return response

        # 전체 CSP 설정이 있으면 그대로 사용
        if csp_full:
            response['Content-Security-Policy'] = csp_full
            return response

        # frame-ancestors만 설정하는 경우
        if csp_frame_ancestors:
            response['Content-Security-Policy'] = f"frame-ancestors {csp_frame_ancestors};"
            return response

        # 설정이 없으면 헤더를 추가하지 않음 (기본 동작 유지)
        return response


class XFrameOptionsMiddleware(MiddlewareMixin):
    """
    X-Frame-Options 미들웨어 (추가 제어용)

    Django의 기본 XFrameOptionsMiddleware를 대체하여 더 유연한 제어를 제공합니다.

    환경변수:
        X_FRAME_OPTIONS: 'DENY', 'SAMEORIGIN', 또는 'ALLOW-FROM {url}'

    사용 예시:
        X_FRAME_OPTIONS=DENY                                    # iframe 완전 차단
        X_FRAME_OPTIONS=SAMEORIGIN                              # 같은 도메인만 허용
        X_FRAME_OPTIONS=ALLOW-FROM https://console.nubison.io   # 특정 도메인 허용 (구형 브라우저)

    참고:
        - CSP frame-ancestors가 설정된 경우 최신 브라우저는 CSP를 우선 적용
        - ALLOW-FROM은 deprecated되었으므로 CSP 사용 권장
        - 서버(nginx 등)에서 설정된 경우 앱 설정은 무시됨
    """

    def process_response(self, request, response):
        # 이미 X-Frame-Options 헤더가 설정되어 있으면 스킵 (서버 설정 우선)
        if 'X-Frame-Options' in response:
            return response

        # 환경변수에서 설정 읽기
        x_frame_options = getattr(settings, 'X_FRAME_OPTIONS_HEADER', None)

        if x_frame_options:
            response['X-Frame-Options'] = x_frame_options

        return response
