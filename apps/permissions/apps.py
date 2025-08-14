from django.apps import AppConfig
from django.core.signals import request_finished

from .checks import clear_perm_cache


def _clear_perm_cache(**kwargs):
    """Signal handler to clear the permission cache."""
    clear_perm_cache()


class PermissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.permissions'

    def ready(self):
        import apps.permissions.signals
        request_finished.connect(
            _clear_perm_cache, dispatch_uid="apps.permissions.clear_perm_cache"
        )
