"""
Custom API URLs

AnnotationAPI를 커스텀 버전으로 오버라이드하고,
Admin 전용 사용자 관리 API를 제공합니다.
"""

from django.urls import path
from custom_api.annotations import AnnotationAPI
from custom_api.admin_users import CreateSuperuserAPI, PromoteToSuperuserAPI, DemoteFromSuperuserAPI

app_name = 'custom_api'

# Annotation API 오버라이드
urlpatterns = [
    path('<int:pk>/', AnnotationAPI.as_view(), name='annotation-detail'),

    # Admin User Management APIs
    path('admin/users/create-superuser', CreateSuperuserAPI.as_view(), name='create-superuser'),
    path('admin/users/<int:user_id>/promote-to-superuser', PromoteToSuperuserAPI.as_view(), name='promote-to-superuser'),
    path('admin/users/<int:user_id>/demote-from-superuser', DemoteFromSuperuserAPI.as_view(), name='demote-from-superuser'),
]
