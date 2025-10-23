from django.db import models
from apps.django_bi.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class ShiftTemplate(WorkflowModelMixin):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('name',), name='unique_shift_template_name'),
        ]

    def __str__(self):
        return str(self.name)
