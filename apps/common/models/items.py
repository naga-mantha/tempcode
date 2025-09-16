from django.db import models
from apps.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager


class Item(WorkflowModelMixin):
    code = models.CharField(max_length=100, verbose_name="Item Code")
    description = models.CharField(max_length=100, blank=True, null=True, default="", verbose_name="Item Description")

    # New relations
    item_group = models.ForeignKey(
        'common.ItemGroup', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Item Group"
    )
    type = models.ForeignKey(
        'common.ItemType', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Item Type"
    )

    objects = models.Manager()
    df_objects = DataFrameManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code'], name='unique_item'),
        ]

    def __str__(self):
        return str(self.code)
