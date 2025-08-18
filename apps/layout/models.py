from django.db import models
from django.utils.text import slugify

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.models.block import Block


class Layout(models.Model):
    """Container for arranging blocks into a page-level layout."""

    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="layouts")
    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE
    )

    def save(self, *args, **kwargs):  # noqa: D401 - override to auto-slugify
        """Persist the layout ensuring a unique slug is generated."""
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Layout.objects.filter(slug=slug).exists():
                counter += 1
                slug = f"{base}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class LayoutBlock(models.Model):
    """Placement of a block within a layout."""

    layout = models.ForeignKey(Layout, on_delete=models.CASCADE, related_name="blocks")
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    row = models.PositiveIntegerField(default=0)
    col = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=12)
    height = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["row", "col"]


class LayoutFilterConfig(models.Model):
    """Stores filter configuration for a layout and user."""

    layout = models.ForeignKey(Layout, on_delete=models.CASCADE, related_name="filter_configs")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    values = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["layout", "user", "name"],
                name="unique_layout_filter_per_user",
            )
        ]

    def save(self, *args, **kwargs):  # noqa: D401 - behaviour documented here
        """Persist the configuration ensuring a single default per layout/user."""
        if not self.pk:
            if not LayoutFilterConfig.objects.filter(layout=self.layout, user=self.user).exists():
                self.is_default = True
        elif self.is_default:
            LayoutFilterConfig.objects.filter(layout=self.layout, user=self.user).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)
