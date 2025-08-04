from django.db import models
from apps.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager
from apps.common.models.calendars import Calendar

class Machine(WorkflowModelMixin):
    code = models.CharField(max_length=20, blank=True, default="")
    name = models.CharField(max_length=100, blank=True, default="")
    calendar = models.ForeignKey(Calendar, on_delete=models.PROTECT)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code',), name='unique_machine'),
        ]

    def __str__(self):
        return str(self.code)