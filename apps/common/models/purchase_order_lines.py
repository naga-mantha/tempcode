from django.db import models
from apps.common.models import PurchaseOrder, Item, Currency, UOM
from apps.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class PurchaseOrderLine(WorkflowModelMixin):
    STATUS_CHOICES = (
        ("open", "Open"),
        ("closed", "Closed"),
    )
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, blank=True, null=True)
    line = models.PositiveIntegerField(blank=True, null=True)
    sequence = models.PositiveIntegerField(blank=True, null=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open", db_index=True)

    order_date = models.DateField(blank=True, null=True)
    initial_receive_date = models.DateField(blank=True, null=True)
    supplier_confirmed_date = models.DateField(blank=True, null=True)
    modified_receive_date = models.DateField(blank=True, null=True)
    final_receive_date = models.DateField(blank=True, null=True)  # This is the "report date"

    total_quantity = models.FloatField(blank=True, null=True)
    received_quantity = models.FloatField(blank=True, null=True)
    back_order = models.FloatField(blank=True, null=True)

    unit_price = models.FloatField(blank=True, null=True)
    uom = models.ForeignKey(UOM, on_delete=models.PROTECT, blank=True, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, blank=True, null=True)
    amount_original_currency = models.FloatField(blank=True, null=True)
    amount_home_currency = models.FloatField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('order', 'line', 'sequence'), name='unique_purchase_order_line'),
        ]

    def __str__(self):
        return f"{self.order}-{self.line}-{self.sequence}"

    def compute_final_receive_date(self):
        """Return the effective final receive date based on priority rules.

        Priority:
        1) modified_receive_date (if not None)
        2) supplier_confirmed_date (if not None)
        3) initial_receive_date (if not None)
        """
        return (
            self.modified_receive_date
            or self.supplier_confirmed_date
            or self.initial_receive_date
        )

    def save(self, *args, **kwargs):
        # Keep final_receive_date in sync before saving
        self.final_receive_date = self.compute_final_receive_date()
        super().save(*args, **kwargs)
