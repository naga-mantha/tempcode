from django.db import models
from apps.common.models import Item
from apps.workflow.models import WorkflowModel, Workflow, State
from django_pandas.managers import DataFrameManager
class PurchaseOrderQuerySet(models.QuerySet):
    pass

class PurchaseOrder(WorkflowModel):
    order = models.CharField(max_length=10)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()
    PurchaseOrderQuerySet = PurchaseOrderQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('order', ), name='unique_purchase_order'),
        ]

    def __str__(self):
        return str(self.order)