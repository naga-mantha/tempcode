from apps.blocks.block_types.table.table_block import TableBlock
from apps.blocks.block_types.pivot.pivot_block import PivotBlock
from apps.blocks.block_types.pivot.generic_pivot_block import GenericPivotBlock
from apps.common.models import ProductionOrder, PlannedOrder, Item, BusinessPartner, MrpMessage
from apps.blocks.services.filtering import apply_filter_registry
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.urls import reverse
import pandas as pd
import environ

env = environ.Env()



class PlannedPurchaseOrderTableBlock(TableBlock):
    def __init__(self):
        super().__init__("planned_purchase_order_table")  # must match what's in admin

    def get_model(self):
        return PlannedOrder

    def get_queryset(self, user, filters, column_config):
        selected_fields = column_config.fields if column_config else []

        # Extract valid forward-related fields for select_related
        related_fields = set()
        for f in selected_fields:
            if "__" in f:
                prefix = f.split("__", 1)[0]
                try:
                    field = PlannedOrder._meta.get_field(prefix)
                except FieldDoesNotExist:
                    continue
                if getattr(field, "is_relation", False) and not getattr(field, "many_to_many", False):
                    related_fields.add(prefix)

        qs = PlannedOrder.objects.filter(type="PPUR").select_related(*related_fields)

        # Apply remaining filters to the queryset (still as model instances)
        return apply_filter_registry("production_order_table", qs, filters, user)

    def get_column_defs(self, user, column_config=None):
        from apps.blocks.helpers.column_config import get_user_column_config
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

    def get_filter_schema(self, request):
        def item_choices(user, query=""):
            qs = Item.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
            return [
                (i.code, f"{i.code} - {i.description}".strip())
                for i in qs.order_by("code")[:20]
            ]

        return {
            "item": {
                "label": "Item",
                "type": "multiselect",
                "multiple": True,
                "choices": item_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "item"]),
                "tom_select_options": {
                    "placeholder": "Search items...",
                    "plugins": ["remove_button"],
                    "maxItems": 3
                },
                "handler": lambda qs, val: qs.filter(item__code__in=val) if val else qs,
            },
        }


class PlannedProductionOrderTableBlock(TableBlock):
    def __init__(self):
        super().__init__("planned_production_order_table")  # must match what's in admin

    def get_model(self):
        return PlannedOrder

    def get_queryset(self, user, filters, column_config):
        selected_fields = column_config.fields if column_config else []

        # Extract valid forward-related fields for select_related
        related_fields = set()
        for f in selected_fields:
            if "__" in f:
                prefix = f.split("__", 1)[0]
                try:
                    field = PlannedOrder._meta.get_field(prefix)
                except FieldDoesNotExist:
                    continue
                if getattr(field, "is_relation", False) and not getattr(field, "many_to_many", False):
                    related_fields.add(prefix)

        qs = PlannedOrder.objects.filter(type="PPRO").select_related(*related_fields)

        # Apply remaining filters to the queryset (still as model instances)
        return apply_filter_registry("production_order_table", qs, filters, user)

    def get_column_defs(self, user, column_config=None):
        from apps.blocks.helpers.column_config import get_user_column_config
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

    def get_filter_schema(self, request):
        def item_choices(user, query=""):
            qs = Item.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
            return [
                (i.code, f"{i.code} - {i.description}".strip())
                for i in qs.order_by("code")[:20]
            ]

        return {
            "item": {
                "label": "Item",
                "type": "multiselect",
                "multiple": True,
                "choices": item_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "item"]),
                "tom_select_options": {
                    "placeholder": "Search items...",
                    "plugins": ["remove_button"],
                    "maxItems": 3
                },
                "handler": lambda qs, val: qs.filter(item__code__in=val) if val else qs,
            },
        }


class PlannedOrderPivot(GenericPivotBlock):
    def __init__(self):
        super().__init__("planned_order_pivot")

    def get_model(self):
        return PlannedOrder

    def get_filter_schema(self, request):
        # Allow filtering by PlannedOrder.type (e.g., PPUR/PPRO) and optionally Item
        def type_choices(user):
            # Keep simple/static for now; can be made dynamic if needed
            return [("PPUR", "Purchase"), ("PPRO", "Production")]

        def item_choices(user, query=""):
            qs = Item.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
            return [
                (i.code, f"{i.code} - {i.description}".strip())
                for i in qs.order_by("code")[:20]
            ]

        return {
            "type": {
                "label": "Type",
                "type": "select",
                "choices": type_choices,
                "handler": lambda qs, val: qs.filter(type=val) if val else qs,
            },
            "item": {
                "label": "Item",
                "type": "multiselect",
                "multiple": True,
                "choices": item_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "item"]),
                "tom_select_options": {
                    "placeholder": "Search items...",
                    "plugins": ["remove_button"],
                    "maxItems": 3
                },
                "handler": lambda qs, val: qs.filter(item__code__in=val) if val else qs,
            },
            "planned_start_date_from": {
                "label": "Planned Start From",
                "type": "date",
                "handler": lambda qs, val: qs.filter(planned_start_date__gte=val) if val else qs,
            },
            "planned_start_date_to": {
                "label": "Planned Start To",
                "type": "date",
                "handler": lambda qs, val: qs.filter(planned_start_date__lte=val) if val else qs,
            },
            # "planned_end_date_from": {
            #     "label": "Planned End From",
            #     "type": "date",
            #     "handler": lambda qs, val: qs.filter(planned_end_date__gte=val) if val else qs,
            # },
            # "planned_end_date_to": {
            #     "label": "Planned End To",
            #     "type": "date",
            #     "handler": lambda qs, val: qs.filter(planned_end_date__lte=val) if val else qs,
            # },
        }



class MRPMessageTableBlock(TableBlock):
    def __init__(self):
        super().__init__("mrp_message_table")  # must match what's in admin

    def get_model(self):
        return MrpMessage

    def get_queryset(self, user, filters, column_config):
        selected_fields = column_config.fields if column_config else []

        # Extract valid forward-related fields for select_related
        related_fields = set()
        for f in selected_fields:
            if "__" in f:
                prefix = f.split("__", 1)[0]
                try:
                    field = PlannedOrder._meta.get_field(prefix)
                except FieldDoesNotExist:
                    continue
                if getattr(field, "is_relation", False) and not getattr(field, "many_to_many", False):
                    related_fields.add(prefix)

        qs = MrpMessage.objects.select_related(*related_fields)

        # Apply remaining filters to the queryset (still as model instances)
        return apply_filter_registry("mrp_message_table", qs, filters, user)

    def get_column_defs(self, user, column_config=None):
        from apps.blocks.helpers.column_config import get_user_column_config
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

    def get_filter_schema(self, request):
        def item_choices(user, query=""):
            qs = Item.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
            return [
                (i.code, f"{i.code} - {i.description}".strip())
                for i in qs.order_by("code")[:20]
            ]

        return {
            "item": {
                "label": "Item",
                "type": "multiselect",
                "multiple": True,
                "choices": item_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "item"]),
                "tom_select_options": {
                    "placeholder": "Search items...",
                    "plugins": ["remove_button"],
                    "maxItems": 3
                },
                "handler": lambda qs, val: qs.filter(item__code__in=val) if val else qs,
            },
        }