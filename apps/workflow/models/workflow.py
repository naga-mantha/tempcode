from django.db import models
from django.contrib.contenttypes.models import ContentType

class Workflow(models.Model):
    ACTIVE   = "active"
    DEPRECATED = "Deprecated"
    INACTIVE = "inactive"
    STATUS_CHOICES = [
        (ACTIVE,   "Active"),
        (DEPRECATED, "Deprecated"),
        (INACTIVE, "Inactive"),
    ]

    name = models.CharField(max_length=100, unique=True)
    content_type = models.ForeignKey(
        ContentType, blank=True, null=True,
        on_delete=models.CASCADE,
        help_text="Which Django model this workflow is for"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=ACTIVE,
        help_text="“Active” allows creation & transitions; “Deprecated” allows transitions only; “Inactive” disallows both."
    )

    objects = models.Manager()

    def __str__(self):
        return self.name
