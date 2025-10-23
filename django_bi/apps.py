from importlib import import_module

from django.apps import AppConfig
from django_bi.conf import settings

from .blocks.registry import block_registry


class DjangoBiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_bi"
    verbose_name = "Django BI"

    def ready(self):
        # Blocks ready logic: register builtins and load configured entry points.
        try:
            from .blocks.builtins import register as register_builtins

            register_builtins(block_registry)
        except Exception:
            pass

        blocks = getattr(settings, "BLOCKS", [])
        for entry in blocks:
            try:
                module_path, callable_name = entry.split(":", 1)
            except ValueError:
                import_module(entry)
            else:
                module = import_module(module_path)
                registrar = getattr(module, callable_name)
                registrar(block_registry)

        # Permissions ready logic: ensure signal handlers are registered.
        from .permissions import signals as permissions_signals  # noqa: F401

        # Workflow ready logic: load workflow signals.
        from .workflow import signals as workflow_signals  # noqa: F401
