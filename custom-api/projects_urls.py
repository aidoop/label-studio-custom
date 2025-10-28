"""
Project API URL patterns

Project API 오버라이드 전용 URL 설정
"""

from django.urls import path
from custom_api.projects import ProjectAPI

app_name = 'custom_projects'

# Project API 오버라이드용 urlpatterns
urlpatterns = [
    path('<int:pk>/', ProjectAPI.as_view(), name='project-detail'),
]
