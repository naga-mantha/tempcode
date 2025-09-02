from django.db import models
from apps.common.models import Item, Currency, SalesOrder
from django_pandas.managers import DataFrameManager

class CustomerPurchaseOrder(models.Model):
    customer_purchase_order = models.CharField(max_length=30, blank=True, default="")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, blank=True, null=True)
    customer = models.CharField(max_length=30, blank=True, default="")
    d2_date = models.DateField(blank=True, null=True)
    back_order = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('customer_purchase_order',), name='unique_customer_purchase_order'),
        ]


    def __str__(self):
        """String for representing the Model object."""
        return str(self.customer_purchase_order)