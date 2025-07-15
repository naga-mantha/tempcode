from django.db import models
from django.contrib.contenttypes.models import ContentType

class Workflow(models.Model):
    ACTIVE   = "active"
    DEPRECATED = "deprecated"
    INACTIVE = "inactive"
    STATUS_CHOICES = [
        (ACTIVE,   "Active"),
        (DEPRECATED, "Deprecated"),
        (INACTIVE, "Inactive"),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="WF Name")
    content_type = models.ForeignKey(ContentType, blank=True, null=True, on_delete=models.PROTECT, help_text="Which Django model this workflow is for", verbose_name="WF Model")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE, help_text="“Active” allows creation & transitions; “Deprecated” allows transitions only; “Inactive” disallows both.", verbose_name="WF Status")

    objects = models.Manager()

    def __str__(self):
        return self.name
