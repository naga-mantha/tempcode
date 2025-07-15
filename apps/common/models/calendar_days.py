from django.db import models
from apps.workflow.models import WorkflowModel, Workflow, State
from apps.common.models import Calendar
from django_pandas.managers import DataFrameManager

class CalendarDay(WorkflowModel):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="days")
    date = models.DateField()
    is_working_day = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    def __str__(self):
        return str(self.calendar)