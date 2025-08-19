from importlib import import_module  # used for dynamic block loading

from django.apps import AppConfig
from django.conf import settings

from .registry import block_registry


class BlocksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.blocks"

    def ready(self):
        # Register signal handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Signals are best-effort at startup to avoid migration-time errors
            pass
        # Load any block entry points defined in settings.BLOCKS.  Each entry
        # can be either a module path that performs registration on import or a
        # "module:callable" string where the callable accepts the registry
        # instance.
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

