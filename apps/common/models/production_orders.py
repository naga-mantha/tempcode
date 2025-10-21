from django.db import models
from apps.common.models import Item
from apps.django_bi.workflow.models import WorkflowModelMixin
from django_pandas.managers import DataFrameManager
class ProductionOrderQuerySet(models.QuerySet):
    pass

class ProductionOrder(WorkflowModelMixin):
    production_order = models.CharField(max_length=10, verbose_name="Prod Order")
    status = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.FloatField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, blank=True, null=True)
    category = models.ForeignKey('ProductionOrderCategory', null=True, blank=True, on_delete=models.PROTECT)

    objects = models.Manager()
    df_objects = DataFrameManager()
    ProductionOrderQuerySet = ProductionOrderQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('production_order', ), name='unique_production_order'),
        ]

    def __str__(self):
        return str(self.production_order)

    def can_user_view(self, user):
            return self.quantity > 100


    def can_user_change(self, user):
        return self.quantity > 1000
