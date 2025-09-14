from django.db import models
from apps.common.models.currencies import Currency


class ExchangeRate(models.Model):
    base = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="fx_base_rates", blank=True, null=True)
    quote = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="fx_quote_rates", blank=True, null=True)
    rate_date = models.DateField(db_index=True)
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    source = models.CharField(max_length=50, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("base", "quote", "rate_date"), name="unique_exchange_rate"),
        ]
        indexes = [
            models.Index(fields=["base", "quote", "rate_date"], name="idx_rate_pair_date"),
        ]

    def __str__(self) -> str:
        return f"{self.base}/{self.quote} {self.rate} on {self.rate_date}"
