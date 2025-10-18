from django.db import models


class Item(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    item_group = models.ForeignKey(
        "blocks.ItemGroup", on_delete=models.PROTECT, related_name="items", null=True, blank=True
    )
    type = models.ForeignKey(
        "blocks.ItemType", on_delete=models.PROTECT, related_name="items", null=True, blank=True
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "Item"
        verbose_name_plural = "Items"

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return self.code
