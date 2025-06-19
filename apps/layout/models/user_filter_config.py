from django.db import models
from apps.accounts.models import CustomUser
from .table_view_config import TableViewConfig

class UserFilterConfig(models.Model):
    user = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.CASCADE)
    table_config = models.ForeignKey(TableViewConfig, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g., "Last 3 Months"
    values = models.JSONField(default=dict)  # e.g., {"status": "active", "months_back": 3}
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'table_config', 'name')

    def __str__(self):
        return f"{self.name} ({self.user.username})"
