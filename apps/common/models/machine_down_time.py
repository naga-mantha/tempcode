from django.db import models
from apps.django_bi.workflow.models import WorkflowModelMixin
from apps.common.models import Machine
from django_pandas.managers import DataFrameManager

class MachineDowntime(WorkflowModelMixin):
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT)
    start_dt = models.DateTimeField()
    end_dt = models.DateTimeField()
    description = models.TextField(blank=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    def __str__(self):
        return str(self.machine)
