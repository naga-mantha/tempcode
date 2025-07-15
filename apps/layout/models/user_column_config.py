from django.db import models, transaction
from apps.accounts.models import CustomUser
from .table_view_config import TableViewConfig

class UserColumnConfig(models.Model):
    user = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.PROTECT)
    table_config = models.ForeignKey(TableViewConfig, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)  # e.g., "Compact View"
    fields = models.JSONField(default=list)  # list of field names in order
    is_default = models.BooleanField(default=False)

    objects = models.Manager()

    def save(self, *args, **kwargs):
        """
        Ensure that:
         1) If this instance.is_default=True, all its siblings are cleared.
         2) If instance.is_default=False but no other sibling is default,
            this instance is switched back to default so that at least one
            always remains.
        """
        # We want a transaction so these updates stay atomic
        with transaction.atomic():
            # First, save as usual so self.pk is set
            super().save(*args, **kwargs)

            qs = UserColumnConfig.objects.filter(
                user=self.user,
                table_config=self.table_config
            )

            if self.is_default:
                # Clear 'is_default' on all others
                qs.exclude(pk=self.pk).update(is_default=False)
            else:
                # If nobody else is default, this one must be
                if not qs.filter(is_default=True).exists():
                    # Bypass our own save() to avoid recursion:
                    UserColumnConfig.objects.filter(pk=self.pk).update(is_default=True)
                    # Reflect change on this instance in memory
                    self.is_default = True

    def __str__(self):
        return f"{self.name} ({self.user})"

    class Meta:
        unique_together = ('user', 'table_config', 'name')

