from django.conf import settings
from django.db import models
from apps.django_bi.blocks.models.block import Block


class BlockFilterLayout(models.Model):
    """Per-user filter layout for a block (single per (block,user))."""

    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    layout = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["block", "user"], name="unique_filter_layout_per_user_block"),
        ]

    def __str__(self):
        return f"Filter Layout ({self.user_id}) for {self.block_id}"

