from apps.blocks.base import BaseBlock
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.models.config_templates import BlockFilterLayoutTemplate
from apps.blocks.models.block_filter_layout import BlockFilterLayout
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
import json
import uuid


class PivotBlock(BaseBlock, FilterResolutionMixin):
    """Base class for pivot-style blocks with a pivot-specific template."""

    template_name = "blocks/pivot/pivot_table.html"
    supported_features = ["filters"]

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

    # Subclass hooks
    def get_model(self):
        raise NotImplementedError

    def get_filter_schema(self, request):
        return {}

    # Config/data
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
                tail.startswith("pivot_config_id")
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

    def get_filter_config_queryset(self, user):
        from django.db.models import Q, Case, When, IntegerField
        qs = BlockFilterConfig.objects.filter(block=self.block).filter(
            Q(user=user) | Q(visibility=BlockFilterConfig.VISIBILITY_PUBLIC)
        )
        return qs.annotate(
            _vis_order=Case(
                When(visibility=BlockFilterConfig.VISIBILITY_PRIVATE, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_vis_order", "name")

    def _build_context(self, request, instance_id):
        user = request.user
        filter_configs = self.get_filter_config_queryset(user)
        active_filter_config = None
        ns = f"{self.block_name}__{instance_id}__"
        filter_config_id = (
            request.GET.get(f"{ns}filter_config_id")
            or (request.GET.get(f"{self.block_name}__filter_config_id") if instance_id else None)
            or request.GET.get("filter_config_id")
        )
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                active_filter_config = None
        if not active_filter_config:
            try:
                active_filter_config = (
                    filter_configs.filter(user=user, is_default=True).first()
                    or filter_configs.filter(visibility=BlockFilterConfig.VISIBILITY_PUBLIC, is_default=True).first()
                    or filter_configs.filter(user=user).first()
                    or filter_configs.filter(visibility=BlockFilterConfig.VISIBILITY_PUBLIC).first()
                )
            except Exception:
                active_filter_config = None

        # Resolve filters
        try:
            raw_schema = self.get_filter_schema(request)
        except TypeError:
            raw_schema = self.get_filter_schema(user)
        filter_schema = self._resolve_filter_schema(raw_schema, user)
        base_values = active_filter_config.values if active_filter_config else {}
        ns_prefix = f"{self.block_name}__{instance_id}__filters."
        selected_filter_values = self._collect_filters(request.GET, filter_schema, base=base_values, prefix=ns_prefix, allow_flat=False)

        # Resolve pivot config selection if subclass provides a selector
        pivot_configs = []
        active_pivot_config = None
        if hasattr(self, "_select_pivot_config"):
            try:
                pivot_configs, active_pivot_config = self._select_pivot_config(request, instance_id)
            except TypeError:
                pivot_configs, active_pivot_config = self._select_pivot_config(request)

        # Ensure we have an instance_id for consistent namespacing in the template
        instance_id = instance_id or uuid.uuid4().hex[:8]

        # Make active pivot config available to subclass during building
        if active_pivot_config is not None:
            setattr(self, "_active_pivot_config", active_pivot_config)
        try:
            # Subclasses build columns + data; return Tabulator config
            columns, rows = self.build_columns_and_rows(user, selected_filter_values)
        finally:
            if hasattr(self, "_active_pivot_config"):
                delattr(self, "_active_pivot_config")

        # Admin-defined filter layout
        filter_layout = self._get_filter_layout_dict()
        # Make user available for layout resolution similar to TableBlock
        self._current_user = user
        try:
            ctx = {
                "block_name": self.block_name,
                "instance_id": instance_id,
                "block_title": getattr(self.block, "name", self.block_name),
                "block": self.block,
                "filter_layout": filter_layout,
                "columns": columns,
                "data": json.dumps(rows),
                "tabulator_options": self.get_tabulator_options(user),
                "xlsx_download": json.dumps(self.get_xlsx_download_options(request, instance_id) or {}),
                "pdf_download": json.dumps(self.get_pdf_download_options(request, instance_id) or {}),
                "filter_configs": filter_configs,
                "active_filter_config_id": active_filter_config.id if active_filter_config else None,
                "pivot_configs": pivot_configs,
                "active_pivot_config_id": getattr(active_pivot_config, "id", None) if active_pivot_config else None,
                "filter_schema": filter_schema,
                "selected_filter_values": selected_filter_values,
            }
        finally:
            if hasattr(self, "_current_user"):
                delattr(self, "_current_user")
        return ctx

    def _get_filter_layout_dict(self):
        try:
            user_layout = None
            # Prefer per-user
            if hasattr(self, "_current_user") and self._current_user:
                user_layout = BlockFilterLayout.objects.filter(block=self.block, user=self._current_user).first()
            if user_layout and isinstance(user_layout.layout, dict):
                return dict(user_layout.layout)
            tpl = BlockFilterLayoutTemplate.objects.filter(block=self.block).first()
            return dict(tpl.layout or {}) if tpl and isinstance(tpl.layout, dict) else None
        except Exception:
            return None

    def get_tabulator_default_options(self, user):
        return {
            "layout": "fitDataFill",
            "pagination": "local",
            "paginationSize": 10,
            "paginationSizeSelector": [10, 20, 50, 100],
        }

    def get_tabulator_options_overrides(self, user):
        return {}

    def get_tabulator_options(self, user):
        defaults = self.get_tabulator_default_options(user) or {}
        overrides = self.get_tabulator_options_overrides(user) or {}
        return {**defaults, **overrides}

    # Subclasses must provide this (return columns, rows)
    def build_columns_and_rows(self, user, filter_values):
        raise NotImplementedError

    # -------------------------------------------------------------
    # Download options (XLSX/PDF) similar to TableBlock
    # -------------------------------------------------------------
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
        # Shallow merge for nested dicts we know about
        for key in ("header", "options"):
            if isinstance(defaults.get(key), dict) or isinstance(overrides.get(key), dict):
                base_sub = defaults.get(key) or {}
                over_sub = overrides.get(key) or {}
                merged[key] = {**base_sub, **over_sub}
        return merged

    def get_pdf_download_default_options(self, request, instance_id=None):
        # Keep defaults minimal; Tabulator + jsPDF options are applied client-side
        return {
            "filename": f"{self.block_name}.pdf",
            "orientation": "portrait",
            "header": {"fillColor": "#003366", "fontColor": "#FFFFFF", "bold": True},
            "options": {"jsPDF": {"unit": "pt", "format": "a4", "compress": True}},
        }

    def get_pdf_download_options_overrides(self, request, instance_id=None):
        return {}

    def get_pdf_download_options(self, request, instance_id=None):
        defaults = self.get_pdf_download_default_options(request, instance_id) or {}
        overrides = self.get_pdf_download_options_overrides(request, instance_id) or {}
        merged = {**defaults, **overrides}
        for key in ("header", "options"):
            if isinstance(defaults.get(key), dict) or isinstance(overrides.get(key), dict):
                base_sub = defaults.get(key) or {}
                over_sub = overrides.get(key) or {}
                merged[key] = {**base_sub, **over_sub}
        return merged
