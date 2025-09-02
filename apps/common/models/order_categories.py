from django.db import models
from django.db.models import Q, F
from django.contrib.contenttypes.models import ContentType

class OrderCategory(models.Model):
    code = models.CharField(max_length=3, blank=True, default="")
    description = models.CharField(max_length=50, blank=True, default="")
    model_ct  = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=Q(app_label__in=["common"]),  # tweak
        verbose_name="Model",
        help_text="Pick the model this refers to.",
    )
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'model_ct', 'parent'], name='unique_category'),

            models.CheckConstraint(
                name="ordercategory_no_self_parent",
                check=~Q(pk=F("parent")),  # forbid a row parenting itself
            ),
        ]

    def __str__(self):
        """String for representing the Model object."""
        return str(self.code) + "-" + str(self.model_ct) + "-" + str(self.parent)

    @staticmethod
    def get_category(code, model_ct):
        try:
            category = OrderCategory.objects.get(model=model_ct, code=code)
        except:
            category = OrderCategory.objects.create(model=model_ct, code=code, description="Unknown")

        return category

    @property
    def model_class(self):
        return self.model_ct.model_class()  # e.g. returns Order, Item, etc.

    @property
    def model_label(self):
        # "app_label.model" (lowercased model name)
        return f"{self.model_ct.app_label}.{self.model_ct.model}"