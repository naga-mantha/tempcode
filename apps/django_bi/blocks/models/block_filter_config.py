from django.db import models

from apps.django_bi.blocks.models.base_user_config import BaseUserConfig


class BlockFilterConfig(BaseUserConfig):
    """Stores filter configuration for a block and user."""

    values = models.JSONField(default=dict)
    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = (
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    )
    visibility = models.CharField(
        max_length=7, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "user", "name"],
                name="unique_filter_config_per_user_block",
            )
        ]
