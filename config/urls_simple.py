"""
Label Studio URL 설정 (SSO API 엔드포인트 추가)
Label Studio 1.20.0 호환 버전 (drf_spectacular 없이)
"""

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
    re_path(
        r'^sw-fallback\.js$',
        views.static_file_with_host_resolver('js/sw-fallback.js', content_type='text/javascript'),
    ),

    # Favicon
    re_path(r'^favicon\.ico$', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),

    # 프론트엔드 정적 파일
    re_path(
        r'^label-studio-frontend/(?P<path>.*)$',
        serve,
        kwargs={'document_root': settings.EDITOR_ROOT, 'show_indexes': True},
    ),
    re_path(r'^dm/(?P<path>.*)$', serve, kwargs={'document_root': settings.DM_ROOT, 'show_indexes': True}),
    re_path(
        r'^react-app/(?P<path>.*)$',
        serve,
        kwargs={
            'document_root': settings.REACT_APP_ROOT,
            'show_indexes': True,
            'manifest_asset_prefix': 'react-app',
        },
    ),

    # 폰트 및 기타 정적 파일
    re_path(
        r'^static/fonts/roboto/roboto.css$',
        views.static_file_with_host_resolver('fonts/roboto/roboto.css', content_type='text/css'),
    ),
    re_path(r'^static/(?P<path>.*)$', serve, kwargs={'document_root': settings.STATIC_ROOT, 'show_indexes': True}),

    # ==============================================================================
    # Custom API Overrides
    # ==============================================================================
    # Annotation API 오버라이드 (ownership permission 추가)
    # 중요: tasks.urls보다 먼저 등록하여 기본 URL을 오버라이드
    path('api/annotations/', include('custom_api.urls')),

    # Label Studio 앱 URL 패턴
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

    # 로컬 파일 데이터
    re_path(r'data/local-files/', views.localfiles_data, name='localfiles_data'),

    # 버전 정보
    re_path(r'version/', views.version_page, name='version'),
    re_path(r'api/version/', views.version_page, name='api-version'),

    # 헬스체크 및 메트릭
    re_path(r'health/', views.health, name='health'),
    re_path(r'metrics/', views.metrics, name='metrics'),
    re_path(r'trigger500/', views.TriggerAPIError.as_view(), name='metrics'),

    # 샘플 데이터
    re_path(r'samples/time-series.csv', views.samples_time_series, name='static_time_series'),
    re_path(r'samples/paragraphs.json', views.samples_paragraphs, name='samples_paragraphs'),

    # Django Admin
    path('admin/', admin.site.urls),

    # Django RQ (백그라운드 작업)
    path('django-rq/', include('django_rq.urls')),

    # Feature Flags
    path('feature-flags/', views.feature_flags, name='feature_flags'),
    path('heidi-tips/', views.heidi_tips, name='heidi_tips'),

    # 메트릭 수집
    path('__lsa/', views.collect_metrics, name='collect_metrics'),

    # REST Framework 인증 UI
    re_path(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # ==============================================================================
    # SSO API 엔드포인트 (label-studio-sso)
    # ==============================================================================
    # SSO 토큰 발급 API
    # POST /api/sso/token - JWT 토큰 발급
    path('api/sso/', include('label_studio_sso.urls')),
]

# 개발 환경 전용 설정
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass

    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
