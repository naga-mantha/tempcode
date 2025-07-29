from django.db import models
from apps.workflow.models import Workflow, State
from django.contrib.auth.models import Group

class StateFieldPermission(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT)
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="field_permissions")
    field_name = models.CharField(max_length=100)
    can_read = models.ManyToManyField(Group, blank=True, related_name="workflow_field_can_read")
    can_write = models.ManyToManyField(Group, blank=True, related_name="workflow_field_can_write")

    class Meta:
        unique_together = ("workflow", "state", "field_name")
        verbose_name = "WF Field Permission"
        verbose_name_plural = "WF Field Permissions"

    def __str__(self):
        return f"{self.workflow.name} / {self.state.name} / {self.field_name}"
