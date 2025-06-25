from django.db import models
from apps.workflow.models import Workflow
from django.contrib.auth.models import Group

class State(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, related_name="states")
    name = models.CharField(max_length=100)
    is_start = models.BooleanField(default=False)
    is_end = models.BooleanField(default=False)
    allowed_groups = models.ManyToManyField(Group, blank=True,  null=True, help_text="Which groups may *edit* the document when it’s in this state.")

    objects = models.Manager()

    class Meta:
        unique_together = ("workflow", "name")

    def __str__(self):
        return f"{self.workflow.name}: {self.name}"
