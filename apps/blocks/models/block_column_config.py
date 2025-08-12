from django.db import models

from apps.blocks.models.base_user_config import BaseUserConfig


class BlockColumnConfig(BaseUserConfig):
    """Stores column visibility configuration for a block and user."""

    fields = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "user", "name"],
                name="unique_column_config_per_user_block",
            )
        ]
