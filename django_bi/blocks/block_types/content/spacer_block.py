from django_bi.blocks.base import BaseBlock


class SpacerBlock(BaseBlock):
    """A simple content block that renders empty space.

    The actual vertical space on layouts is controlled by the layout tile's
    height (Gridstack `gs-h`). Place this block and adjust its height in the
    layout editor to create vertical gaps between rows.
    """

    template_name = "blocks/content/spacer.html"
    supported_features: list[str] = []

    def __init__(self, block_name: str = "spacer"):
        self.block_name = block_name

    def get_config(self, request, instance_id=None):
        return {"block_name": getattr(self, "block_name", "spacer"), "instance_id": instance_id}

    def get_data(self, request, instance_id=None):
        return {}


__all__ = ["SpacerBlock"]

