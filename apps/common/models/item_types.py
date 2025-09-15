from django.db import models


class ItemType(models.Model):
    code = models.CharField(max_length=100, verbose_name="Item Type Code")
    description = models.CharField(max_length=100, blank=True, default="", verbose_name="Item Type Description")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["code"], name="unique_item_type"),
        ]
        ordering = ("code",)

    def __str__(self):
        return str(self.code)


