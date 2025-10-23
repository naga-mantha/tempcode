from django.db import models
from django.utils import timezone
from django_bi.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager
from apps.common.models.auto_compute_mixin import AutoComputeMixin
from apps.common.models.purchase_order_lines import PurchaseOrderLine


class Receipt(models.Model):
    number = models.CharField(max_length=50, unique=True, verbose_name="Receipt Number")
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

    name = models.CharField(max_length=50, unique=True, verbose_name="Supplier OTD Classification Name")
    priority = models.PositiveIntegerField(default=0, help_text="Lower runs first")
    active = models.BooleanField(default=True)
    counts_for_ontime = models.BooleanField(default=False, help_text="If true, rows with this class count toward OTD%", verbose_name="Counts for OTD%")

    min_days = models.IntegerField(null=True, blank=True, verbose_name="Minimum Days Offset")
    min_inclusive = models.BooleanField(default=True, verbose_name="Min Inclusive")
    max_days = models.IntegerField(null=True, blank=True, verbose_name="Maximum Days Offset")
    max_inclusive = models.BooleanField(default=True, verbose_name="Max Inclusive")

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
    home_currency_code = models.CharField(max_length=5, default="CAD")

    def __str__(self):
        return (
            f"Global Settings (FY start {self.fiscal_year_start_month}/{self.fiscal_year_start_day}, "
            f"home {self.home_currency_code})"
        )


class ReceiptLine(AutoComputeMixin, WorkflowModelMixin):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name="lines")
    line = models.PositiveIntegerField(verbose_name="Receipt Line")
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.PROTECT, related_name="receipt_lines", db_index=True, verbose_name="PO Line (Obj)")
    received_quantity = models.FloatField(blank=True, null=True, verbose_name="Received Quantity")
    receipt_date = models.DateField(blank=True, null=True, db_index=True, verbose_name="Receipt Date")

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

    def classify(self, days_offset: int):
        if days_offset is None:
            return None
        qs = PurchaseTimelinessClassification.objects.filter(active=True).order_by("priority", "id")
        for rule in qs:
            if rule.matches(days_offset):
                return rule
        return None

    def compute_classification(self):
        days = self.days_offset
        if days is None:
            days = self.compute_days_offset()
        return self.classify(days)

    # Declare auto-computed fields for the mixin
    AUTO_COMPUTE = {
        "days_offset": "compute_days_offset",
        "classification": "compute_classification",
    }
