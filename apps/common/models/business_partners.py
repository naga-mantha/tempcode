from django.db import models

class BusinessPartner(models.Model):
    STATUS = (
        ('-', '-'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )

    code = models.CharField(max_length=15, blank=True, default="")
    name = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS, default='-')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('code',), name='unique_business_partner'),
        ]

    def __str__(self):
        """String for representing the Model object."""
        return str(self.code)