from django.db import models
from django.contrib.contenttypes.models import ContentType

class FieldPermLevel(models.Model):
    """
    Assign exactly one permlevel (integer) to each model.field.
    """
    content_type = models.ForeignKey(
        ContentType, blank=True, null=True,
        on_delete=models.CASCADE,
        help_text="Which model this field belongs to"
    )
    field_name = models.CharField(
        max_length=64,
        help_text="Name of the field (or '__model__' for model-level perms)"
    )
    permlevel = models.PositiveSmallIntegerField(blank=True, null=True,
        help_text="Numeric permission level (e.g. 1,2,3...)"
    )

    class Meta:
        unique_together = ("content_type", "field_name")
        ordering = ("content_type", "permlevel")

    def __str__(self):
        return f"{self.content_type.app_label}.{self.content_type.model}.{self.field_name} @ L{self.permlevel}"

