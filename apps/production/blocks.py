from apps.blocks.blocks.table.table_block import TableBlock
from apps.common.models import ProductionOrder
from apps.blocks.helpers.filter_config import apply_filter_registry

class ProductionOrderTableBlock(TableBlock):
    def __init__(self):
        super().__init__("production_order_table")  # must match what's in admin

    def get_model(self):
        return ProductionOrder

    def get_queryset(self, user, filters, column_config):
        selected_fields = column_config.fields if column_config else []

        # Extract related fields for select_related
        related_fields = set()
        for f in selected_fields:
            if "__" in f:
                related_fields.add(f.split("__")[0])

        qs = ProductionOrder.objects.select_related(*related_fields)

        # Apply filters to the queryset (still as model instances)
        return apply_filter_registry("production_order_table", qs, filters, user)


    def get_column_defs(self, user, column_config=None):
        from apps.blocks.helpers.column_config import get_user_column_config
        from django.contrib.admin.utils import label_for_field

        fields = column_config.fields if column_config else get_user_column_config(user, self.block)
        model = self.get_model()

        defs = []
        for field in fields:
            label = label_for_field(field, model, return_attr=False)
            defs.append({"field": field, "title": label})

        return defs

    def get_tabulator_options(self, user):
        return {
            "layout": "fitColumns",
            "pagination": "local",
            "paginationSize": 20,
        }

    def get_filter_schema(self, user):
        return {
            "status": {
                "label": "Status",
                "handler": lambda qs, val: qs.filter(status=val),
            },
            # add more filters here
        }