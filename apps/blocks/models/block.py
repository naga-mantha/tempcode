from django.db import models


class Block(models.Model):
    code = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    # V2: registry sync + display controls
    enabled = models.BooleanField(default=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True, default="")
    # When True, DB values (name/description/category) are used over registry defaults
    override_display = models.BooleanField(default=True, null=True)

    def __str__(self):
        # Prefer human-readable name; fall back to code if missing
        return self.name or self.code
