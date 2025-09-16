from django.db import models
from django.db.models import Q

from apps.common.models.items import Item
from apps.common.models.unit_of_measuries import UOM
from apps.common.models.purchase_order_lines import PurchaseOrderLine
from apps.common.models.production_orders import ProductionOrder
from apps.common.models.business_partners import BusinessPartner
from apps.accounts.models import CustomUser
from apps.common.models.auto_compute_mixin import AutoComputeMixin


class MrpRescheduleDaysClassification(models.Model):
    """Classification rules for MRP reschedule delta days.

    A rule matches when the provided days value falls within the bounds.
    - If min_days is None, there is no lower bound.
    - If max_days is None, there is no upper bound.
    Bounds are inclusive when specified.
    """

    name = models.CharField(max_length=50, unique=True, verbose_name="MRP Reschedule Days Classification Name")
    min_days = models.IntegerField(null=True, blank=True, verbose_name="Minimum Days")
    max_days = models.IntegerField(null=True, blank=True, verbose_name="Maximum Days")

    class Meta:
        ordering = ("min_days", "id")

    def __str__(self):
        return self.name

    def matches(self, days: int) -> bool:
        if days is None:
            return False
        if self.min_days is not None and days < self.min_days:
            return False
        if self.max_days is not None and days > self.max_days:
            return False
        return True


class BasePlannedOrder(models.Model):
    order = models.CharField(max_length=20, verbose_name='Planned Order')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, blank=True, null=True)
    quantity = models.FloatField(blank=True, null=True, verbose_name="Planned Quantity")
    uom = models.ForeignKey(UOM, on_delete=models.PROTECT, blank=True, null=True)

    buyer = models.ForeignKey(CustomUser, on_delete=models.PROTECT, blank=True, null=True)
    supplier = models.ForeignKey(BusinessPartner, on_delete=models.PROTECT, blank=True, null=True)

    planned_start_date = models.DateField(blank=True, null=True, verbose_name="Planned Start Date")
    planned_end_date = models.DateField(blank=True, null=True, verbose_name="Planned End Date")
    required_date = models.DateField(blank=True, null=True, verbose_name="Required Date")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("order",)

    def __str__(self):
        return f"{self.order}"


class PlannedPurchaseOrder(BasePlannedOrder):
    class Meta(BasePlannedOrder.Meta):
        constraints = [
            models.UniqueConstraint(fields=("order",), name="unique_planned_purchase_order"),
        ]


class PlannedProductionOrder(BasePlannedOrder):
    class Meta(BasePlannedOrder.Meta):
        constraints = [
            models.UniqueConstraint(fields=("order",), name="unique_planned_production_order"),
        ]


class BaseMrpMessage(AutoComputeMixin, models.Model):
    DIRECTION_CHOICES = (
        ("PULL_IN", "Pull In"),
        ("PUSH_OUT", "Push Out"),
    )

    mrp_message = models.TextField(blank=True, default="", null=True, verbose_name="MRP Message")
    mrp_reschedule_date = models.DateField(blank=True, null=True, db_index=True, verbose_name="MRP Reschedule Date")

    reschedule_delta_days = models.IntegerField(blank=True, null=True, db_index=True, verbose_name="Reschedule Delta Days")
    direction = models.CharField(max_length=8, choices=DIRECTION_CHOICES, blank=True, null=True, db_index=True, verbose_name="Reschedule Direction")
    classification = models.ForeignKey(
        MrpRescheduleDaysClassification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-mrp_reschedule_date", "id")

    # --- Auto-compute helpers (generic) ---
    def compute_reschedule_delta_days(self):
        return None

    def compute_direction(self):
        delta = getattr(self, "reschedule_delta_days", None)
        if delta is None:
            try:
                delta = self.compute_reschedule_delta_days()
            except Exception:
                delta = None
        if delta is None:
            return None
        return "PULL_IN" if delta < 0 else "PUSH_OUT"

    def compute_classification(self):
        try:
            days = getattr(self, "reschedule_delta_days", None)
            if days is None:
                days = self.compute_reschedule_delta_days()
            if days is None:
                return None
            abs_days = abs(days)
        except Exception:
            return None
        qs = MrpRescheduleDaysClassification.objects.all().order_by("min_days", "id")
        for rule in qs:
            if rule.matches(abs_days):
                return rule
        return None


class PurchaseMrpMessage(BaseMrpMessage):
    pol = models.OneToOneField(
        PurchaseOrderLine,
        on_delete=models.PROTECT,
        related_name="mrp_message",
    )

    def __str__(self):
        msg = (self.mrp_message or "")
        try:
            msg = msg[:30]
        except Exception:
            msg = str(msg)[:30]
        return f"MRP Message for PO Line {self.pol_id}: {msg}".strip()

    def compute_reschedule_delta_days(self):
        pol = self.pol
        if not pol or not self.mrp_reschedule_date:
            return None
        final_date = getattr(pol, "final_receive_date", None)
        if not final_date and hasattr(pol, "compute_final_receive_date"):
            final_date = pol.compute_final_receive_date()
        if not final_date:
            return None
        return (self.mrp_reschedule_date - final_date).days

    # Fields to auto-compute on save unless overridden by recalc policy
    AUTO_COMPUTE = {
        "reschedule_delta_days": "compute_reschedule_delta_days",
        "direction": "compute_direction",
        "classification": "compute_classification",
    }


class ProductionMrpMessage(BaseMrpMessage):
    production_order = models.OneToOneField(
        ProductionOrder,
        on_delete=models.PROTECT,
        related_name="mrp_message",
    )

    def __str__(self):
        msg = (self.mrp_message or "")
        try:
            msg = msg[:30]
        except Exception:
            msg = str(msg)[:30]
        return f"MRP Message for Prod Order {self.production_order_id}: {msg}".strip()
