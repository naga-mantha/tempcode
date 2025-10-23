from django.db import models
from django_bi.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class Calendar(WorkflowModelMixin):
    name = models.CharField(max_length=100)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('name',), name='unique_calendar_name'),
        ]

    def __str__(self):
        return str(self.name)