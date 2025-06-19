from django.db import models

class TableViewConfig(models.Model):
    table_name = models.CharField(max_length=100, unique=True)
    model_label = models.CharField(max_length=255)  # e.g. "accounts.CustomUser"
    title = models.CharField(max_length=255, blank=True, null=True)
    tabulator_options = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.table_name} -> {self.model_label}"
