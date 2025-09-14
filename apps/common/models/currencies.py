from django.db import models


class Currency(models.Model):
    code = models.CharField(max_length=5, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def __str__(self):
        return str(self.code)
