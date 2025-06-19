from django.db import models
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

class FieldPermission(models.Model):
    """
    For a given model + permlevel + role, define exactly which actions are allowed.
    Actions: 'read','write','add','change','delete','view'
    """
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Which model this permission mapping applies to"
    )
    permlevel = models.PositiveSmallIntegerField(
        help_text="Matches the permlevel in FieldPermLevel"
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        help_text="User group (role) this entry applies to"
    )
    actions = models.JSONField(
        default=list,
        help_text="List of allowed actions (e.g. ['read','write','add','change','delete','view'])"
    )

    class Meta:
        unique_together = ("content_type", "permlevel", "group")
        ordering = ("content_type", "permlevel", "group__name")

    def __str__(self):
        acts = ", ".join(self.actions)
        return f"{self.content_type.app_label}.{self.content_type.model} @ L{self.permlevel} → {self.group.name}: [{acts}]"
