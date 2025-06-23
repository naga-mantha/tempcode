from django.db import models

class FieldDisplayRule(models.Model):
    model_label = models.CharField(max_length=200)  # e.g. 'accounts.Employee'
    field_name = models.CharField(max_length=100)   # e.g. 'department'
    is_mandatory = models.BooleanField(default=False)
    is_excluded = models.BooleanField(default=False)

    objects = models.Manager()

    class Meta:
        unique_together = ('model_label', 'field_name')

    def __str__(self):
        status = []
        if self.is_mandatory:
            status.append("Mandatory")
        if self.is_excluded:
            status.append("Excluded")
        return f"{self.model_label}.{self.field_name} ({', '.join(status) or 'Normal'})"
