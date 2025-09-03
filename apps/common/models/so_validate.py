from django.core.exceptions import ValidationError
from django.db import models
from apps.common.models import Item, BusinessPartner

class SoValidateAggregate(models.Model):
    """Monthly aggregate of back_order per item for a specific parent company.

    Fields:
    - item: the item being aggregated
    - company: the company that the row belongs to (root BusinessPartner: MAI or the customer root)
    - customer: the parent BusinessPartner the aggregation is for (root BusinessPartner)
    - period: first day of month
    - value: summed back_order for that month
    """

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="so_validate_aggregates", blank=False, null=False)
    # Company is a root BusinessPartner (MAI or a customer root)
    company = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE, limit_choices_to={"parent__isnull": True}, related_name="so_validate_company_rows", blank=True, null=True)
    # Customer/root filter this row belongs to (root BusinessPartner)
    customer = models.ForeignKey(BusinessPartner, on_delete=models.PROTECT, limit_choices_to={"parent__isnull": True}, related_name="so_validate_customer_rows", blank=True, null=True)
    period = models.DateField() # Store first day of month (normalize to day=1)
    value = models.DecimalField(max_digits=20, decimal_places=2) # Summed back_order value for that month
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SO Validator Aggregate"
        verbose_name_plural = "SO Validator Aggregates"
        unique_together = ("item", "company", "customer", "period")
        indexes = [
            models.Index(fields=["period"]),
            models.Index(fields=["customer", "period"]),
            models.Index(fields=["company", "period"]),
            models.Index(fields=["item", "period"]),
        ]

    def clean(self):
        # Enforce that company and customer are roots (no parent)
        if self.company_id and getattr(self.company, "parent_id", None):
            raise ValidationError({"company": "Company must be a root BusinessPartner (no parent)."})
        if self.customer_id and getattr(self.customer, "parent_id", None):
            raise ValidationError({"customer": "Customer must be a root BusinessPartner (no parent)."})

    def __str__(self) -> str:
        comp = getattr(self.company, "code", None) or getattr(self.company, "name", "?")
        cust = getattr(self.customer, "code", None) or getattr(self.customer, "name", "?")
        return f"{self.item_id} {comp}/{cust} {self.period}: {self.value}"
