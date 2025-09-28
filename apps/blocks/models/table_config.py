from django.db import models, transaction

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.models.block import Block


class BlockTableConfig(models.Model):
    VISIBILITY_PRIVATE = "private"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = (
        (VISIBILITY_PRIVATE, "Private"),
        (VISIBILITY_PUBLIC, "Public"),
    )

    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name="table_configs")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    columns = models.JSONField(default=list)  # ordered list of keys
    visibility = models.CharField(max_length=7, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["block", "user", "name"], name="unique_tablecfg_per_user"),
            models.UniqueConstraint(
                fields=["block", "user"],
                condition=models.Q(is_default=True),
                name="unique_default_tablecfg_per_user",
            ),
        ]

    def save(self, *args, **kwargs):  # noqa: D401
        """Ensure a single default per (block, user)."""
        model = self.__class__
        with transaction.atomic():
            if self.is_default:
                model.objects.select_for_update().filter(block=self.block, user=self.user).exclude(pk=self.pk).update(is_default=False)
            # If this is the only config, enforce default
            if model.objects.filter(block=self.block, user=self.user).count() == 0:
                self.is_default = True
            super().save(*args, **kwargs)

