from django.db import models


class SoValidateAggregate(models.Model):
    """Monthly aggregate of back_order per item and company.

    One row represents the summed back_order for an (item, company, period-month).
    We keep this as a fact table (long form) to avoid schema churn and enable fast filters.
    """

    COMPANY_CHOICES = (
        ("Collins", "Collins"),
        ("MAI", "MAI"),
    )

    item = models.ForeignKey(
        "common.Item",
        on_delete=models.CASCADE,
        related_name="so_validate_aggregates",
    )
    company = models.CharField(max_length=32, choices=COMPANY_CHOICES)
    # Store first day of month
    period = models.DateField()
    # Summed back_order value for that month
    value = models.DecimalField(max_digits=20, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SO Validator Aggregate"
        verbose_name_plural = "SO Validator Aggregates"
        unique_together = ("item", "company", "period")
        indexes = [
            models.Index(fields=["period"]),
            models.Index(fields=["company", "period"]),
            models.Index(fields=["item", "period"]),
        ]

    def __str__(self) -> str:
        return f"{self.item_id} {self.company} {self.period}: {self.value}"

