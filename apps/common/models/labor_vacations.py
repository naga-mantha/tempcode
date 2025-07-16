from django.db import models
from apps.workflow.models import WorkflowModel, Workflow, State
from django_pandas.managers import DataFrameManager
from apps.common.models import Labor

class LaborVacation(WorkflowModel):
    labor = models.ForeignKey(Labor, on_delete=models.PROTECT, related_name="vacations")
    start_date = models.DateField()
    end_date = models.DateField()
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    def covers(self, date):
        return self.start_date <= date <= self.end_date