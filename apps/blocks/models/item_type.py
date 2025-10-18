from django.db import models


class ItemType(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["code"]
        verbose_name = "Item Type"
        verbose_name_plural = "Item Types"

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return self.code
