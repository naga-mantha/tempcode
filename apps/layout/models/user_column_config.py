# layout/models/user_column_config.py
from django.db import models
from apps.accounts.models import CustomUser
from .table_view_config import TableViewConfig

class UserColumnConfig(models.Model):
    user = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.CASCADE)
    table_config = models.ForeignKey(TableViewConfig, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g., "Compact View"
    fields = models.JSONField(default=list)  # list of field names in order
    is_default = models.BooleanField(default=False)

    objects = models.Manager()

    def __str__(self):
        return f"{self.name} ({self.user})"

    class Meta:
        unique_together = ('user', 'table_config', 'name')

