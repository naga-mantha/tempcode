from django.db import models, transaction
from django.db.models import Q
from django.utils.text import slugify

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.models.block import Block
from .constants import ALLOWED_COLS, RESPONSIVE_COL_FIELDS


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
    # Bootstrap column span (1..12). We will validate via forms to allowed values.
    col = models.PositiveIntegerField(default=12)
    # Optional responsive overrides per breakpoint; when null, inherit from smaller breakpoint
    col_sm = models.PositiveIntegerField(null=True, blank=True)
    col_md = models.PositiveIntegerField(null=True, blank=True)
    col_lg = models.PositiveIntegerField(null=True, blank=True)
    col_xl = models.PositiveIntegerField(null=True, blank=True)
    col_xxl = models.PositiveIntegerField(null=True, blank=True)
    # Optional display metadata
    title = models.CharField(max_length=255, blank=True, default="")
    note = models.TextField(blank=True, default="")
    # Note: vertical sizing not currently used; remove old width/height fields

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.CheckConstraint(
                check=Q(col__in=ALLOWED_COLS), name="layoutblock_col_allowed_values"
            ),
            models.CheckConstraint(
                check=(Q(col_sm__isnull=True) | Q(col_sm__in=ALLOWED_COLS)),
                name="layoutblock_col_sm_allowed_values",
            ),
            models.CheckConstraint(
                check=(Q(col_md__isnull=True) | Q(col_md__in=ALLOWED_COLS)),
                name="layoutblock_col_md_allowed_values",
            ),
            models.CheckConstraint(
                check=(Q(col_lg__isnull=True) | Q(col_lg__in=ALLOWED_COLS)),
                name="layoutblock_col_lg_allowed_values",
            ),
            models.CheckConstraint(
                check=(Q(col_xl__isnull=True) | Q(col_xl__in=ALLOWED_COLS)),
                name="layoutblock_col_xl_allowed_values",
            ),
            models.CheckConstraint(
                check=(Q(col_xxl__isnull=True) | Q(col_xxl__in=ALLOWED_COLS)),
                name="layoutblock_col_xxl_allowed_values",
            ),
        ]
        indexes = [
            models.Index(fields=["layout", "position"], name="layout_pos_idx")
        ]

    def bootstrap_col_classes(self) -> str:
        parts = [f"col-{self.col}"]
        for fname in RESPONSIVE_COL_FIELDS:
            val = getattr(self, fname, None)
            if val:
                bp = fname.split("_", 1)[1]
                parts.append(f"col-{bp}-{val}")
        return " ".join(parts)


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
