# apps/production/models/field_display_rule.py

from django.db import models

class FieldDisplayRule(models.Model):
    model_label = models.CharField(max_length=255)  # ex: "production.ProductionOrder"
    field_name = models.CharField(max_length=255)
    is_mandatory = models.BooleanField(default=False)
    is_excluded = models.BooleanField(default=False)  # means HIDDEN

    class Meta:
        unique_together = ("model_label", "field_name")

    def __str__(self):
        return f"{self.model_label} → {self.field_name}"

    def get_field_display_rules(model_label):
        return FieldDisplayRule.objects.filter(model=model_label)