from apps.blocks.base import BaseBlock
from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
from apps.permissions.checks import (
    filter_viewable_queryset as filter_viewable_queryset_generic,
)
from apps.workflow.permissions import (
    filter_viewable_queryset_state,
)
import json
import uuid


class PivotBlock(BaseBlock, FilterResolutionMixin):
    """Base class for pivot-style blocks.

    Responsibilities:
    - Resolve saved filter and column (view) configs per instance
    - Apply filter schema and collect current selections
    - Build a base queryset and delegate to subclass to produce pivoted columns/rows
    - Return Tabulator-compatible config + data payloads
    """

    template_name = "blocks/table/table_block.html"
    supported_features = ["filters", "column_config"]

    def __init__(self, block_name):
        self.block_name = block_name
        self._block = None
        self._context_cache = {}

    @property
    def block(self):
        if self._block is None:
            try:
                self._block = Block.objects.get(code=self.block_name)
            except Block.DoesNotExist:
                raise Exception(f"Block '{self.block_name}' not registered in admin.")
        return self._block

    # ---- Required subclass hooks ----
    def get_model(self):
        raise NotImplementedError("You must override get_model()")

    def get_base_queryset(self, user):
        """Return an initial queryset for the pivot's data source."""
        raise NotImplementedError("You must override get_base_queryset(user)")

    def get_filter_schema(self, request):
        """Return schema dict for supported filters (like TableBlock)."""
        return {}

    def get_manageable_fields(self, user):
        """Return a curated list of field names allowed in Manage Views.

        Examples: ["item__code", "item__description", "company__name"]
        """
        return []

    def build_pivot(self, queryset, selected_fields, filters, user):
        """Given filtered queryset and selected fields, return (columns, rows).

        columns: list of {"title": str, "field": str}
        rows: list of dicts (Tabulator data)
        """
        raise NotImplementedError("You must override build_pivot(queryset, selected_fields, filters, user)")

    # ---- Column defs for Manage Views (names + labels) ----
    def get_column_defs(self, user, column_config=None):
        from django.contrib.admin.utils import label_for_field
        fields = self.get_manageable_fields(user)
        defs = []
        model = self.get_model()
        for f in fields:
            try:
                title = label_for_field(f, model, return_attr=False)
            except Exception:
                # fallback friendly label
                title = str(f).replace("__", " ").title()
            defs.append({"field": f, "title": title})
        return defs

    # ---- Tabulator options / downloads (reuse TableBlock defaults) ----
    def get_tabulator_default_options(self, user):
        return {
            "layout": "fitColumns",
            "pagination": "local",
            "paginationSize": 20,
            "paginationSizeSelector": [10, 20, 50, 100],
        }

    def get_tabulator_options_overrides(self, user):
        return {}

    def get_tabulator_options(self, user):
        defaults = self.get_tabulator_default_options(user) or {}
        overrides = self.get_tabulator_options_overrides(user) or {}
        return {**defaults, **overrides}

    def get_xlsx_download_default_options(self, request, instance_id=None):
        return {
            "filename": f"{self.block_name}.xlsx",
            "sheetName": f"{self.block_name}",
            "header": {"fillColor": "#004085", "fontColor": "#FFFFFF", "bold": True},
        }

    def get_xlsx_download_options_overrides(self, request, instance_id=None):
        return {}

    def get_xlsx_download_options(self, request, instance_id=None):
        defaults = self.get_xlsx_download_default_options(request, instance_id) or {}
        overrides = self.get_xlsx_download_options_overrides(request, instance_id) or {}
        merged = {**defaults, **overrides}
        for key in ("options", "header"):
            if isinstance(defaults.get(key), dict) or isinstance(overrides.get(key), dict):
                base_sub = defaults.get(key) or {}
                over_sub = overrides.get(key) or {}
                merged[key] = {**base_sub, **over_sub}
        return merged

    def get_pdf_download_default_options(self, request, instance_id=None):
        return {
            "filename": f"{self.block_name}.pdf",
            "orientation": "portrait",
            "title": getattr(self.block, "name", self.block_name),
            "header": {"fillColor": "#003366", "fontColor": "#FFFFFF", "bold": True},
            "options": {"jsPDF": {"unit": "pt", "format": "a4", "compress": True}},
        }

    def get_pdf_download_options_overrides(self, request, instance_id=None):
        return {}

    def get_pdf_download_options(self, request, instance_id=None):
        defaults = self.get_pdf_download_default_options(request, instance_id) or {}
        overrides = self.get_pdf_download_options_overrides(request, instance_id) or {}
        merged = {**defaults, **overrides}
        for key in ("options", "header"):
            if isinstance(defaults.get(key), dict) or isinstance(overrides.get(key), dict):
                base_sub = defaults.get(key) or {}
                over_sub = overrides.get(key) or {}
                merged[key] = {**base_sub, **over_sub}
        return merged

    # ---- Config/data pipeline ----
    def render(self, request, instance_id=None):
        self._context_cache.clear()
        return super().render(request, instance_id=instance_id)

    def _get_context(self, request, instance_id):
        effective_instance_id = instance_id or self._detect_instance_id_from_query(request)
        cache_key = (id(request), effective_instance_id)
        if cache_key not in self._context_cache:
            self._context_cache[cache_key] = self._build_context(request, effective_instance_id)
        return self._context_cache[cache_key]

    def _detect_instance_id_from_query(self, request):
        try:
            keys = request.GET.keys()
        except Exception:
            return None
        prefix = f"{self.block_name}__"
        for key in keys:
            if not key.startswith(prefix):
                continue
            rest = key[len(prefix):]
            if "__" not in rest:
                continue
            candidate, tail = rest.split("__", 1)
            if (
                tail.startswith("column_config_id")
                or tail.startswith("filter_config_id")
                or tail.startswith("filters.")
            ):
                return candidate
        return None

    def get_config(self, request, instance_id=None):
        context = dict(self._get_context(request, instance_id))
        context.pop("data", None)
        return context

    def get_data(self, request, instance_id=None):
        context = self._get_context(request, instance_id)
        return {"data": context.get("data")}

    def get_column_config_queryset(self, user):
        return BlockColumnConfig.objects.filter(user=user, block=self.block)

    def get_filter_config_queryset(self, user):
        return BlockFilterConfig.objects.filter(user=user, block=self.block)

    def _select_configs(self, request, instance_id=None):
        user = request.user
        ns = f"{self.block_name}__{instance_id}__" if instance_id else f"{self.block_name}__"
        column_config_id = (
            request.GET.get(f"{ns}column_config_id")
            or (request.GET.get(f"{self.block_name}__column_config_id") if instance_id else None)
            or request.GET.get("column_config_id")
        )
        filter_config_id = (
            request.GET.get(f"{ns}filter_config_id")
            or (request.GET.get(f"{self.block_name}__filter_config_id") if instance_id else None)
            or request.GET.get("filter_config_id")
        )
        column_configs = self.get_column_config_queryset(user)
        filter_configs = self.get_filter_config_queryset(user)
        active_column_config = None
        if column_config_id:
            try:
                active_column_config = column_configs.get(pk=column_config_id)
            except BlockColumnConfig.DoesNotExist:
                pass
        if not active_column_config:
            active_column_config = column_configs.filter(is_default=True).first()
        active_filter_config = None
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                pass
        if not active_filter_config:
            active_filter_config = filter_configs.filter(is_default=True).first()
        selected_fields = active_column_config.fields if active_column_config else []
        return (
            column_configs,
            filter_configs,
            active_column_config,
            active_filter_config,
            selected_fields,
        )

    def _resolve_filters(self, request, active_filter_config, instance_id=None):
        user = request.user
        try:
            raw_schema = self.get_filter_schema(request)
        except TypeError:
            raw_schema = self.get_filter_schema(user)
        filter_schema = self._resolve_filter_schema(raw_schema, user)
        base_values = active_filter_config.values if active_filter_config else {}
        ns_prefix = (
            f"{self.block_name}__{instance_id}__filters."
            if instance_id
            else f"{self.block_name}__filters."
        )
        selected_filter_values = self._collect_filters(
            request.GET, filter_schema, base=base_values, prefix=ns_prefix, allow_flat=False
        )
        return filter_schema, selected_filter_values

    def _build_context(self, request, instance_id):
        user = request.user
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

        # Build base queryset and enforce row-level visibility
        qs = self.get_base_queryset(user)
        qs = filter_viewable_queryset_generic(user, qs)
        qs = filter_viewable_queryset_state(user, qs)

        # Subclass builds pivot output
        columns, rows = self.build_pivot(qs, selected_fields, selected_filter_values, user)

        # Ensure we have an instance_id
        instance_id = instance_id or uuid.uuid4().hex[:8]

        # Build simplified fields list for Manage Views UI: use current selection order
        defs = self.get_column_defs(user, active_column_config)
        label_map = {d["field"]: d.get("title", d["field"]) for d in defs}
        fields = [
            {"name": str(f), "label": label_map.get(str(f), str(f)), "mandatory": False, "editable": False}
            for f in (selected_fields or [])
        ]

        return {
            "block_name": self.block_name,
            "instance_id": instance_id,
            "block_title": getattr(self.block, "name", self.block_name),
            "block": self.block,
            "fields": fields,
            "tabulator_options": self.get_tabulator_options(user),
            "xlsx_download": json.dumps(self.get_xlsx_download_options(request, instance_id) or {}),
            "pdf_download": json.dumps(self.get_pdf_download_options(request, instance_id) or {}),
            "column_configs": column_configs,
            "filter_configs": filter_configs,
            "active_column_config_id": active_column_config.id if active_column_config else None,
            "active_filter_config_id": active_filter_config.id if active_filter_config else None,
            "columns": columns,
            "data": json.dumps(rows),
            "filter_schema": filter_schema,
            "selected_filter_values": selected_filter_values,
        }

