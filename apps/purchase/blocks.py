from apps.blocks.block_types.table.table_block import TableBlock
from apps.blocks.base import BaseBlock
from apps.blocks.block_types.repeater.repeater_block import RepeaterBlock
from apps.blocks.block_types.pivot.pivot_block import PivotBlock
from apps.blocks.block_types.pivot.generic_pivot_block import GenericPivotBlock
from apps.common.models import PurchaseOrderLine, Item
from apps.blocks.services.filtering import apply_filter_registry
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.urls import reverse
import pandas as pd
import environ
from django.utils import timezone
from django.db.models import Count
from django.template.loader import render_to_string
from apps.accounts.models import CustomUser

env = environ.Env()

# class ProductionOrderTableBlock(TableBlock):
#     def __init__(self):
#         super().__init__("production_order_table")  # must match what's in admin
#
#     def get_model(self):
#         return ProductionOrder
#
#     def get_queryset(self, user, filters, column_config):
#         selected_fields = column_config.fields if column_config else []
#
#         # Extract valid forward-related fields for select_related
#         related_fields = set()
#         for f in selected_fields:
#             if "__" in f:
#                 prefix = f.split("__", 1)[0]
#                 try:
#                     field = ProductionOrder._meta.get_field(prefix)
#                 except FieldDoesNotExist:
#                     continue
#                 if getattr(field, "is_relation", False) and not getattr(field, "many_to_many", False):
#                     related_fields.add(prefix)
#
#         qs = ProductionOrder.objects.select_related(*related_fields)
#
#         # Apply remaining filters to the queryset (still as model instances)
#         return apply_filter_registry("production_order_table", qs, filters, user)
#
#
#     def get_column_defs(self, user, column_config=None):
#         from apps.blocks.helpers.column_config import get_user_column_config
#         from django.contrib.admin.utils import label_for_field
#
#         fields = column_config.fields if column_config else get_user_column_config(user, self.block)
#         model = self.get_model()
#
#         defs = []
#         for field in fields:
#             try:
#                 label = label_for_field(field, model, return_attr=False)
#             except Exception:
#                 # Skip invalid/missing fields gracefully
#                 continue
#             defs.append({"field": field, "title": label})
#
#         return defs
#
#     def get_tabulator_options_overrides(self, user):
#         return {
#             "paginationSize": 3,
#             "paginationSizeSelector": [3, 6, 8, 10],
#         }
#
#
#     def get_xlsx_download_options_overrides(self, request, instance_id=None):
#         return { }
#
#     def get_pdf_download_options_overrides(self, request, instance_id=None):
#         return {
#             "filename": "Naga",
#         }
#
#     def get_filter_schema(self, request):
#         def order_choices(user, query=""):
#             qs = ProductionOrder.objects.all()
#             if query:
#                 qs = qs.filter(production_order__icontains=query)
#             return [(o.production_order, o.production_order) for o in qs.order_by("production_order")[:20]]
#
#         def item_choices(user, query=""):
#             qs = Item.objects.all()
#             if query:
#                 qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
#             return [
#                 (i.code, f"{i.code} - {i.description}".strip())
#                 for i in qs.order_by("code")[:20]
#             ]
#
#         return {
#             "production_order": {
#                 "label": "Order #",
#                 "type": "select",
#                 "choices": order_choices,
#                 "choices_url": reverse("block_filter_choices", args=[self.block_name, "production_order"]),
#                 "handler": lambda qs, val: qs.filter(production_order=val) if val else qs,
#                 "tom_select_options": {
#                     "placeholder": "Search production orders...",
#                 },
#             },
#             "item": {
#                 "label": "Item",
#                 "type": "multiselect",
#                 "multiple": True,
#                 "choices": item_choices,
#                 "choices_url": reverse("block_filter_choices", args=[self.block_name, "item"]),
#                 "tom_select_options": {
#                     "placeholder": "Search items...",
#                     "plugins": ["remove_button"],
#                     "maxItems": 3
#                 },
#                 "handler": lambda qs, val: qs.filter(item__code__in=val) if val else qs,
#             },
#         }
#
#
# class ProductionOrderOperationTableBlock(TableBlock):
#     def __init__(self):
#         super().__init__("production_order_operation_table")  # must match what's in admin
#
#     def get_model(self):
#         return ProductionOrderOperation
#
#     def get_queryset(self, user, filters, column_config):
#         selected_fields = column_config.fields if column_config else []
#
#         # Extract valid forward-related fields for select_related
#         related_fields = set()
#         for f in selected_fields:
#             if "__" in f:
#                 prefix = f.split("__", 1)[0]
#                 try:
#                     field = ProductionOrderOperation._meta.get_field(prefix)
#                 except FieldDoesNotExist:
#                     continue
#                 if getattr(field, "is_relation", False) and not getattr(field, "many_to_many", False):
#                     related_fields.add(prefix)
#
#         qs = ProductionOrderOperation.objects.select_related(*related_fields)
#
#         # Apply filters to the queryset (still as model instances)
#         return apply_filter_registry("production_order_operation_table", qs, filters, user)
#
#
#     def get_column_defs(self, user, column_config=None):
#         from apps.blocks.helpers.column_config import get_user_column_config
#         from django.contrib.admin.utils import label_for_field
#
#         fields = column_config.fields if column_config else get_user_column_config(user, self.block)
#         model = self.get_model()
#
#         defs = []
#         for field in fields:
#             label = label_for_field(field, model, return_attr=False)
#             defs.append({"field": field, "title": label})
#
#         return defs
#
#     # Uses base tabulator defaults; no overrides needed.
#
#     def get_filter_schema(self, request):
#         return {
#             "production_order_operation": {
#                 "label": "Operation",
#                 "type": "text",
#                 "handler": lambda qs, val: qs.filter(operation__icontains=val),
#             },
#
#             "production_order": {
#                 "label": "Order",
#                 "type": "text",
#                 "handler": lambda qs, val: qs.filter(production_order__production_order__icontains=val),
#             },
#         }


