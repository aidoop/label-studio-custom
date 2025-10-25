from django.apps import AppConfig


class CustomPermissionsConfig(AppConfig):
    """Custom Permissions App Configuration"""

    name = 'label_studio.custom_permissions'
    verbose_name = 'Custom Permissions'
    default_auto_field = 'django.db.models.BigAutoField'
