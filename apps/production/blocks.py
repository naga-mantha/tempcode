from apps.blocks.block_types.table.table_block import TableBlock
from apps.common.models import ProductionOrder, ProductionOrderOperation, Item
from apps.blocks.services.filtering import apply_filter_registry
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
import pandas as pd
from apps.common.models import SalesOrderLine, CustomerPurchaseOrder
from apps.common.models import SoValidateAggregate
from django.db.models.functions import TruncMonth
from django.db.models import Sum

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
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "production_order"]),
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
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "item"]),
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
        from apps.blocks.helpers.column_config import get_user_column_config
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


class SoValidateTableBlock(TableBlock):
    def __init__(self):
        super().__init__("so_validate_table")

    def get_model(self):
        # Use the aggregate fact model for column/filter config metadata
        return SoValidateAggregate

    def get_filter_schema(self, request):
        # Helpers to provide choices
        def month_choices(user, query=""):
            qs = (
                SoValidateAggregate.objects
                .values_list("period", flat=True)
                .distinct()
            )
            months = sorted({p for p in qs if p is not None})
            # value format YYYY-MM for clarity
            return [(p.strftime("%Y-%m-01"), p.strftime("%b %Y")) for p in months]

        def item_choices(user, query=""):
            qs = Item.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(description__icontains=query))
            return [(i.id, f"{i.code} - {i.description}".strip()) for i in qs.order_by("code")[:50]]

        return {
            "start_period": {
                "label": "Start Month",
                "type": "select",
                "choices": month_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "start_period"]),
            },
            "end_period": {
                "label": "End Month",
                "type": "select",
                "choices": month_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "end_period"]),
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
                    "maxItems": 5,
                },
            },
        }

    def _build_pivot(self, selected_filters, selected_fields):
        # Resolve period bounds
        import datetime as _dt
        start_raw = (selected_filters or {}).get("start_period")
        end_raw = (selected_filters or {}).get("end_period")
        def parse_date(s):
            try:
                return _dt.datetime.strptime(str(s), "%Y-%m-01").date()
            except Exception:
                return None
        start_p = parse_date(start_raw)
        end_p = parse_date(end_raw)

        qs = SoValidateAggregate.objects.select_related("item")
        if start_p:
            qs = qs.filter(period__gte=start_p)
        if end_p:
            qs = qs.filter(period__lte=end_p)
        items_filter = (selected_filters or {}).get("item")
        if items_filter:
            qs = qs.filter(item__in=items_filter)

        # If no bounds provided, default to last 12 months present
        if not start_p or not end_p:
            months = list(
                qs.values_list("period", flat=True).distinct().order_by("period")
            )
            if months:
                tail = months[-12:]
                min_p, max_p = tail[0], tail[-1]
                qs = qs.filter(period__gte=min_p, period__lte=max_p)

        # Build a dataframe from the aggregate table
        # Note: we can do this in pure Django ORM too, but pandas keeps consistency with earlier logic.
        df = pd.DataFrame(list(qs.values("item__code", "company", "period", "value")))
        if df.empty:
            return [
                {"title": "Item", "field": "Item"},
                {"title": "Company", "field": "Company"},
            ], []

        df = df.rename(columns={"item__code": "Item", "company": "Company"})
        df["period"] = pd.to_datetime(df["period"], errors="coerce")
        df = df.dropna(subset=["period"]).copy()
        df["MMYY"] = df["period"].dt.strftime("%m%y")
        # Determine chronological order
        periods_sorted = (
            df[["period", "MMYY"]].drop_duplicates().sort_values("period")
        )
        columns_order = periods_sorted["MMYY"].tolist()

        # Pivot using aggregated value
        pivot_sum = df.pivot_table(
            index=["Item", "Company"],
            columns="MMYY",
            values="value",
            aggfunc="sum",
            fill_value=0,
        )
        pivot_sum = pivot_sum.reindex(columns=columns_order)

        # Decide if we include identity columns based on selected column config fields
        show_item = True
        show_company = True
        if isinstance(selected_fields, (list, tuple)) and selected_fields:
            # If admin configured columns, only include those identities they picked
            show_item = any(f.startswith("item") for f in selected_fields)
            show_company = any(f == "company" for f in selected_fields)

        # Build rows per Item: Collins, MAI, Delta
        rows = []
        for item, df_item in pivot_sum.groupby(level=0):
            df_item_companies = df_item.droplevel(0)
            df_item_companies = df_item_companies.reindex(["Collins", "MAI"]).fillna(0)
            for company in ["Collins", "MAI"]:
                row = {}
                if show_item:
                    row["Item"] = item
                if show_company:
                    row["Company"] = company
                row.update({col: float(df_item_companies.loc[company].get(col, 0)) for col in columns_order})
                rows.append(row)
            delta_vals = (df_item_companies.loc["Collins"] - df_item_companies.loc["MAI"]).fillna(0)
            delta_row = {}
            if show_item:
                delta_row["Item"] = item
            if show_company:
                delta_row["Company"] = "Delta"
            delta_row.update({col: float(delta_vals.get(col, 0)) for col in columns_order})
            rows.append(delta_row)

        # Columns for Tabulator (dynamic months + optionally identity columns)
        columns = []
        if show_item:
            columns.append({"title": "Item", "field": "Item"})
        if show_company:
            columns.append({"title": "Company", "field": "Company"})
        columns.extend({"title": col, "field": col} for col in columns_order)

        return columns, rows

    def get_config(self, request, instance_id=None):
        # Reuse TableBlock's config selection and filter resolution so saved configs work
        (
            column_configs,
            filter_configs,
            active_column_config,
            active_filter_config,
            selected_fields,
        ) = self._select_configs(request, instance_id)
        filter_schema, selected_filter_values = self._resolve_filters(
            request, active_filter_config, instance_id
        )
        columns, _ = self._build_pivot(selected_filter_values, selected_fields)
        return {
            "block_name": self.block_name,
            "instance_id": instance_id or "main",
            "columns": columns,
            "tabulator_options": self.get_tabulator_options(request.user),
            "xlsx_download": self.get_xlsx_download_options(request, instance_id),
            "pdf_download": self.get_pdf_download_options(request, instance_id),
            "column_configs": column_configs,
            "filter_configs": filter_configs,
            "active_column_config_id": active_column_config.id if active_column_config else None,
            "active_filter_config_id": active_filter_config.id if active_filter_config else None,
            "filter_schema": filter_schema,
            "selected_filter_values": selected_filter_values,
        }

    def get_data(self, request, instance_id=None):
        import json
        (
            _column_configs,
            _filter_configs,
            _active_column_config,
            active_filter_config,
            selected_fields,
        ) = self._select_configs(request, instance_id)
        _schema, selected_filter_values = self._resolve_filters(
            request, active_filter_config, instance_id
        )
        _, rows = self._build_pivot(selected_filter_values, selected_fields)
        return {"data": json.dumps(rows)}
