from apps.django_bi.blocks.block_types.table.table_block import TableBlock
from apps.django_bi.blocks.block_types.pivot.pivot_block import PivotBlock
from apps.common.models import ProductionOrder, ProductionOrderOperation, Item, BusinessPartner
from apps.django_bi.blocks.services.filtering import apply_filter_registry
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.urls import reverse
import pandas as pd
import environ

env = environ.Env()


class ProductionOrderTableBlock(TableBlock):
    def __init__(self):
        super().__init__("production_order_table")  # must match what's in admin

    def get_model(self):
        return ProductionOrder

    def get_queryset(self, user, filters, column_config):
        selected_fields = column_config.fields if column_config else []

        # Extract valid forward-related fields for select_related
        related_fields = set()
        for f in selected_fields:
            if "__" in f:
                prefix = f.split("__", 1)[0]
                try:
                    field = ProductionOrder._meta.get_field(prefix)
                except FieldDoesNotExist:
                    continue
                if getattr(field, "is_relation", False) and not getattr(field, "many_to_many", False):
                    related_fields.add(prefix)

        qs = ProductionOrder.objects.select_related(*related_fields)

        # Apply remaining filters to the queryset (still as model instances)
        return apply_filter_registry("production_order_table", qs, filters, user)


    def get_column_defs(self, user, column_config=None):
        from apps.django_bi.blocks.services.column_config import get_user_column_config
        from django.contrib.admin.utils import label_for_field

        fields = column_config.fields if column_config else get_user_column_config(user, self.block)
        model = self.get_model()

        defs = []
        for field in fields:
            try:
                label = label_for_field(field, model, return_attr=False)
            except Exception:
                # Skip invalid/missing fields gracefully
                continue
            defs.append({"field": field, "title": label})

        return defs

    def get_tabulator_options_overrides(self, user):
        return {
            "paginationSize": 3,
            "paginationSizeSelector": [3, 6, 8, 10],
        }


    def get_xlsx_download_options_overrides(self, request, instance_id=None):
        return { }

    def get_pdf_download_options_overrides(self, request, instance_id=None):
        return {
            "filename": "Naga",
        }

    def get_filter_schema(self, request):
        def order_choices(user, query=""):
            qs = ProductionOrder.objects.all()
            if query:
                qs = qs.filter(production_order__icontains=query)
            return [(o.production_order, o.production_order) for o in qs.order_by("production_order")[:20]]

        def item_choices(user, query=""):
            qs = Item.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
            return [
                (i.code, f"{i.code} - {i.description}".strip())
                for i in qs.order_by("code")[:20]
            ]

        return {
            "production_order": {
                "label": "Order #",
                "type": "select",
                "choices": order_choices,
                "choices_url": reverse(
                    "blocks:block_filter_choices", args=[self.block_name, "production_order"]
                ),
                "handler": lambda qs, val: qs.filter(production_order=val) if val else qs,
                "tom_select_options": {
                    "placeholder": "Search production orders...",
                },
            },
            "item": {
                "label": "Item",
                "type": "multiselect",
                "multiple": True,
                "choices": item_choices,
                "choices_url": reverse(
                    "blocks:block_filter_choices", args=[self.block_name, "item"]
                ),
                "tom_select_options": {
                    "placeholder": "Search items...",
                    "plugins": ["remove_button"],
                    "maxItems": 3
                },
                "handler": lambda qs, val: qs.filter(item__code__in=val) if val else qs,
            },
        }


class ProductionOrderOperationTableBlock(TableBlock):
    def __init__(self):
        super().__init__("production_order_operation_table")  # must match what's in admin

    def get_model(self):
        return ProductionOrderOperation

    def get_queryset(self, user, filters, column_config):
        selected_fields = column_config.fields if column_config else []

        # Extract valid forward-related fields for select_related
        related_fields = set()
        for f in selected_fields:
            if "__" in f:
                prefix = f.split("__", 1)[0]
                try:
                    field = ProductionOrderOperation._meta.get_field(prefix)
                except FieldDoesNotExist:
                    continue
                if getattr(field, "is_relation", False) and not getattr(field, "many_to_many", False):
                    related_fields.add(prefix)

        qs = ProductionOrderOperation.objects.select_related(*related_fields)

        # Apply filters to the queryset (still as model instances)
        return apply_filter_registry("production_order_operation_table", qs, filters, user)


    def get_column_defs(self, user, column_config=None):
        from apps.django_bi.blocks.services.column_config import get_user_column_config
        from django.contrib.admin.utils import label_for_field

        fields = column_config.fields if column_config else get_user_column_config(user, self.block)
        model = self.get_model()

        defs = []
        for field in fields:
            label = label_for_field(field, model, return_attr=False)
            defs.append({"field": field, "title": label})

        return defs

    # Uses base tabulator defaults; no overrides needed.

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


class ProductionGenericPivot(PivotBlock):
    def __init__(self):
        super().__init__("production_generic_pivot")

    def get_model(self):
        return ProductionOrder

    # Single-source pivot; no Source selection required.

    def get_filter_schema(self, request):
        def item_choices(user, query=""):
            qs = Item.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
            # Use Item.code as the value so saved filters store and retrieve the code, not the PK
            return [(i.code, f"{i.code} - {i.description}".strip()) for i in qs.order_by("code")[:50]]

        return {
            "status": {
                "label": "Status",
                "type": "text",
                "handler": lambda qs, val: qs.filter(status__icontains=val) if val else qs,
            },
            "item": {
                "label": "Item",
                "type": "select",
                "choices": item_choices,
                "choices_url": reverse(
                    "blocks:block_filter_choices", args=[self.block_name, "item"]
                ),
                # Filter by item code (string), not by PK
                "handler": lambda qs, val: qs.filter(item__code=str(val)) if val else qs,
            },
            "due_start": {
                "label": "Due From",
                "type": "text",
                "handler": lambda qs, val: qs.filter(due_date__gte=val) if val else qs,
            },
            "due_end": {
                "label": "Due To",
                "type": "text",
                "handler": lambda qs, val: qs.filter(due_date__lte=val) if val else qs,
            },
        }
