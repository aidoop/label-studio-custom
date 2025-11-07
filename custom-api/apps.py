"""
Custom API Django App Configuration
"""

from django.apps import AppConfig


class CustomApiConfig(AppConfig):
    """Custom API App 설정"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'custom_api'
    verbose_name = 'Custom API'

    def ready(self):
        """
        앱이 준비되었을 때 실행
        - Signals 등록
        """
        # Import signals to register them
        import custom_api.signals  # noqa: F401
        print("[Custom API] Signals registered")
