from django.db import models
from apps.workflow.models import WorkflowModel, Workflow, State
from apps.common.models import CalendarDay, ShiftTemplate
from django_pandas.managers import DataFrameManager

class CalendarShift(WorkflowModel):
    calendar_day = models.ForeignKey(CalendarDay, on_delete=models.PROTECT, related_name="shifts")
    shift_template = models.ForeignKey(ShiftTemplate, on_delete=models.PROTECT)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    def __str__(self):
        return str(self.calendar_day)
