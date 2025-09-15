from django.db import models


class Program(models.Model):
    code = models.CharField(max_length=100, verbose_name="Program Code")
    name = models.CharField(max_length=100, verbose_name="Program Name")
    budget = models.FloatField(blank=True, null=True, verbose_name="Budget")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["code"], name="unique_program_code"),
        ]
        ordering = ("name",)

    def __str__(self):
        return f"{self.code} - {self.name}"
