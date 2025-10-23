from django.db import models
from apps.common.models import ProductionOrder, Task, Machine, WorkCenter, PurchaseOrderLine
from django_bi.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class ProductionOrderOperationQuerySet(models.QuerySet):
    pass

class ProductionOrderOperation(WorkflowModelMixin):
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.PROTECT, blank=True, null=True, related_name="operations")
    operation = models.PositiveIntegerField(blank=True, null=True)
    task = models.ForeignKey(Task, on_delete=models.PROTECT, blank=True, null=True)
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT, blank=True, null=True, related_name="operations")
    workcenter = models.ForeignKey(WorkCenter, on_delete=models.PROTECT, blank=True, null=True, related_name="operations")
    setup_time = models.FloatField(default=0, blank=True, null=True)
    production_time = models.FloatField(default=0, blank=True, null=True)
    wait_time = models.FloatField(default=0, blank=True, null=True)
    total_time = models.FloatField(default=0, blank=True, null=True) #Sum of setup_time + prod_time + wait_time
    remaining_time = models.FloatField(default=0, blank=True, null=True) # This is the time remaining on the job
    required_start = models.DateTimeField(blank=True, null=True) # Used in MPS (Can read from INFOR)
    required_end = models.DateTimeField(blank=True, null=True) # Used in MPS (Can read from INFOR)
    priority = models.PositiveIntegerField(default=999, help_text="Lower numbers = higher priority. 1 = top priority")
    op_po = models.ForeignKey(PurchaseOrderLine, on_delete=models.PROTECT, blank=True, null=True)

    objects = models.Manager()
    df_objects = DataFrameManager()
    ProductionOrderOperationQuerySet = ProductionOrderOperationQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('production_order', 'operation',), name='unique_production_order_operation'),
        ]

        get_latest_by = 'operation'

    @property
    def prev_operation(self):
        return (
            self.production_order.operations
            .filter(operation__lt=self.operation)
            .order_by("-operation")
            .first()
        )

    @property
    def next_operation(self):
        return (
            self.production_order.operations
            .filter(operation__gt=self.operation)
            .order_by("operation")
            .first()
        )

    def __str__(self):
        return f"{self.production_order}-{self.operation}"
