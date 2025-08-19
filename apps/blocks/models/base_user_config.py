"""Common user configuration model for Blocks.

This abstract model encapsulates fields and behaviour shared by user
configuration models such as ``BlockColumnConfig`` and
``BlockFilterConfig``.  The subclasses only need to declare their
specific data payload (e.g. ``fields`` or ``values``).
"""

from django.db import models

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.models.block import Block


class BaseUserConfig(models.Model):
    """Abstract base class for user-specific block configurations."""

    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    class Meta:
        abstract = True

    # ------------------------------------------------------------------
    # Common behaviour
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):  # noqa: D401 - behaviour documented in child
        """Persist the configuration ensuring a single default per user.

        When saving a new configuration and none exist for the user and block,
        it becomes the default. If an existing configuration is marked as the
        new default, all other configurations for the same user and block are
        updated to not be default.
        """

        model = self.__class__

        if not self.pk:
            if not model.objects.filter(block=self.block, user=self.user).exists():
                self.is_default = True
        else:
            if self.is_default:
                model.objects.filter(block=self.block, user=self.user).exclude(pk=self.pk).update(
                    is_default=False
                )
            # If this is the only config, it must remain default
            if model.objects.filter(block=self.block, user=self.user).count() == 1:
                self.is_default = True

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # noqa: D401 - behaviour documented in child
        """Delete the configuration ensuring another default if required."""

        model = self.__class__
        configs = model.objects.filter(block=self.block, user=self.user)
        if configs.count() <= 1:
            raise Exception("At least one configuration must exist.")

        was_default = self.is_default
        super().delete(*args, **kwargs)

        if was_default:
            new_default = configs.exclude(pk=self.pk).order_by("pk").first()
            if new_default:
                new_default.is_default = True
                new_default.save()

