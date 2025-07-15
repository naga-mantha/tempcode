from django.db import models
from apps.common.models import Item
from apps.workflow.models import WorkflowModel, Workflow, State
from django_pandas.managers import DataFrameManager
class ProductionOrderQuerySet(models.QuerySet):
    pass

class ProductionOrder(WorkflowModel):
    production_order = models.CharField(max_length=10)
    part_no = models.ForeignKey(Item, on_delete=models.PROTECT, blank=True, null=True)
    quantity = models.FloatField(blank=True, null=True)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()
    ProductionOrderQuerySet = ProductionOrderQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('production_order', ), name='unique_production_order'),
        ]

    def __str__(self):
        return str(self.production_order)