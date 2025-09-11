from django.db import models
from django.db.models import Q

from apps.common.models.items import Item
from apps.common.models.unit_of_measuries import UOM
from apps.common.models.purchase_order_lines import PurchaseOrderLine
from apps.common.models.production_orders import ProductionOrder
from apps.common.models.business_partners import BusinessPartner
from apps.accounts.models import CustomUser


class MrpRescheduleDaysClassification(models.Model):
    """Classification rules for MRP reschedule delta days.

    A rule matches when the provided days value falls within the bounds.
    - If min_days is None, there is no lower bound.
    - If max_days is None, there is no upper bound.
    Bounds are inclusive when specified.
    """

    name = models.CharField(max_length=50, unique=True)
    min_days = models.IntegerField(null=True, blank=True)
    max_days = models.IntegerField(null=True, blank=True)

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


class PlannedOrder(models.Model):
    TYPE_CHOICES = (
        ("PPUR", "Planned Purchase Order"),
        ("PPRO", "Planned Production Order"),
    )

    order = models.CharField(max_length=20, verbose_name='Order')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, blank=True, null=True)
    quantity = models.FloatField(blank=True, null=True)
    uom = models.ForeignKey(UOM, on_delete=models.PROTECT, blank=True, null=True)
    type = models.CharField(max_length=4, choices=TYPE_CHOICES, blank=True, null=True)

    buyer = models.ForeignKey(CustomUser, on_delete=models.PROTECT, blank=True, null=True)
    supplier = models.ForeignKey(BusinessPartner, on_delete=models.PROTECT, blank=True, null=True)

    planned_start_date = models.DateField(blank=True, null=True)
    planned_end_date = models.DateField(blank=True, null=True)
    required_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("order", "type"), name="unique_planned_order_per_type"),
        ]

    def __str__(self):
        return f"{self.order} ({self.get_type_display()})"


class MrpMessage(models.Model):
    DIRECTION_CHOICES = (
        ("PULL_IN", "Pull In"),
        ("PUSH_OUT", "Push Out"),
    )

    # Typed relations: exactly one of these must be set
    pol = models.OneToOneField(
        PurchaseOrderLine,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mrp_message",
    )
    production_order = models.OneToOneField(
        ProductionOrder,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mrp_message",
    )

    mrp_message = models.TextField(blank=True, default="")
    mrp_reschedule_date = models.DateField(blank=True, null=True, db_index=True)

    reschedule_delta_days = models.IntegerField(blank=True, null=True, db_index=True)
    direction = models.CharField(max_length=8, choices=DIRECTION_CHOICES, blank=True, null=True, db_index=True)
    classification = models.ForeignKey(
        MrpRescheduleDaysClassification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mrp_messages",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(pol__isnull=False) & Q(production_order__isnull=True))
                    | (Q(pol__isnull=True) & Q(production_order__isnull=False))
                ),
                name="mrp_message_exactly_one_target",
            ),
        ]

    def __str__(self):
        return f"MRP Message for {self.model_label}: {self.mrp_message[:30]}".strip()

    @property
    def model_label(self) -> str:
        if self.pol_id:
            return "Purchase Order Line"
        if self.production_order_id:
            return "Production Order"
        return "Object"

    def _compute_delta_and_direction(self):
        # Only applicable for PurchaseOrderLine
        pol = self.pol
        if not pol or not self.mrp_reschedule_date:
            return None, None
        final_date = getattr(pol, "final_receive_date", None)
        if not final_date:
            return None, None
        delta_days = (self.mrp_reschedule_date - final_date).days
        direction = "PULL_IN" if delta_days < 0 else "PUSH_OUT"
        return delta_days, direction

    def _classify_reschedule(self, days: int):
        if days is None:
            return None
        qs = MrpRescheduleDaysClassification.objects.all().order_by("min_days", "id")
        for rule in qs:
            if rule.matches(days):
                return rule
        return None

    def save(self, *args, **kwargs):
        delta, direction = self._compute_delta_and_direction()
        self.reschedule_delta_days = delta
        self.direction = direction
        self.classification = self._classify_reschedule(abs(delta))
        super().save(*args, **kwargs)
