from django.db import models, transaction
from django.db.models import Q
from django.utils.text import slugify

from apps.accounts.models.custom_user import CustomUser
from apps.django_bi.blocks.models.block import Block
from .constants import GRID_MAX_COL_SPAN, GRID_MAX_ROW_SPAN


class Layout(models.Model):
    """Container for arranging blocks into a page-level layout."""

    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    ]

    name = models.CharField(max_length=255)
    # Slug is auto-derived from name; unique per-user
    slug = models.SlugField(blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="layouts")
    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE
    )
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=255, blank=True, default="")

    def save(self, *args, **kwargs):  # noqa: D401 - override to auto-slugify
        """Persist the layout ensuring slug is derived from name."""
        # Derive slug deterministically from name (lowercase, hyphens)
        self.slug = slugify(self.name or "")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_layout_name_per_user"
            ),
            models.UniqueConstraint(
                fields=["user", "slug"], name="unique_layout_slug_per_user"
            ),
        ]


class LayoutBlock(models.Model):
    """Placement of a block within a layout."""

    layout = models.ForeignKey(Layout, on_delete=models.CASCADE, related_name="blocks")
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    # Absolute sequence of this block within the layout. Lower numbers appear first.
    position = models.PositiveIntegerField(default=0)
    # Gridstack position and size (x,y in grid units; w,h in spans)
    x = models.PositiveIntegerField(default=0)
    y = models.PositiveIntegerField(default=0)
    w = models.PositiveIntegerField(default=4)
    h = models.PositiveIntegerField(default=2)
    # Legacy CSS Grid spans (unused in Gridstack mode; kept to avoid breaking earlier data)
    col_span = models.PositiveIntegerField(default=1)
    row_span = models.PositiveIntegerField(default=1)
    # Optional display metadata
    title = models.CharField(max_length=255, blank=True, default="")
    note = models.TextField(blank=True, default="")
    # Optional per-instance default Block filter selection by name
    # When set, the layout will try to select the viewer's BlockFilterConfig
    # with this name for this block instance.
    preferred_filter_name = models.CharField(max_length=255, blank=True, default="")
    # Optional per-instance default Block column config selection by name
    # When set, the layout will try to select the viewer's BlockColumnConfig
    # with this name for this block instance.
    preferred_column_config_name = models.CharField(max_length=255, blank=True, default="")
    # Note: vertical sizing not currently used; remove old width/height fields

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.CheckConstraint(check=Q(w__gte=1) & Q(w__lte=12), name="layoutblock_w_range"),
            models.CheckConstraint(check=Q(h__gte=1) & Q(h__lte=12), name="layoutblock_h_range"),
            models.CheckConstraint(check=Q(x__gte=0), name="layoutblock_x_nonneg"),
            models.CheckConstraint(check=Q(y__gte=0), name="layoutblock_y_nonneg"),
        ]
        indexes = [
            models.Index(fields=["layout", "position"], name="layout_pos_idx")
        ]

    # bootstrap_col_classes removed in grid refactor


class LayoutFilterConfig(models.Model):
    """Stores filter configuration for a layout and user."""

    layout = models.ForeignKey(Layout, on_delete=models.CASCADE, related_name="filter_configs")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    values = models.JSONField(default=dict)
    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = (
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    )
    visibility = models.CharField(
        max_length=7, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["layout", "user", "name"],
                name="unique_layout_filter_per_user",
            ),
            # Ensure at most one default config per (layout, user)
            models.UniqueConstraint(
                fields=["layout", "user"],
                condition=models.Q(is_default=True),
                name="unique_default_layout_filter_per_user",
            ),
        ]

    def save(self, *args, **kwargs):  # noqa: D401 - behaviour documented here
        """Persist the configuration ensuring a single default per layout/user.

        - If creating the first configuration for this layout+user, mark it
          as default.
        - When marking one as default, ensure all others are unset.
        """
        model = self.__class__
        with transaction.atomic():
            if not self.pk:
                # Lock existing configs for this (layout, user) to avoid races
                existing_qs = model.objects.select_for_update().filter(
                    layout=self.layout, user=self.user
                )
                if not existing_qs.exists():
                    self.is_default = True
            else:
                # If marking as default, unset others within the same transaction
                if self.is_default:
                    model.objects.select_for_update().filter(
                        layout=self.layout, user=self.user
                    ).exclude(pk=self.pk).update(is_default=False)
                # If this is the only config, it must remain default
                if model.objects.filter(layout=self.layout, user=self.user).count() == 1:
                    self.is_default = True
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # noqa: D401 - behaviour documented here
        """Delete the configuration while maintaining a default.

        - Prevent deleting the last remaining configuration for a layout+user.
        - If the deleted configuration was default, promote another to default.
        """
        model = self.__class__
        with transaction.atomic():
            qs = model.objects.select_for_update().filter(layout=self.layout, user=self.user)
            if qs.count() <= 1:
                raise Exception("At least one configuration must exist.")
            was_default = self.is_default
            pk = self.pk
            super().delete(*args, **kwargs)
            if was_default:
                new_default = qs.exclude(pk=pk).order_by("pk").first()
                if new_default:
                    new_default.is_default = True
                    new_default.save()
