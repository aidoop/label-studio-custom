"""
Label Studio URL 설정 (SSO API 엔드포인트 추가)

이 파일은 Label Studio의 기본 URL 패턴에 SSO API만 추가합니다.
"""

from django.urls import path, include

# Label Studio의 기본 URL 패턴들을 모두 가져옴
# 이 import는 Label Studio가 설치된 환경에서 동작합니다
try:
    # Label Studio 1.20.0의 기본 urlpatterns
    from label_studio.core.urls_default import urlpatterns as default_urlpatterns
    urlpatterns = default_urlpatterns.copy()
except ImportError:
    # fallback: 직접 정의
    from core import views
    from core.utils.static_serve import serve
    from django.conf import settings
    from django.conf.urls import include
    from django.contrib import admin
    from django.http import HttpResponseRedirect
    from django.urls import path, re_path
    from django.views.generic.base import RedirectView

    urlpatterns = [
        # 메인 페이지
        re_path(r'^$', views.main, name='main'),

        # Service Worker
        re_path(r'^sw\.js$', views.static_file_with_host_resolver('js/sw.js', content_type='text/javascript')),

        # Favicon
        re_path(r'^favicon\.ico$', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),

        # 정적 파일
        re_path(r'^static/(?P<path>.*)$', serve, kwargs={'document_root': settings.STATIC_ROOT}),

        # Label Studio 앱 URL
        re_path(r'^', include('organizations.urls')),
        re_path(r'^', include('projects.urls')),
        re_path(r'^', include('data_import.urls')),
        re_path(r'^', include('data_manager.urls')),
        re_path(r'^', include('data_export.urls')),
        re_path(r'^', include('users.urls')),
        re_path(r'^', include('tasks.urls')),
        re_path(r'^', include('io_storages.urls')),
        re_path(r'^', include('ml.urls')),
        re_path(r'^', include('webhooks.urls')),

        # 헬스체크
        re_path(r'health/', views.health, name='health'),

        # Admin
        path('admin/', admin.site.urls),

        # REST Framework 인증
        re_path(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    ]

# ==============================================================================
# SSO API 엔드포인트 추가 (label-studio-sso)
# ==============================================================================

# SSO 토큰 발급 API
# POST /api/sso/token - JWT 토큰 발급
# 외부 애플리케이션이 이 엔드포인트를 호출하여 사용자를 인증할 수 있습니다.
urlpatterns.append(
    path('api/sso/', include('label_studio_sso.urls'))
)
