"""Central registry for block implementations."""

from .base import BaseBlock


class BlockRegistry:
    """Store block implementations by identifier.

    The registry tracks registered blocks and prevents duplicate
    registrations.  Consumers can look up a block by its identifier or
    iterate over all registered blocks.  Alongside each block instance the
    registry keeps metadata such as supported features.
    """

    def __init__(self):
        self._blocks = {}
        self._metadata = {}

    def register(self, block_id, block_instance):
        """Register ``block_instance`` under ``block_id``.

        Raises ``ValueError`` if ``block_id`` is already present in the
        registry or ``TypeError`` if the instance is not a ``BaseBlock``
        subclass.
        """

        if not isinstance(block_instance, BaseBlock):
            raise TypeError("block_instance must subclass BaseBlock")
        if block_id in self._blocks:
            raise ValueError(f"Block '{block_id}' is already registered")
        self._blocks[block_id] = block_instance
        # Derive app name at registration time for reliable labeling later
        # Resolve app name once by matching the block class module
        from django.apps import apps as django_apps
        module = getattr(block_instance.__class__, "__module__", "")
        cfg = None
        for candidate in django_apps.get_app_configs():
            mod_name = getattr(candidate.module, "__name__", "")
            if module.startswith(mod_name):
                cfg = candidate
                break
        app_label = cfg.label if cfg else None
        app_name = (getattr(cfg, "verbose_name", None) or app_label) if cfg else None

        self._metadata[block_id] = {
            "supported_features": getattr(block_instance, "supported_features", []),
            "class": block_instance.__class__.__name__,
            "app_name": app_name,
            "app_label": app_label,
        }

    def get(self, block_id):
        """Return the block registered under ``block_id`` if any."""

        entry = self._blocks.get(block_id)
        return entry

    def metadata(self, block_id):
        """Return metadata for ``block_id`` if present."""

        return self._metadata.get(block_id, {})

    def all(self):
        """Return a copy of the internal registry mapping ids to instances."""

        return dict(self._blocks)

    def all_metadata(self):
        """Return metadata for all registered blocks."""

        return dict(self._metadata)


# Global registry instance used throughout the project.
block_registry = BlockRegistry()


__all__ = ["BlockRegistry", "block_registry"]