class PurchaseGenericPivot(GenericPivotBlock):
    def __init__(self):
        super().__init__("purchase_generic_pivot")

    def get_model(self):
        return PurchaseOrderLine

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
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "item"]),
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


class PurchaseOverdueByBuyerPivot(PivotBlock):
    """Simple pivot: count of lines with final_receive_date in the past, grouped by buyer."""

    def __init__(self):
        super().__init__("purchase_overdue_by_buyer")

    def get_model(self):
        return PurchaseOrderLine

    # Provide enumeration queryset for the Repeater to derive panels
    def get_enumeration_queryset(self, user):
        return PurchaseOrderLine.objects.filter(final_receive_date__lt=timezone.now().date())

    def get_filter_schema(self, request):
        # Optional buyer filter to allow narrowing to a given buyer (or unassigned)
        def buyer_choices(user, query=""):
            qs = CustomUser.objects.all()
            if query:
                qs = qs.filter(username__icontains=query)
            out = [(u.id, u.username) for u in qs.order_by("username")[:50]]
            # Add an explicit Unassigned option
            out.insert(0, ("__none__", "(Unassigned)"))
            return out

        return {
            "buyer": {
                "label": "Buyer",
                "type": "select",
                "choices": buyer_choices,
                # Handles both numeric ID and the special '__none__' sentinel
                "handler": lambda qs, val: (
                    qs.filter(order__buyer__isnull=True)
                    if str(val) == "__none__"
                    else qs.filter(order__buyer_id=int(val)) if val else qs
                ),
            },
        }

    def build_columns_and_rows(self, user, filter_values):
        today = timezone.now().date()
        # Base queryset filtered to overdue lines
        qs = PurchaseOrderLine.objects.filter(final_receive_date__lt=today)
        # Apply optional buyer filter if provided via filter schema
        qs = apply_filter_registry(self.block_name, qs, filter_values or {}, user)
        qs = qs.values("order__buyer__username").annotate(overdue_count=Count("id")).order_by("order__buyer__username")
        rows = []
        for r in qs:
            buyer = r.get("order__buyer__username") or "(Unassigned)"
            rows.append({"Buyer": buyer, "Overdue Lines": r.get("overdue_count", 0)})
        columns = [
            {"title": "Buyer", "field": "Buyer"},
            {"title": "Overdue Lines", "field": "Overdue Lines"},
        ]
        return columns, rows


class PurchaseBuyerOverdueRepeaterBlock(RepeaterBlock):
    """Repeater that renders the overdue-by-buyer child pivot per buyer."""

    template_name = "purchase/buyer_pivot_repeater.html"

    def __init__(self):
        super().__init__("purchase_buyer_overdue_repeater")

    def get_fixed_child_block_code(self) -> str | None:
        return "purchase_overdue_by_buyer"

    def _build_panels(self, request, user, active_config):
        # Provide a sensible default schema if user has no saved settings
        if not active_config or not getattr(active_config, "schema", None):
            default_schema = {
                "group_by": "order__buyer",
                "label_field": "order__buyer__username",
                "include_null": True,
                "null_sentinel": "__none__",
                "cols": 6,
                "child_filters_map": {"buyer": "value"},
                "sort": "asc",
                "title_template": "{label}",
            }
            class _Temp:
                pass
            t = _Temp()
            t.schema = default_schema
            return super()._build_panels(request, user, t)
        return super()._build_panels(request, user, active_config)
