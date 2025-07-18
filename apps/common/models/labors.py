from django.db import models
from apps.workflow.models import WorkflowModel, Workflow, State
from django_pandas.managers import DataFrameManager
from apps.common.models import Calendar, WorkCenter

class Labor(WorkflowModel):
    code = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100)
    workcenter = models.ForeignKey(WorkCenter, on_delete=models.PROTECT, blank=True, null=True)
    calendar = models.ForeignKey(Calendar, on_delete=models.PROTECT, blank=True, null=True)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code',), name='unique_labor_code'),
        ]

    def __str__(self):
        return str(self.code)