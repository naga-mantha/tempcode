from django.db import models
from django_bi.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class SalesOrder(WorkflowModelMixin):
    order = models.CharField(max_length=10)
    customer = models.ForeignKey('BusinessPartner', null=True, blank=True, on_delete=models.PROTECT)
    category = models.ForeignKey('SalesOrderCategory', null=True, blank=True, on_delete=models.PROTECT)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('order', ), name='unique_sales_order'),
        ]

    def __str__(self):
        return str(self.order)
