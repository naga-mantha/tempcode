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
    line = models.PositiveIntegerField(blank=True, null=True, verbose_name="PO Line")
    sequence = models.PositiveIntegerField(blank=True, null=True, verbose_name="Sequence")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, blank=True, null=True, verbose_name="Item")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open", db_index=True, verbose_name="Purchase Order Line Status")

    order_date = models.DateField(blank=True, null=True, verbose_name="Order Date")
    initial_receive_date = models.DateField(blank=True, null=True, verbose_name="Initial Receive Date")
    supplier_confirmed_date = models.DateField(blank=True, null=True, verbose_name="Supplier Confirmed Date")
    modified_receive_date = models.DateField(blank=True, null=True, verbose_name="Modified Receive Date")
    final_receive_date = models.DateField(blank=True, null=True, verbose_name="Report Date")  # This is the "report date"

    total_quantity = models.FloatField(blank=True, null=True, verbose_name="Total Quantity")
    received_quantity = models.FloatField(blank=True, null=True, verbose_name="Received Quantity")
    back_order = models.FloatField(blank=True, null=True, verbose_name="Back Order")

    unit_price = models.FloatField(blank=True, null=True, verbose_name="Unit Price")
    uom = models.ForeignKey(UOM, on_delete=models.PROTECT, blank=True, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, blank=True, null=True)
    amount_original_currency = models.FloatField(blank=True, null=True, verbose_name="Amount (Orig. Curr.)")
    amount_home_currency = models.FloatField(blank=True, null=True, verbose_name="Amount (Home Curr.)")
    comments = models.TextField(blank=True, null=True, default="", verbose_name="Comments")

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

    def compute_back_order(self):
        """Return back order as total_quantity - received_quantity, treating NULLs as 0.

        Mirrors the logic used by the fill_back_order management command.
        """
        total = self.total_quantity if self.total_quantity is not None else 0.0
        received = self.received_quantity if self.received_quantity is not None else 0.0
        return total - received

    def save(self, *args, **kwargs):
        # Keep final_receive_date in sync before saving
        self.final_receive_date = self.compute_final_receive_date()
        # Keep back_order in sync before saving
        self.back_order = self.compute_back_order()
        super().save(*args, **kwargs)
