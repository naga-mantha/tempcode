from django.db import models
from django.db.models import Q, F


class BaseOrderCategory(models.Model):
    """Abstract base for order categories per domain.

    Replaces the prior single-table, content-type based OrderCategory with
    three domain-specific tables to strengthen referential integrity and allow
    domain-specific evolution.
    """

    code = models.CharField(max_length=3, blank=True, default="")
    description = models.CharField(max_length=50, blank=True, default="")
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("code",)

    def __str__(self):  # pragma: no cover
        return f"{self.code} - {self.description}" if self.description else self.code


class PurchaseOrderCategory(BaseOrderCategory):
    class Meta(BaseOrderCategory.Meta):
        constraints = [
            models.UniqueConstraint(fields=["code", "parent"], name="unique_purchase_order_category"),
            models.CheckConstraint(
                name="purchaseordercategory_no_self_parent",
                check=~Q(pk=F("parent")),
            ),
        ]


class SalesOrderCategory(BaseOrderCategory):
    class Meta(BaseOrderCategory.Meta):
        constraints = [
            models.UniqueConstraint(fields=["code", "parent"], name="unique_sales_order_category"),
            models.CheckConstraint(
                name="salesordercategory_no_self_parent",
                check=~Q(pk=F("parent")),
            ),
        ]


class ProductionOrderCategory(BaseOrderCategory):
    class Meta(BaseOrderCategory.Meta):
        constraints = [
            models.UniqueConstraint(fields=["code", "parent"], name="unique_production_order_category"),
            models.CheckConstraint(
                name="productionordercategory_no_self_parent",
                check=~Q(pk=F("parent")),
            ),
        ]
