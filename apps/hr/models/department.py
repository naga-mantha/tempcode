from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def __str__(self):
        """String for representing the Model object."""
        return str(self.name)