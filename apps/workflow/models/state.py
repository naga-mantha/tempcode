from django.db import models
from apps.workflow.models import Workflow

class State(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, related_name="states")
    name = models.CharField(max_length=100, verbose_name="WF State Name")
    is_start = models.BooleanField(default=False, verbose_name="WF State Start")
    is_end = models.BooleanField(default=False, verbose_name="WF State End")

    objects = models.Manager()

    class Meta:
        unique_together = ("workflow", "name")

    def __str__(self):
        return f"{self.workflow.name}: {self.name}"
