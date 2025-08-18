from django.db import models


class Block(models.Model):
    code = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        # Prefer human-readable name; fall back to code if missing
        return self.name or self.code
