from django.db import models
from apps.workflow.models import WorkflowModel, Workflow, State
from django_pandas.managers import DataFrameManager

class WorkCenter(WorkflowModel):
    code = models.CharField(max_length=20, blank=True, default="")
    name = models.CharField(max_length=100, blank=True, default="")
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code',), name='unique_work_center'),
        ]

    def __str__(self):
        return str(self.code)