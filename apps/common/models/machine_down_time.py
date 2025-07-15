from django.db import models
from apps.workflow.models import WorkflowModel, Workflow, State
from apps.common.models import Machine
from django_pandas.managers import DataFrameManager

class MachineDowntime(WorkflowModel):
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT)
    start_dt = models.DateTimeField()
    end_dt = models.DateTimeField()
    description = models.TextField(blank=True)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    def __str__(self):
        return str(self.machine)
