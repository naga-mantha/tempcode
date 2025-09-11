from apps.blocks.block_types.table.table_block import TableBlock
from apps.blocks.base import BaseBlock
from apps.blocks.block_types.repeater.repeater_block import RepeaterBlock
from apps.blocks.block_types.pivot.pivot_block import PivotBlock
from apps.blocks.block_types.pivot.generic_pivot_block import GenericPivotBlock
from apps.common.models import PurchaseOrderLine, Item, BusinessPartner
from apps.common.models.receipts import ReceiptLine
from apps.blocks.services.filtering import apply_filter_registry
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.urls import reverse
import pandas as pd
import environ
from django.utils import timezone
from django.db.models import Count, Sum, Case, When, IntegerField
from django.db.models.functions import TruncMonth
from django.template.loader import render_to_string
from apps.accounts.models import CustomUser
from apps.common.models.receipts import PurchaseTimelinessClassification

env = environ.Env()

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


class ReceiptLinesTableBlock(TableBlock):
    def __init__(self):
        super().__init__("receipt_lines_table")

    def get_model(self):
        return ReceiptLine

    def get_queryset(self, user, filters, column_config):
        # Always bring common relations
        qs = ReceiptLine.objects.select_related("po_line", "po_line__order")
        # Apply remaining filters to the queryset (still as model instances)
        return apply_filter_registry(self.block_name, qs, filters or {}, user)

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
                # Fallback to prettified field name for properties
                label = field.replace("_", " ").title()
            defs.append({"field": field, "title": label})
        return defs

    def get_filter_schema(self, request):
        def supplier_choices(user, query=""):
            qs = BusinessPartner.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
            return [(bp.id, f"{bp.code} - {bp.name}".strip(" -")) for bp in qs.order_by("code")[:50]]

        return {
            "supplier": {
                "label": "Supplier",
                "type": "select",
                "choices": supplier_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "supplier"]),
                "handler": lambda qs, val: qs.filter(po_line__order__supplier_id=int(val)) if val else qs,
            },
            "receipt_date_from": {
                "label": "Receipt From",
                "type": "date",
                "handler": lambda qs, val: qs.filter(receipt_date__gte=val) if val else qs,
            },
            "receipt_date_to": {
                "label": "Receipt To",
                "type": "date",
                "handler": lambda qs, val: qs.filter(receipt_date__lte=val) if val else qs,
            },
        }


