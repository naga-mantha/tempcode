from django.db import models

from apps.blocks.models.base_user_config import BaseUserConfig


class PivotConfig(BaseUserConfig):
    """Stores a saved pivot schema per user + block.

    Fields:
    - schema: JSON definition describing rows, cols, and measures.
    """

    schema = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "user", "name"],
                name="unique_pivot_config_per_user_block",
            )
        ]
