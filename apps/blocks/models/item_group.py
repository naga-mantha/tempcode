from django.db import models


class ItemGroup(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["code"]
        verbose_name = "Item Group"
        verbose_name_plural = "Item Groups"

    def __str__(self) -> str:  # pragma: no cover - simple display helper
        return self.code
