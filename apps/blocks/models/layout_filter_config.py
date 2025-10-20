"""Filter presets scoped to layouts."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.blocks.models.layout import Layout, VisibilityChoices, validate_public_visibility


class LayoutFilterConfig(models.Model):
    """Saved filter configuration associated with a layout."""

    layout = models.ForeignKey(
        Layout,
        on_delete=models.CASCADE,
        related_name="filter_configs",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="layout_filter_configs",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=7,
        choices=VisibilityChoices.choices,
        default=VisibilityChoices.PRIVATE,
    )
    is_default = models.BooleanField(default=False)
    values = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("layout", "slug"),
                name="unique_layout_filter_config_slug",
            ),
            models.UniqueConstraint(
                fields=("layout", "owner", "name"),
                name="unique_layout_filter_config_name_per_owner",
            ),
        ]
        ordering = ("layout", "owner", "name")

    def __str__(self) -> str:
        return f"{self.layout.name}: {self.name}"

    # ------------------------------------------------------------------
    # Validation and persistence helpers
    # ------------------------------------------------------------------
    def clean(self):  # noqa: D401 - behaviour described inline
        """Validate ownership + visibility invariants."""

        super().clean()
        if self.visibility == VisibilityChoices.PUBLIC:
            validate_public_visibility(self.owner, model_label="layout filter config")

        if self.owner_id and self.layout_id and self.owner_id != self.layout.owner_id:
            raise ValidationError({"owner": "Filter configs must be owned by the layout owner."})

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            qs = LayoutFilterConfig.objects.select_for_update().filter(
                layout=self.layout,
                owner=self.owner,
            )
            if not self.pk and not qs.exists():
                self.is_default = True

            super().save(*args, **kwargs)

            if self.is_default:
                qs.exclude(pk=self.pk).update(is_default=False)

    def delete(self, using=None, keep_parents=False):
        with transaction.atomic():
            qs = LayoutFilterConfig.objects.select_for_update().filter(
                layout=self.layout,
                owner=self.owner,
            )
            was_default = bool(self.is_default)
            super().delete(using=using, keep_parents=keep_parents)
            if was_default:
                fallback = qs.exclude(pk=self.pk).order_by("pk").first()
                if fallback:
                    fallback.is_default = True
                    fallback.save(update_fields=["is_default"])
