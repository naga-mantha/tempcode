from django.db import models
from apps.common.models import BusinessPartner
from apps.accounts.models import CustomUser
from apps.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager

class PurchaseOrder(WorkflowModelMixin):
    order = models.CharField(max_length=10)
    buyer = models.ForeignKey(CustomUser, on_delete=models.PROTECT, blank=True, null=True)
    supplier = models.ForeignKey(BusinessPartner, on_delete=models.PROTECT, blank=True, null=True)
    category = models.ForeignKey('OrderCategory', null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('order', ), name='unique_purchase_order'),
        ]

    def __str__(self):
        return str(self.order)