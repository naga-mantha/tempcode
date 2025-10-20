"""User-defined dashboard layout model."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class VisibilityChoices(models.TextChoices):
    """Shared visibility options for layout-related models."""

    PRIVATE = "private", "Private"
    PUBLIC = "public", "Public"


def validate_public_visibility(user, *, model_label: str) -> None:
    """Ensure the supplied user can create/update a public resource.

    Parameters
    ----------
    user:
        The acting/owning user instance to validate.
    model_label:
        Human-readable label describing the resource (e.g. "layout").
    """

    if not user:
        raise ValidationError("A user must be provided to evaluate visibility constraints.")

    if not getattr(user, "is_staff", False):
        raise ValidationError(
            {
                "visibility": f"Only staff users can mark {model_label} records as public.",
            }
        )


class Layout(models.Model):
    """A reusable dashboard layout composed of block instances."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="layouts",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=7,
        choices=VisibilityChoices.choices,
        default=VisibilityChoices.PRIVATE,
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Indicates whether this layout should be the default for the owner.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "slug"),
                name="unique_layout_owner_slug",
            ),
        ]
        indexes = [
            models.Index(fields=("owner", "slug"), name="layout_owner_slug_idx"),
        ]
        ordering = ("owner", "name")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.name} ({self.owner})"

    @property
    def is_public(self) -> bool:
        return self.visibility == VisibilityChoices.PUBLIC

    def clean(self):  # noqa: D401 - behaviour described inline
        """Apply validation for visibility changes."""

        super().clean()
        if self.visibility == VisibilityChoices.PUBLIC:
            validate_public_visibility(self.owner, model_label="layout")

    def save(self, *args, **kwargs):
        # Ensure visibility rules are enforced when saving without explicit clean()
        self.clean()

        if self.is_default:
            # Maintain a single default per owner.
            Layout.objects.filter(owner=self.owner, is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )

        super().save(*args, **kwargs)
