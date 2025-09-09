from django.db import models
from django.utils import timezone

from apps.common.models.purchase_order_lines import PurchaseOrderLine


class Receipt(models.Model):
    number = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("number",), name="unique_receipt"),
        ]

    def __str__(self):
        return str(self.number)


class PurchaseTimelinessClassification(models.Model):
    """Rule-based classification for receipt timeliness.

    A rule matches when days_offset falls within the configured bounds.
    - If min_days is None, there is no lower bound.
    - If max_days is None, there is no upper bound.
    - Inclusivity flags control boundary behaviour.
    Rules are evaluated by ascending priority; first match wins.
    """

    name = models.CharField(max_length=50, unique=True)
    priority = models.PositiveIntegerField(default=0, help_text="Lower runs first")
    active = models.BooleanField(default=True)
    counts_for_ontime = models.BooleanField(default=False, help_text="If true, rows with this class count toward OTD%")

    min_days = models.IntegerField(null=True, blank=True)
    min_inclusive = models.BooleanField(default=True)
    max_days = models.IntegerField(null=True, blank=True)
    max_inclusive = models.BooleanField(default=True)

    color = models.CharField(max_length=20, blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("priority", "id")

    def __str__(self):
        return f"{self.name} (prio {self.priority})"

    def matches(self, days_offset: int) -> bool:
        if self.min_days is not None:
            if self.min_inclusive:
                if not (days_offset >= self.min_days):
                    return False
            else:
                if not (days_offset > self.min_days):
                    return False
        if self.max_days is not None:
            if self.max_inclusive:
                if not (days_offset <= self.max_days):
                    return False
            else:
                if not (days_offset < self.max_days):
                    return False
        return True


class PurchaseSettings(models.Model):
    """Purchase-specific settings.

    Thresholds for timeliness are defined via PurchaseTimelinessClassification.
    This model holds other purchase KPIs like OTD target.
    """

    otd_target_percent = models.PositiveIntegerField(default=95, help_text="Target OTD percentage")

    def __str__(self):
        return f"Purchase Settings (OTD target {self.otd_target_percent}%)"


class GlobalSettings(models.Model):
    """Global settings used across apps (e.g., fiscal year start)."""

    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1)
    fiscal_year_start_day = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"Global Settings (FY start {self.fiscal_year_start_month}/{self.fiscal_year_start_day})"


class ReceiptLine(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name="lines")
    line = models.PositiveIntegerField()
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.PROTECT, related_name="receipt_lines", db_index=True)

    received_quantity = models.FloatField(blank=True, null=True)
    receipt_date = models.DateField(blank=True, null=True, db_index=True)

    # Derived/computed fields
    days_offset = models.IntegerField(blank=True, null=True)
    amount_home_currency = models.FloatField(blank=True, null=True)
    classification = models.ForeignKey(
        PurchaseTimelinessClassification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_lines",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("receipt", "line"), name="unique_receipt_line"),
        ]

    def __str__(self):
        return f"{self.receipt}-{self.line}"

    # --- Computation helpers ---
    @property
    def supplier(self):
        try:
            return getattr(self.po_line.order, "supplier", None)
        except Exception:
            return None

    @property
    def final_receive_date(self):
        try:
            return getattr(self.po_line, "final_receive_date", None)
        except Exception:
            return None

    def compute_days_offset(self):
        if not self.receipt_date:
            return None
        final_date = self.po_line.final_receive_date
        # Fallback to computed value if model offers method
        if not final_date and hasattr(self.po_line, "compute_final_receive_date"):
            final_date = self.po_line.compute_final_receive_date()
        if not final_date:
            return None
        delta = self.receipt_date - final_date
        return delta.days

    def compute_amount_home_currency(self):
        if self.received_quantity is None:
            return None
        # Prefer explicit unit price in home currency if available
        unit_price_home = getattr(self.po_line, "unit_price_home_currency", None)
        if unit_price_home is not None:
            return unit_price_home * self.received_quantity

        # Derive unit price from PO line totals if possible
        total_amount_home = getattr(self.po_line, "amount_home_currency", None)
        total_qty = getattr(self.po_line, "total_quantity", None)
        if total_amount_home is not None and total_qty:
            try:
                return (total_amount_home / total_qty) * self.received_quantity
            except ZeroDivisionError:
                return None
        return None

    def classify(self, days_offset: int):
        if days_offset is None:
            return None
        qs = PurchaseTimelinessClassification.objects.filter(active=True).order_by("priority", "id")
        for rule in qs:
            if rule.matches(days_offset):
                return rule
        return None

    def save(self, *args, **kwargs):
        # Keep derived fields current before saving
        self.days_offset = self.compute_days_offset()
        self.amount_home_currency = self.compute_amount_home_currency()
        self.classification = self.classify(self.days_offset)
        super().save(*args, **kwargs)
