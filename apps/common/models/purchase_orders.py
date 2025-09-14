from django.db import models
from apps.common.models import BusinessPartner, PurchaseOrderCategory
from django.db.models.functions import Length
from apps.accounts.models import CustomUser
from apps.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager
from apps.common.models.auto_compute_mixin import AutoComputeMixin

class PurchaseOrder(AutoComputeMixin, WorkflowModelMixin):
    order = models.CharField(max_length=10, verbose_name="Purchase Order")
    buyer = models.ForeignKey(CustomUser, on_delete=models.PROTECT, blank=True, null=True)
    supplier = models.ForeignKey(BusinessPartner, on_delete=models.PROTECT, blank=True, null=True)
    category = models.ForeignKey('PurchaseOrderCategory', null=True, blank=True, on_delete=models.PROTECT)
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

    # Auto-category assignment based on longest matching numeric prefix.
    # Examples:
    #   Categories: 1, 10, 100, 2
    #   PO=1088  -> match "10"
    #   PO=1883  -> match "1"
    def _compute_category(self):
        order_val = (self.order or "").strip()
        if not order_val:
            return None
        # Find the longest category.code that is a prefix of order_val
        qs = (
            PurchaseOrderCategory.objects
            .annotate(code_len=Length("code"))
            .order_by("-code_len", "parent_id", "id")
        )
        for cat in qs:
            code = (cat.code or "").strip()
            if code and order_val.startswith(code):
                return cat
        return None


    # Declare auto-computed fields for the mixin
    AUTO_COMPUTE = {
        "category": "_compute_category",
    }
