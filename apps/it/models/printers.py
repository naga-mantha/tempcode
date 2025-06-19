from django.db import models
from apps.hr.models.department import Department

class Printer(models.Model):
    name = models.CharField(max_length=50, blank=True, default="")
    dept = models.ForeignKey(Department, on_delete=models.PROTECT, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def __str__(self):
        """String for representing the Model object."""
        return str(self.name)