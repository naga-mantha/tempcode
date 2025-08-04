from django.db import models
from apps.common.models import Machine
from apps.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class Task(WorkflowModelMixin):
    code = models.CharField(max_length=10, blank=True, default="")
    name = models.CharField(max_length=100, blank=True, default="")
    primary_machine = models.ForeignKey(Machine, on_delete=models.PROTECT, related_name="primary_for_tasks", blank=True, null=True)
    alternate_machines = models.ManyToManyField(Machine, blank=True, null=True, related_name="alternate_for_tasks", help_text="Other machines that can perform this task")

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code',), name='unique_task'),
        ]

    def __str__(self):
        return str(self.code)