from django.db import models

from apps.django_bi.blocks.models.base_user_config import BaseUserConfig


class BlockColumnConfig(BaseUserConfig):
    """Stores column visibility configuration for a block and user.

    Visibility allows sharing across users:
    - private: visible/editable only by the owner (non-admins can only create/edit private)
    - public: visible to all users; editable only by staff/admins
    """

    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = (
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    )

    fields = models.JSONField(default=list)
    visibility = models.CharField(
        max_length=7, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "user", "name"],
                name="unique_column_config_per_user_block",
            )
        ]

    def delete(self, *args, **kwargs):
        """Allow deleting even the last private config for a user.

        If the deleted row was default and other user-owned configs remain,
        promote the first remaining to default. If none remain, do nothing;
        runtime will fall back to public defaults.
        """
        model = self.__class__
        qs = model.objects.filter(block=self.block, user=self.user)
        was_default = bool(self.is_default)
        # Capture an alternative before deleting
        alternative = qs.exclude(pk=self.pk).order_by("pk").first()
        # Bypass BaseUserConfig.delete restriction and delete at Model level
        super(BaseUserConfig, self).delete(*args, **kwargs)
        if was_default and alternative:
            alternative.is_default = True
            alternative.save(update_fields=["is_default"])
