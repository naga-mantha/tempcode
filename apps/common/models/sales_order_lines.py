from django.db import models
from apps.common.models import Item, Currency, SalesOrder
from django_pandas.managers import DataFrameManager

class SalesOrderLine(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, blank=True, null=True)
    sales_order_line = models.PositiveIntegerField(blank=True, null=True)
    sequence = models.PositiveIntegerField(blank=True, null=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, blank=True, null=True)
    d1_date = models.DateField(blank=True, null=True)
    d2_date = models.DateField(blank=True, null=True)
    d3_date = models.DateField(blank=True, null=True)
    d4_date = models.DateField(blank=True, null=True)
    total_quantity = models.FloatField(blank=True, null=True)
    delivered_quantity = models.FloatField(blank=True, null=True)
    back_order = models.FloatField(blank=True, null=True)
    unit_price = models.FloatField(blank=True, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, blank=True, null=True)
    customer_po = models.CharField(max_length=20, blank=True, default="")
    customer_po_line = models.CharField(max_length=20, blank=True, default="")
    total_amount_cad = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('sales_order', 'sales_order_line', 'sequence',), name='unique_sales_order_line_sequence'),
        ]

    def __str__(self):
        """String for representing the Model object."""
        return str(self.sales_order)