from django.db import models

from django_bi.blocks.models.block import Block


class BlockFilterLayoutTemplate(models.Model):
    """Admin-defined filter layout per block (single, authoritative).

    Controls placement of filter fields for a block. One per block.
    """

    block = models.ForeignKey(Block, on_delete=models.CASCADE, unique=True)
    layout = models.JSONField(default=dict)

    def __str__(self):
        return f"Filter Layout for {self.block_id}"

    class Meta:
        verbose_name = "Block Filter Layout Template"
        verbose_name_plural = "Block Filter Layout Templates"
