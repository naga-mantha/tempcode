from django.db import models

from apps.blocks.models.base_user_config import BaseUserConfig


class PivotConfig(BaseUserConfig):
    """Stores a saved pivot schema per user + block.

    Visibility allows sharing across users:
    - private: visible/editable only by the owner (non-admins can only create/edit private)
    - public: visible to all users; editable only by staff/admins

    Fields:
    - schema: JSON definition describing rows, cols, and measures.
    """

    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = (
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    )

    schema = models.JSONField(default=dict)
    visibility = models.CharField(
        max_length=7, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "user", "name"],
                name="unique_pivot_config_per_user_block",
            )
        ]
