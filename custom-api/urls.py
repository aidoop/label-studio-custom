"""
Custom API URLs

AnnotationAPI를 커스텀 버전으로 오버라이드합니다.
"""

from django.urls import path
from custom_api.annotations import AnnotationAPI

app_name = 'custom_api'

# Annotation API 오버라이드
urlpatterns = [
    path('<int:pk>/', AnnotationAPI.as_view(), name='annotation-detail'),
]
