from apps.blocks.block_types.table.table_block import TableBlock
from apps.common.models import ProductionOrder, ProductionOrderOperation
from apps.blocks.services.filtering import apply_filter_registry

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

    def get_filter_schema(self, request):
        from django.db.models import Value
        # Dynamic choices example: callable receiving user (will be resolved in view)
        def status_choices(user):
            return [("open", "Open"), ("in_progress", "In Progress"), ("closed", "Closed")]

        return {
            # "status": {
            #     "label": "Status",
            #     "type": "multiselect",  # or "select"
            #     "choices": status_choices,  # or a static list
            #     "help": "Filter by one or more statuses.",
            #     "handler": lambda qs, val: qs.filter(status__in=val if isinstance(val, list) else [val]),
            # },
            # "due_date": {
            #     "label": "Due Date",
            #     "type": "date",
            #     "handler": lambda qs, val: qs.filter(due_date=val),
            # },
            "production_order": {
                "label": "Order #",
                "type": "text",
                "handler": lambda qs, val: qs.filter(production_order__icontains=val),
            },
            # "urgent": {
            #     "label": "Urgent only",
            #     "type": "boolean",
            #     "handler": lambda qs, val: qs.filter(is_urgent=True) if val else qs,
            # },
        }


class ProductionOrderOperationTableBlock(TableBlock):
    def __init__(self):
        super().__init__("production_order_operation_table")  # must match what's in admin

    def get_model(self):
        return ProductionOrderOperation

    def get_queryset(self, user, filters, column_config):
        selected_fields = column_config.fields if column_config else []

        # Extract related fields for select_related
        related_fields = set()
        for f in selected_fields:
            if "__" in f:
                related_fields.add(f.split("__")[0])

        qs = ProductionOrderOperation.objects.select_related(*related_fields)

        # Apply filters to the queryset (still as model instances)
        return apply_filter_registry("production_order_operation_table", qs, filters, user)


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

    def get_filter_schema(self, request):
        return {
            "production_order_operation": {
                "label": "Operation",
                "type": "text",
                "handler": lambda qs, val: qs.filter(operation__icontains=val),
            },

            "production_order": {
                "label": "Order",
                "type": "text",
                "handler": lambda qs, val: qs.filter(production_order__production_order__icontains=val),
            },
        }
