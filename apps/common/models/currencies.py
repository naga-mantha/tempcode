from django.db import models

class Currency(models.Model):
    base_currency = models.CharField(max_length=5)
    quote_currency = models.CharField(max_length=5)
    price = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def __str__(self):
        """String for representing the Model object."""
        return str(self.base_currency)

    @staticmethod
    def convert_amount_to_cad(amount, currency):
        conversion = Currency.objects.get(base_currency=currency).price
        total = float(amount) * float(conversion)

        return float("%.2f" % total)