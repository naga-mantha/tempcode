"""Central registry for block implementations."""


class BlockRegistry:
    """Store block implementations by identifier.

    The registry tracks registered blocks and prevents duplicate
    registrations.  Consumers can look up a block by its identifier or
    iterate over all registered blocks.
    """

    def __init__(self):
        self._blocks = {}

    def register(self, block_id, block_instance):
        """Register ``block_instance`` under ``block_id``.

        Raises ``ValueError`` if ``block_id`` is already present in the
        registry.
        """

        if block_id in self._blocks:
            raise ValueError(f"Block '{block_id}' is already registered")
        self._blocks[block_id] = block_instance

    def get(self, block_id):
        """Return the block registered under ``block_id`` if any."""

        return self._blocks.get(block_id)

    def all(self):
        """Return a copy of the internal registry."""

        return dict(self._blocks)


# Global registry instance used throughout the project.
block_registry = BlockRegistry()


__all__ = ["BlockRegistry", "block_registry"]