class SupplierByMonthSummaryTableBlock(TableBlock):
    """Aggregated summary of receipts by supplier and month.

    Uses a lightweight row class to satisfy TableBlock's column labeling.
    """

    class Row:
        # Dummy attributes for label_for_field compatibility
        supplier = None
        month = None
        amount_received = None
        quantity_received = None
        otd_percent = None
        late_percent = None
        very_late_percent = None

    def __init__(self):
        super().__init__("supplier_by_month_summary_table")

    def get_model(self):
        return SupplierByMonthSummaryTableBlock.Row

    def _build_queryset(self, user, filter_values, active_column_config):
        # Bypass model permission filters since these are aggregated, non-model rows
        rows = self.get_queryset(user, filter_values, active_column_config)
        sample = rows[0] if rows else None
        return rows, sample

    def _compute_fields(self, user, selected_fields, active_column_config, sample_obj):
        # Build fields/columns directly from dynamic column defs, bypassing model meta
        column_defs = self.get_column_defs(user, None)
        fields_order = [c.get("field") for c in column_defs]
        fields = []
        for c in column_defs:
            fields.append({
                "name": c.get("field"),
                "label": c.get("title", c.get("field")),
                "mandatory": False,
                "editable": False,
            })
        columns = column_defs
        return fields, columns

    def get_queryset(self, user, filters, column_config):
        base = ReceiptLine.objects.select_related("po_line", "po_line__order")
        base = apply_filter_registry(self.block_name, base, filters or {}, user)

        # Active classifications drive the dynamic columns
        classes = list(PurchaseTimelinessClassification.objects.filter(active=True).order_by("priority", "id"))

        # Prepare dynamic annotations for per-class counts
        annotations = {
            "amount_received": Sum("amount_home_currency"),
            "quantity_received": Sum("received_quantity"),
            "total": Count("id"),
        }
        name_to_field = {}
        for c in classes:
            # Safe field key for this class
            key = self._class_field_key(c.name)
            name_to_field[c.name] = key
            annotations[key] = Count("id", filter=Q(classification_id=c.id))

        qs = (
            base.annotate(month=TruncMonth("receipt_date"))
            .values("po_line__order__supplier__id", "po_line__order__supplier__name", "month")
            .annotate(**annotations)
            .order_by("po_line__order__supplier__name", "month")
        )

        rows = []
        for r in qs:
            total = r.get("total") or 0
            row = {
                "supplier": r.get("po_line__order__supplier__name") or "",
                "month": r.get("month"),
                "amount_received": r.get("amount_received") or 0,
                "quantity_received": r.get("quantity_received") or 0,
            }
            otd_count = 0
            for c in classes:
                key = name_to_field[c.name]
                count = r.get(key) or 0
                pct_field = f"pct_{key}"
                row[pct_field] = round((count / total) * 100, 2) if total else 0.0
                if getattr(c, "counts_for_ontime", False):
                    otd_count += count

            row["otd_percent"] = round((otd_count / total) * 100, 2) if total else 0.0
            rows.append(_DictObj(row))
        return rows

    def get_column_defs(self, user, column_config=None):
        # Dynamic columns driven by active classification rules
        classes = list(PurchaseTimelinessClassification.objects.filter(active=True).order_by("priority", "id"))
        cols = [
            {"field": "supplier", "title": "Supplier"},
            {"field": "month", "title": "Month"},
            {"field": "amount_received", "title": "Amount Received"},
            {"field": "quantity_received", "title": "Quantity Received"},
        ]
        for c in classes:
            key = self._class_field_key(c.name)
            cols.append({"field": f"pct_{key}", "title": f"{c.name} %"})
        cols.append({"field": "otd_percent", "title": "OTD %"})
        return cols

    @staticmethod
    def _class_field_key(name: str) -> str:
        # Normalize class names into safe snake-case keys
        import re
        key = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
        if not key:
            key = "class"
        return key

    def _serialize_rows(self, queryset, selected_fields):
        # Fallback to dynamic columns when no column config is set
        if not selected_fields:
            selected_fields = [c["field"] for c in self.get_column_defs(getattr(self, "_current_user", None), None)]
        return super()._serialize_rows(queryset, selected_fields)

    def get_filter_schema(self, request):
        # Reuse filters similar to receipt lines
        def supplier_choices(user, query=""):
            qs = BusinessPartner.objects.all()
            if query:
                qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
            return [(bp.id, f"{bp.code} - {bp.name}".strip(" -")) for bp in qs.order_by("code")[:50]]

        return {
            "supplier": {
                "label": "Supplier",
                "type": "select",
                "choices": supplier_choices,
                "choices_url": reverse("block_filter_choices", args=[self.block_name, "supplier"]),
                "handler": lambda qs, val: qs.filter(po_line__order__supplier_id=int(val)) if val else qs,
            },
            "receipt_date_from": {
                "label": "Receipt From",
                "type": "date",
                "handler": lambda qs, val: qs.filter(receipt_date__gte=val) if val else qs,
            },
            "receipt_date_to": {
                "label": "Receipt To",
                "type": "date",
                "handler": lambda qs, val: qs.filter(receipt_date__lte=val) if val else qs,
            },
        }


