from django.db import models

from apps.blocks.models.base_user_config import BaseUserConfig


class BlockFilterConfig(BaseUserConfig):
    """Stores filter configuration for a block and user."""

    values = models.JSONField(default=dict)
