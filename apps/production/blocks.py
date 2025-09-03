from apps.blocks.block_types.table.table_block import TableBlock
from apps.blocks.block_types.pivot.pivot_block import PivotBlock
from apps.common.models import ProductionOrder, ProductionOrderOperation, Item, BusinessPartner
from apps.blocks.services.filtering import apply_filter_registry
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.urls import reverse
import pandas as pd
from apps.common.models import SoValidateAggregate
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


class SoValidateTableBlock(PivotBlock):
    def __init__(self):
        super().__init__("so_validate_table")

    def get_model(self):
        # Use the aggregate fact model for column/filter config metadata
        return SoValidateAggregate

    def get_column_defs(self, user, column_config=None):
        # Use PivotBlock's curated Manage Views fields
        return super().get_column_defs(user, column_config)

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

        def parent_bp_choices(user, query=""):
            qs = BusinessPartner.objects.filter(parent__isnull=True)
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
            return [(bp.id, f"{bp.code or bp.name}") for bp in qs.order_by("code", "name")[:50]]

        return {
            "start_period": {
                "label": "Start Month",
                "type": "select",
                "choices": month_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "start_period"]),
                "handler": lambda qs, val: qs.filter(period__gte=pd.to_datetime(val).date()) if val else qs,
            },
            "end_period": {
                "label": "End Month",
                "type": "select",
                "choices": month_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "end_period"]),
                "handler": lambda qs, val: qs.filter(period__lte=pd.to_datetime(val).date()) if val else qs,
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
                },
                "handler": lambda qs, val: qs.filter(item__in=[int(v) for v in val]) if val else qs,
            },
            "parent_bp": {
                "label": "Parent Business Partner",
                "type": "select",
                "choices": parent_bp_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "parent_bp"]),
                "tom_select_options": {
                    "placeholder": "Select parent company...",
                },
                "maxItems": 1,
                "handler": lambda qs, val: qs.filter(customer_id=int(val)) if val else qs,
            },
        }

    def get_manageable_fields(self, user):
        return ["item__code", "item__description", "company__name", "company__code"]

    def get_base_queryset(self, user):
        return SoValidateAggregate.objects.select_related("item", "company", "customer")

    def build_pivot(self, queryset, selected_fields, selected_filters, user):
        # Resolve selected parent BP (for labeling) from filters
        parent_raw = (selected_filters or {}).get("parent_bp")
        try:
            parent_bp_id = int(parent_raw) if parent_raw not in (None, "") else None
        except Exception:
            parent_bp_id = None

        # Apply registered filter handlers to provided queryset
        qs = apply_filter_registry("so_validate_table", queryset, selected_filters or {}, user)

        # Determine requested nested fields for item and company, based on Manage Views selection
        selected_list = list(map(str, (selected_fields or [])))
        item_fields_requested = [f for f in selected_list if f.startswith("item__")]
        company_fields_requested = [f for f in selected_list if f.startswith("company__")]
        # Identity columns shown only if corresponding name field is selected
        show_item = "item__code" in selected_list
        show_company = "company__name" in selected_list
        extra_item_fields = [f for f in item_fields_requested if f != "item__code"]
        extra_company_fields = [f for f in company_fields_requested if f != "company__name"]

        # Build a dataframe from the aggregate table
        # Note: we can do this in pure Django ORM too, but pandas keeps consistency with earlier logic.
        values_fields = [
            "item__code",
            "company__name",
            "company__code",
            "customer_id",
            "period",
            "value",
        ] + extra_item_fields + extra_company_fields
        df = pd.DataFrame(list(qs.values(*values_fields)))
        if df.empty:
            cols = []
            if show_item:
                cols.append({"title": "Item", "field": "Item"})
            if show_company:
                cols.append({"title": "Company", "field": "Company"})
            return cols, []

        df = df.rename(columns={"item__code": "Item", "company__name": "CompanyName", "company__code": "CompanyCode"})
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
            index=["Item", "CompanyName"],
            columns="MMYY",
            values="value",
            aggfunc="sum",
            fill_value=0,
        )
        pivot_sum = pivot_sum.reindex(columns=columns_order)

        # maps for additional selected fields
        item_field_maps = {}
        for f in extra_item_fields:
            # value tied to Item (code) irrespective of company/month
            if f in df.columns:
                item_field_maps[f] = df[["Item", f]].dropna().drop_duplicates("Item").set_index("Item")[f].to_dict()
        company_field_maps = {}
        for f in extra_company_fields:
            if f in df.columns:
                company_field_maps[f] = df[["CompanyName", f]].dropna().drop_duplicates("CompanyName").set_index("CompanyName")[f].to_dict()

        # Build rows per Item: Customer, Company, Delta
        # Determine selected parent label and comparison company label for row ordering
        selected_parent_name = None
        if parent_bp_id:
            try:
                bp = BusinessPartner.objects.get(pk=parent_bp_id)
                selected_parent_name = bp.name or bp.code
            except BusinessPartner.DoesNotExist:
                selected_parent_name = None

        try:
            company_label = environ.Env()("COMPANY")
        except Exception:
            company_label = None

        rows = []
        for item, df_item in pivot_sum.groupby(level=0):
            df_item_companies = df_item.droplevel(0)
            # Determine the two companies to show for this item
            customer_label = selected_parent_name
            if not customer_label:
                # Fallback to first available company as "customer"
                customer_label = next(iter(df_item_companies.index.tolist()), None)
            companies_order = [customer_label, company_label]

            # Ensure both rows exist
            df_item_companies = df_item_companies.reindex(companies_order).fillna(0)

            # Customer and Company rows
            for company_name in companies_order:
                row = {}
                if show_item:
                    row["Item"] = item
                if show_company:
                    row["Company"] = company_name
                # Additional selected fields
                for f in extra_item_fields:
                    row[f] = item_field_maps.get(f, {}).get(item, "")
                for f in extra_company_fields:
                    row[f] = company_field_maps.get(f, {}).get(company_name, "")
                vals = df_item_companies.loc[company_name] if company_name in df_item_companies.index else None
                if vals is None or isinstance(vals, float):
                    # If the reindex produced a scalar due to missing index, handle gracefully
                    data_map = {col: float(vals) if vals is not None else 0.0 for col in columns_order}
                else:
                    data_map = {col: float(vals.get(col, 0)) for col in columns_order}
                row.update(data_map)
                rows.append(row)

            # Delta row (Customer - Company)
            try:
                delta_vals = (df_item_companies.loc[companies_order[0]] - df_item_companies.loc[companies_order[1]]).fillna(0)
            except Exception:
                # If any missing, treat as zeros
                zero = pd.Series({c: 0.0 for c in columns_order})
                delta_vals = zero
            delta_row = {}
            if show_item:
                delta_row["Item"] = item
            if show_company:
                delta_row["Company"] = "Delta"
            # Leave additional descriptive fields blank on delta row
            for f in extra_item_fields:
                delta_row[f] = ""
            for f in extra_company_fields:
                delta_row[f] = ""
            delta_row.update({col: float(delta_vals.get(col, 0)) for col in columns_order})
            rows.append(delta_row)

        # Columns for Tabulator (dynamic months + optionally identity columns)
        from django.contrib.admin.utils import label_for_field
        model = self.get_model()
        columns = []
        # Respect Manage Views order for identity and extra fields
        for f in selected_list:
            if f == "item__code" and show_item:
                columns.append({"title": "Item", "field": "Item"})
            elif f == "company__name" and show_company:
                columns.append({"title": "Company", "field": "Company"})
            elif f in extra_item_fields or f in extra_company_fields:
                try:
                    title = label_for_field(f, model, return_attr=False)
                except Exception:
                    title = f.replace("__", " ").title()
                columns.append({"title": title, "field": f})
        # Then the dynamic month columns
        columns.extend({"title": col, "field": col} for col in columns_order)

        return columns, rows