class PurchaseOtdRepeaterBlock(RepeaterBlock):
    """Repeater that renders PurchaseOtdDialChart per Supplier (code - name).

    - Groups by supplier (no nulls)
    - Shows 3 panels per row (cols=4)
    - Limits to 5 suppliers, sorted ascending by supplier code
    - Injects child filters: supplier id, last month's date range
    """

    def __init__(self):
        super().__init__("purchase_otd_repeater")

    def get_fixed_child_block_code(self) -> str | None:
        return "purchase_otd_dial"

    def _build_panels(self, request, user, active_config):
        # Build defaults if user has no saved repeater config
        if not active_config or not getattr(active_config, "schema", None):
            default_schema = {
                "group_by": "po_line__order__supplier",  # supplier id
                # label will be built as "code - name" below (custom enumeration)
                "include_null": False,
                "cols": 4,
                "child_filters_map": {"supplier": "value"},
                # Sort/limit by metric (OTD%) via child metrics hook
                "order_by": "metric",
                "order": "desc",  # Top N (highest OTD%)
                "limit": 5,
                "metric_mode": "child",
                "title_template": "{label}",
            }
            class _Temp:
                pass
            t = _Temp()
            t.schema = default_schema
            return self._build_supplier_panels(request, user, t)
        return self._build_supplier_panels(request, user, active_config)

    def _build_supplier_panels(self, request, user, active_config):
        from apps.blocks.registry import block_registry
        from apps.blocks.models.block import Block
        from apps.blocks.models.block_filter_config import BlockFilterConfig
        from apps.blocks.models.block_column_config import BlockColumnConfig
        from django.http import QueryDict
        from django.utils.text import slugify
        import uuid
        from django.utils import timezone
        from datetime import timedelta

        schema = active_config.schema or {}
        block_code = self.get_fixed_child_block_code() or schema.get("block_code")
        group_by = schema.get("group_by") or "po_line__order__supplier"
        include_null = bool(schema.get("include_null"))
        cols = int(schema.get("cols") or 4)
        child_filters_map = schema.get("child_filters_map") or {}
        order_by = (schema.get("order_by") or "label").lower()
        order = (schema.get("order") or schema.get("sort") or "asc").lower()
        limit = schema.get("limit")
        title_template = (schema.get("title_template") or "{label}").strip()

        if not block_code:
            return [], cols, ""
        child = block_registry.get(block_code)
        if not child:
            return ([{"title": "Error", "html": f"<div class='alert alert-danger p-2 m-0'>Child block '{block_code}' not available.</div>"}], cols, "")

        # Enumeration queryset from child (ReceiptLine objects)
        try:
            if hasattr(child, "get_enumeration_queryset"):
                base_qs = child.get_enumeration_queryset(user)  # type: ignore[attr-defined]
            elif hasattr(child, "get_model"):
                model = child.get_model()
                base_qs = model.objects.all()
            else:
                base_qs = None
        except Exception:
            base_qs = None

        # Build distinct suppliers with code and name, then compose label "code - name"
        values = []
        if base_qs is not None:
            fields = [group_by, "po_line__order__supplier__code", "po_line__order__supplier__name"]
            qs = base_qs.values(*fields).distinct()
            if not include_null:
                qs = qs.exclude(**{f"{group_by}__isnull": True})
            for r in qs:
                supplier_id = r.get(group_by)
                code = r.get("po_line__order__supplier__code") or ""
                name = r.get("po_line__order__supplier__name") or ""
                label = f"{code} - {name}".strip(" -")
                values.append({
                    "value": supplier_id,
                    "label": label,
                })

        # Compute last month's date range (used for both injection and child metric evaluation)
        today = timezone.now().date()
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        # When configured to order by metric, use child hook to compute OTD% and sort values
        if values and order_by == "metric" and hasattr(child, "get_repeater_metrics"):
            metric_filters = {
                "receipt_date_from": last_month_start.isoformat(),
                "receipt_date_to": last_month_end.isoformat(),
            }
            try:
                metrics = child.get_repeater_metrics(user, group_by, base_qs, metric_filters)  # type: ignore[attr-defined]
            except Exception:
                metrics = {}
            for it in values:
                it["metric"] = metrics.get(it["value"], 0)
            if order in ("asc", "desc"):
                rev = order == "desc"
                values.sort(key=lambda x: (x.get("metric") is None, x.get("metric", 0)), reverse=rev)
            if isinstance(limit, int) and limit > 0:
                values = values[:limit]
        else:
            # Fallback to label/code ordering
            if order in ("asc", "desc"):
                values.sort(key=lambda x: x.get("label") or "", reverse=(order == "desc"))
            if isinstance(limit, int) and limit > 0:
                values = values[:limit]

        panels = []

        class _ReqProxy:
            def __init__(self, req, get):
                self._req = req
                self.GET = get
            def __getattr__(self, item):
                return getattr(self._req, item)

        # Resolve child block object and default saved configs named "Previous Month"
        child_block_obj = getattr(child, "block", None)
        child_block = None
        try:
            child_block = child_block_obj if child_block_obj else Block.objects.get(code=getattr(child, "block_name", block_code))
        except Exception:
            child_block = None
        child_filter_cfg_id = None
        child_column_cfg_id = None

        if child_block:
            cfg = BlockFilterConfig.objects.filter(block=child_block, user=user, name="Previous Month").only("id").first()
            if not cfg:
                try:
                    cfg = BlockFilterConfig.objects.create(
                        block=child_block,
                        user=user,
                        name="Previous Month",
                        values={
                            "receipt_date_from": last_month_start.isoformat(),
                            "receipt_date_to": last_month_end.isoformat(),
                        },
                        is_default=False,
                    )
                except Exception:
                    cfg = None
            if cfg:
                child_filter_cfg_id = str(cfg.id)
            col = BlockColumnConfig.objects.filter(block=child_block, user=user, name="Previous Month").only("id").first()
            if col:
                child_column_cfg_id = str(col.id)

        for item in values:
            raw_value = item.get("value")
            label = item.get("label")
            inst_slug = slugify(str(label if label is not None else raw_value)) or uuid.uuid4().hex[:6]
            instance = f"rep_{inst_slug}"
            qd: QueryDict = request.GET.copy()

            # Map configured filters into child
            for key, source in (child_filters_map.items() if isinstance(child_filters_map, dict) else []):
                sval = None
                if source == "value":
                    sval = raw_value
                elif source == "label":
                    sval = label
                else:
                    # treat as literal
                    sval = source
                qd[f"{getattr(child, 'block_name', block_code)}__{instance}__filters.{key}"] = "" if sval is None else str(sval)

            # Inject last month's date range (only if not already provided)
            base_ns = f"{getattr(child, 'block_name', block_code)}__{instance}__filters."
            if f"{base_ns}receipt_date_from" not in qd:
                qd[f"{base_ns}receipt_date_from"] = last_month_start.isoformat()
            if f"{base_ns}receipt_date_to" not in qd:
                qd[f"{base_ns}receipt_date_to"] = last_month_end.isoformat()

            # Inject saved configs named "Default" if present
            if child_filter_cfg_id:
                key = f"{getattr(child, 'block_name', block_code)}__{instance}__filter_config_id"
                if key not in qd:
                    qd[key] = child_filter_cfg_id
            if child_column_cfg_id:
                key = f"{getattr(child, 'block_name', block_code)}__{instance}__column_config_id"
                if key not in qd:
                    qd[key] = child_column_cfg_id

            qd["embedded"] = "1"
            proxy = _ReqProxy(request, qd)
            try:
                # Evaluate child metrics for this month using the hook to ensure ordering reflects OTD%
                # Build metric_filters for last month
                metric_filters = {
                    "receipt_date_from": last_month_start.isoformat(),
                    "receipt_date_to": last_month_end.isoformat(),
                }
                # Best-effort precomputation (child rendering does not need it, but ensures metrics route works)
                if hasattr(child, "get_repeater_metrics"):
                    try:
                        _ = child.get_repeater_metrics(user, group_by, child.get_enumeration_queryset(user), metric_filters)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                resp = child.render(proxy, instance_id=instance)
                html = resp.content.decode(getattr(resp, "charset", "utf-8") or "utf-8")
            except Exception as exc:
                html = (
                    "<div class='alert alert-danger p-2 m-0'>"
                    f"Error rendering child '{block_code}': {str(exc)}"
                    "</div>"
                )
            title = title_template.format(label=label, value=raw_value)
            panels.append({"title": title, "html": html})

        return panels, cols, schema.get("title", "")


