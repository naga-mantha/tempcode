from django.db import models


class FieldDisplayRuleManager(models.Manager):
    def for_model(self, model_label: str):
        """Return rules for the given ``model_label``."""
        return self.filter(model_label=model_label)


class FieldDisplayRule(models.Model):
    model_label = models.CharField(max_length=255)  # ex: "production.ProductionOrder"
    field_name = models.CharField(max_length=255)
    is_mandatory = models.BooleanField(default=False)
    is_excluded = models.BooleanField(default=False)  # means HIDDEN

    objects = FieldDisplayRuleManager()

    class Meta:
        unique_together = ("model_label", "field_name")

    def __str__(self):
        return f"{self.model_label} → {self.field_name}"

