from django.db import models
from apps.django_bi.workflow.models import WorkflowModelMixin
from apps.common.models import CalendarDay, ShiftTemplate, Labor
from django_pandas.managers import DataFrameManager

class CalendarShift(WorkflowModelMixin):
    calendar_day = models.ForeignKey(CalendarDay, on_delete=models.PROTECT, related_name="shifts")
    shift_template = models.ForeignKey(ShiftTemplate, on_delete=models.PROTECT)
    labours = models.ManyToManyField(Labor, blank=True, related_name="assigned_shifts")

    objects = models.Manager()
    df_objects = DataFrameManager()

    def __str__(self):
        return str(self.calendar_day)
