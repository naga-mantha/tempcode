from django.db import models

class TableViewConfig(models.Model):
    table_name = models.CharField(max_length=100, unique=True)
    model_label = models.CharField(max_length=255)  # e.g. "accounts.CustomUser"
    title = models.CharField(max_length=255, blank=True, null=True)
    tabulator_options = models.JSONField(default=dict)
    default_columns = models.JSONField(
        default=list,
        help_text="List of field-names, in order, to show by default"
    )

    objects = models.Manager()

    def __str__(self):
        return f"{self.table_name} -> {self.model_label}"

    class Meta:
        unique_together = ('table_name', 'model_label')
