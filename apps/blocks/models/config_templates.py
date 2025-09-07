from django.db import models

from apps.blocks.models.block import Block


class ColumnConfigTemplate(models.Model):
    """Admin-defined default column configs per block (optionally per site via key).

    These are cloned to per-user BlockColumnConfig on first use when a user has
    no personal configs for the block yet.
    """

    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default="Default")
    is_default = models.BooleanField(default=True)
    fields = models.JSONField(default=list)
    site_key = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "name", "site_key"],
                name="unique_column_template_per_block_site",
            )
        ]


class PivotConfigTemplate(models.Model):
    """Admin-defined default pivot schemas per block (optionally per site).

    Cloned to per-user PivotConfig on first use.
    """

    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default="Default")
    is_default = models.BooleanField(default=True)
    schema = models.JSONField(default=dict)
    site_key = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "name", "site_key"],
                name="unique_pivot_template_per_block_site",
            )
        ]


class RepeaterConfigTemplate(models.Model):
    """Admin-defined default repeater schemas per block (optionally per site).

    Cloned to per-user RepeaterConfig on first use.
    """

    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default="Default")
    is_default = models.BooleanField(default=True)
    schema = models.JSONField(default=dict)
    site_key = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "name", "site_key"],
                name="unique_repeater_template_per_block_site",
            )
        ]

