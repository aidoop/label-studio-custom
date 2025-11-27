"""
Custom Version API

Label Studio 커스텀 버전 정보를 제공합니다.
기존 /version API를 오버라이드하여 커스텀 버전 정보를 추가합니다.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
import requests
import os


class CustomVersionAPI(APIView):
    """
    커스텀 버전 정보 조회 API

    GET /version

    기존 Label Studio 버전 정보에 커스텀 정보를 추가합니다.

    Response:
    {
        "release": "1.20.0",
        "custom_version": "1.20.0-sso.30",
        "custom_edition": "Community + SSO Custom",
        "custom_release_date": "2025-11-07",
        "custom_features": [...],
        "label-studio-os-package": {...},
        ...
    }
    """
    permission_classes = []  # Public API

    def get(self, request):
        try:
            # 기존 Label Studio /version API 호출
            # Django의 내부 URL resolver를 사용하여 원본 view 호출
            from label_studio.core.urls import urlpatterns as core_urlpatterns
            from django.urls import resolve

            # 원본 Label Studio version view 찾기
            original_version_view = None
            for pattern in core_urlpatterns:
                if hasattr(pattern, 'pattern') and str(pattern.pattern) == 'version':
                    original_version_view = pattern.callback
                    break

            # 원본 버전 정보 가져오기
            base_response = {}
            if original_version_view:
                try:
                    original_response = original_version_view(request)
                    if hasattr(original_response, 'data'):
                        base_response = dict(original_response.data)
                    elif hasattr(original_response, 'content'):
                        import json
                        base_response = json.loads(original_response.content)
                except Exception:
                    pass

            # 기본 버전 정보가 없으면 최소한의 정보 제공
            if not base_response:
                base_response = {
                    "release": "1.20.0",
                    "edition": "Community"
                }

            # 환경 변수에서 커스텀 버전 정보 가져오기
            custom_version = os.environ.get('CUSTOM_VERSION', '1.20.0-sso.42')
            release_date = os.environ.get('CUSTOM_RELEASE_DATE', '2025-11-28')

            # 원본 버전 백업 (참고용)
            base_response['base_release'] = base_response.get('release', '1.20.0')

            # release 필드를 커스텀 버전으로 오버라이드 (UI에서 사용)
            base_response['release'] = custom_version

            # 커스텀 정보 추가
            base_response['custom_version'] = custom_version
            base_response['custom_edition'] = 'Community + SSO Custom'
            base_response['custom_release_date'] = release_date
            base_response['custom_features'] = [
                'Admin User List API with Superuser Info',
                'Admin User Management (Create/Promote/Demote Superuser)',
                'Active Organization Signal (Auto-set on membership)',
                'Custom Export API with Date Filtering',
                'SSO Token Validation API',
                'Custom SSO Login Page for iframe',
                'Enhanced Security (CSRF, CSP, X-Frame-Options)',
                'Date Range Filter UI for Data Manager'
            ]

            # HTML 형식 응답 (브라우저 접근 시)
            if 'text/html' in request.META.get('HTTP_ACCEPT', ''):
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Label Studio Custom Version</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .version {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .custom-version {{ font-size: 20px; color: #28a745; margin-top: 10px; }}
        .info {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin-top: 20px; }}
        .features {{ list-style: none; padding: 0; }}
        .features li {{ padding: 5px 0; }}
        .features li:before {{ content: "✓ "; color: #28a745; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Label Studio Version Information</h1>
    <div class="version">Base Version: {base_response.get('release', '1.20.0')}</div>
    <div class="custom-version">Custom Version: {custom_version}</div>
    <div class="info">
        <h2>Custom Features</h2>
        <ul class="features">
            {''.join(f'<li>{feature}</li>' for feature in base_response['custom_features'])}
        </ul>
        <p><strong>Edition:</strong> {base_response['custom_edition']}</p>
        <p><strong>Release Date:</strong> {release_date}</p>
    </div>
</body>
</html>"""
                return HttpResponse(html_content, content_type='text/html')

            # JSON 응답 (API 호출 시)
            return Response(base_response, status=status.HTTP_200_OK)

        except Exception as e:
            # 에러 발생 시 최소한의 정보라도 반환
            custom_version = os.environ.get('CUSTOM_VERSION', '1.20.0-sso.41')
            return Response({
                'release': custom_version,
                'base_release': '1.20.0',
                'custom_version': custom_version,
                'edition': 'Community + SSO Custom',
                'error': f'Failed to get full version info: {str(e)}'
            }, status=status.HTTP_200_OK)
