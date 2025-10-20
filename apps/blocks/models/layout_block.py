"""Block placement model for layouts."""

from django.db import models

from apps.blocks.models.block import Block
from apps.blocks.models.layout import Layout


class LayoutBlock(models.Model):
    """Stores block instances and positioning metadata for a layout."""

    layout = models.ForeignKey(
        Layout,
        on_delete=models.CASCADE,
        related_name="layout_blocks",
    )
    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name="layout_blocks",
    )
    slug = models.SlugField(
        max_length=255,
        help_text="Unique identifier for the block within the layout.",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional custom title displayed for this block instance.",
    )
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Block-specific configuration payload.",
    )
    row_index = models.PositiveIntegerField(
        default=0,
        help_text="Zero-based row index for grid placement.",
    )
    column_index = models.PositiveIntegerField(
        default=0,
        help_text="Zero-based column index for grid placement.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Ordering value applied when rendering blocks in sequence.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("layout", "order", "row_index", "column_index", "slug")
        constraints = [
            models.UniqueConstraint(
                fields=("layout", "slug"),
                name="unique_layout_block_slug",
            )
        ]
        indexes = [
            models.Index(fields=("layout", "order"), name="layout_block_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.layout.name}: {self.slug}"
