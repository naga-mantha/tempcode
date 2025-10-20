"""Database models for the Blocks Demo app."""

from django.db import models


class DemoBlock(models.Model):
    """A placeholder model for future block-related data."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Demo Block"
        verbose_name_plural = "Demo Blocks"

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name
