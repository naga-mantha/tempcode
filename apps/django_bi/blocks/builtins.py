"""Built-in, generic blocks provided by apps.django_bi.blocks.

Currently includes small content utilities like a Spacer block.
"""

from apps.django_bi.blocks.block_types.content.spacer_block import SpacerBlock


def register(registry):
    # Register a generic spacer block for layouts
    try:
        registry.register("spacer", SpacerBlock())
    except Exception:
        # Ignore if already registered by another app/startup path
        pass


__all__ = ["register"]

