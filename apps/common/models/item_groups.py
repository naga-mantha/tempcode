from django.db import models
from apps.common.models.item_group_types import ItemGroupType
from apps.common.models.programs import Program


class ItemGroup(models.Model):
    code = models.CharField(max_length=100, verbose_name="Item Group Code")
    description = models.CharField(max_length=100, blank=True, default="", verbose_name="Item Group Description")

    type = models.ForeignKey(ItemGroupType, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Item Group Type")
    program = models.ForeignKey(Program, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Program")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["code"], name="unique_item_group"),
        ]
        ordering = ("code",)

    def __str__(self):
        return str(self.code)