class _DictObj:
    """Tiny adapter to allow attribute access for dicts for TableBlock serializer."""

    def __init__(self, data):
        self.__dict__.update(data)



class PurchaseOrderLineTableBlock(TableBlock):
    def __init__(self):
        super().__init__("purchase_order_lines_table")  # must match what's in admin

    def get_model(self):
        return PurchaseOrderLine

    def get_queryset(self, user, filters, column_config):
        selected_fields = column_config.fields if column_config else []

        # Extract valid forward-related fields for select_related
        related_fields = set()
        for f in selected_fields:
            if "__" in f:
                prefix = f.split("__", 1)[0]
                try:
                    field = PurchaseOrderLine._meta.get_field(prefix)
                except FieldDoesNotExist:
                    continue
                if getattr(field, "is_relation", False) and not getattr(field, "many_to_many", False):
                    related_fields.add(prefix)

        qs = PurchaseOrderLine.objects.filter(status="open").select_related(*related_fields)

        # Apply remaining filters to the queryset (still as model instances)
        return apply_filter_registry("purchase_order_lines_table", qs, filters, user)

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



class PurchaseOrderLinePivot(GenericPivotBlock):
    def __init__(self):
        super().__init__("purchase_order_line_pivot")

    def get_model(self):
        return PurchaseOrderLine
