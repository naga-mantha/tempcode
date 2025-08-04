from django.db import models
from apps.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class WorkCenter(WorkflowModelMixin):
    code = models.CharField(max_length=20, blank=True, default="")
    name = models.CharField(max_length=100, blank=True, default="")

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code',), name='unique_work_center'),
        ]

    def __str__(self):
        return str(self.code)