from django.db import models
from apps.accounts.models import CustomUser
from .table_view_config import TableViewConfig

class UserFilterConfig(models.Model):
    user = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.PROTECT)
    table_config = models.ForeignKey(TableViewConfig, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)  # e.g., "Last 3 Months"
    values = models.JSONField(default=dict)  # e.g., {"status": "active", "months_back": 3}
    is_default = models.BooleanField(default=False)

    objects = models.Manager()

    class Meta:
        unique_together = ('user', 'table_config', 'name')

    def save(self, *args, **kwargs):
        # If marking this one default, clear the flag on all siblings first
        if self.is_default:
            (
                UserFilterConfig.objects
                .filter(user=self.user, table_config=self.table_config)
                .exclude(pk=self.pk)
                .update(is_default=False)
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.user.username})"
