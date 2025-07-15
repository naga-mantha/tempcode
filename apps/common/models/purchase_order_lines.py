from django.db import models
from apps.common.models import PurchaseOrder
from apps.workflow.models import WorkflowModel, Workflow, State
from django_pandas.managers import DataFrameManager
class PurchaseOrderLineQuerySet(models.QuerySet):
    pass

class PurchaseOrderLine(WorkflowModel):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, blank=True, null=True)
    line = models.PositiveIntegerField(blank=True, null=True)
    sequence = models.PositiveIntegerField(blank=True, null=True)
    final_receive_date = models.DateTimeField(blank=True, null=True)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()
    PurchaseOrderLineQuerySet = PurchaseOrderLineQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('order', 'line' , 'sequence'), name='unique_purchase_order_line'),
        ]

    def __str__(self):
        return f"{self.order}-{self.line}-{self.sequence}"
