from django.db import models
from django_bi.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class UOM(WorkflowModelMixin):
    code = models.CharField(max_length=10, unique=True)  # EA, KG, M, L, HR, BOX
    name = models.CharField(max_length=60)  # Each, Kilogram, Metre, Litre, Hour, Box
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code', ), name='unique_uom_code'),
        ]

    def __str__(self):
        return str(self.code)