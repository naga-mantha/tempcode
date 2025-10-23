from django.db import models
from django_bi.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager
from apps.common.models import Labor

class LaborVacation(WorkflowModelMixin):
    labor = models.ForeignKey(Labor, on_delete=models.PROTECT, related_name="vacations")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    objects = models.Manager()
    df_objects = DataFrameManager()

    def covers(self, date):
        return self.start_date <= date <= self.end_date