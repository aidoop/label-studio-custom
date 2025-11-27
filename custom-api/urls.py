"""
Custom API URLs

AnnotationAPI와 ProjectAPI를 커스텀 버전으로 오버라이드하고,
Admin 전용 사용자 관리 API를 제공합니다.
"""

from django.urls import path
from custom_api.annotations import AnnotationAPI
from custom_api.projects import ProjectAPI
from custom_api.admin_users import CreateSuperuserAPI, PromoteToSuperuserAPI, DemoteFromSuperuserAPI, ListUsersAPI
from custom_api.export import CustomExportAPI
from custom_api.users import user_detail, user_by_email

app_name = 'custom_api'

# 기본 urlpatterns
# Annotation API 오버라이드 + Admin User Management API + Custom Export API + Version API
urlpatterns = [
    # Annotation API 오버라이드 (annotation ownership control)
    path('<int:pk>/', AnnotationAPI.as_view(), name='annotation-detail'),

    # Admin User Management APIs
    path('admin/users/list', ListUsersAPI.as_view(), name='list-users'),
    path('admin/users/create-superuser', CreateSuperuserAPI.as_view(), name='create-superuser'),
    path('admin/users/<int:user_id>/promote-to-superuser', PromoteToSuperuserAPI.as_view(), name='promote-to-superuser'),
    path('admin/users/<int:user_id>/demote-from-superuser', DemoteFromSuperuserAPI.as_view(), name='demote-from-superuser'),

    # Custom Export API (MLOps 모델 학습 및 성능 계산용)
    path('custom/export/', CustomExportAPI.as_view(), name='custom-export'),

    # User Management API (이메일 수정 지원)
    path('users/<int:pk>/', user_detail, name='user-detail'),
    path('users/by-email/', user_by_email, name='user-by-email'),
]
