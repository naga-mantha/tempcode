"""Chart block implementations using Plotly."""

import json
from abc import ABC, abstractmethod
import uuid

import plotly.graph_objects as go

from apps.blocks.base import BaseBlock
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.models.config_templates import BlockFilterLayoutTemplate
from apps.blocks.models.block_filter_layout import BlockFilterLayout
from apps.blocks.services.blocks_filter_utils import FilterResolutionMixin
from apps.permissions.checks import (
    filter_viewable_queryset as filter_viewable_queryset_generic,
    can_read_field as can_read_field_generic,
)
from apps.workflow.permissions import (
    filter_viewable_queryset_state,
    can_read_field_state,
)
from django.core.exceptions import PermissionDenied


class ChartBlock(BaseBlock, FilterResolutionMixin, ABC):
    """Base block for rendering Plotly charts.

    Subclasses are expected to provide a concrete implementation of
    :meth:`get_figure` which returns a :class:`plotly.graph_objects.Figure`.
    The default implementation handles filter resolution and passes the
    resulting figure and layout to the template.
    """

    template_name = "blocks/chart/chart_block.html"
    supported_features = ["filters"]

    def __init__(self, block_name, default_layout=None):
        self.block_name = block_name
        self.default_layout = default_layout or {}
        self._block = None
        self._context_cache = {}
        self._layout_overrides = {}

    def render(self, request, instance_id=None):
        """Clear cached context and render the block."""
        self._context_cache.clear()
        return super().render(request, instance_id=instance_id)

    @property
    def block(self):
        if self._block is None:
            try:
                self._block = Block.objects.get(code=self.block_name)
            except Block.DoesNotExist as exc:  # pragma: no cover - defensive
                raise Exception(
                    f"Block '{self.block_name}' not registered in admin."
                ) from exc
        return self._block

    # ----- hooks for subclasses -------------------------------------------------
    @abstractmethod
    def get_filter_schema(self, request):
        """Return a filter schema dictionary."""

    @abstractmethod
    def get_figure(self, user, filters):
        """Return a Plotly Figure based on ``filters`` for ``user``."""

    def get_layout(self, user):
        """Return Plotly layout for the chart (defaults + per-request overrides).

        Overrides can be supplied via query params (both standalone and embedded):
          - layout.width=<int>
          - layout.height=<int>
        These are merged shallowly onto ``default_layout`` for the current request.
        """
        layout = dict(self.default_layout)
        try:
            overrides = dict(self._layout_overrides or {})
        except Exception:
            overrides = {}
        if overrides:
            layout.update(overrides)
        return layout
    
    # ----- request helpers -----------------------------------------------------
    def _parse_layout_overrides(self, request):
        """Extract safe Plotly layout overrides from query params.

        Currently supports numeric width/height only, via keys:
          - layout.width
          - layout.height
        """
        q = getattr(request, "GET", None)
        if not q:
            return {}
        out = {}
        for key in ("layout.width", "layout.height"):
            try:
                raw = q.get(key)
                if raw is None or raw == "":
                    continue
                val = int(str(raw).strip())
                if val > 0:
                    out[key.split(".")[-1]] = val
            except Exception:
                continue
        return out

    def has_view_permission(self, user):
        """Placeholder for future permission checks."""
        return True

    # ----- filtering helpers ----------------------------------------------------
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

    def filter_queryset(self, user, queryset):
        """Filter ``queryset`` to rows ``user`` may view."""
        queryset = filter_viewable_queryset_generic(user, queryset)
        return filter_viewable_queryset_state(user, queryset)

    def _select_filter_config(self, request, instance_id=None):
        user = request.user
        ns = f"{self.block_name}__{instance_id}__" if instance_id else f"{self.block_name}__"
        filter_config_id = (
            request.GET.get(f"{ns}filter_config_id")
            or (request.GET.get(f"{self.block_name}__filter_config_id") if instance_id else None)
            or request.GET.get("filter_config_id")
        )
        filter_configs = self.get_filter_config_queryset(user)
        active_filter_config = None
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                pass
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
        return filter_configs, active_filter_config

    def _resolve_filters(self, request, active_filter_config, instance_id=None):
        user = request.user
        try:
            raw_schema = self.get_filter_schema(request)
        except TypeError:
            raw_schema = self.get_filter_schema(user)
        filter_schema = self._resolve_filter_schema(raw_schema, user)
        # Remove filters for fields the user cannot read
        filtered_schema = {}
        for key, cfg in filter_schema.items():
            model = cfg.get("model")
            field_name = cfg.get("field")
            if model and field_name:
                if not (
                    can_read_field_generic(user, model, field_name)
                    and can_read_field_state(user, model, field_name)
                ):
                    continue
            filtered_schema[key] = cfg
        filter_schema = filtered_schema
        raw_base = active_filter_config.values if active_filter_config else {}
        base_values = {k: v for k, v in raw_base.items() if k in filter_schema}
        ns_prefix = (
            f"{self.block_name}__{instance_id}__filters."
            if instance_id
            else f"{self.block_name}__filters."
        )
        selected_filter_values = self._collect_filters(
            request.GET, filter_schema, base=base_values, prefix=ns_prefix, allow_flat=False
        )
        return filter_schema, selected_filter_values

    # ----- context building -----------------------------------------------------
    def _build_context(self, request, instance_id):
        user = request.user
        if not self.has_view_permission(user):
            raise PermissionDenied

        filter_configs, active_filter_config = self._select_filter_config(request, instance_id)
        # Capture per-request layout overrides before computing figure/layout
        try:
            self._layout_overrides = self._parse_layout_overrides(request)
        except Exception:
            self._layout_overrides = {}
        filter_schema, selected_filter_values = self._resolve_filters(
            request, active_filter_config, instance_id
        )
        figure = self.get_figure(user, selected_filter_values)
        # ensure layout defaults are applied
        layout = self.get_layout(user)
        if isinstance(figure, go.Figure):
            figure.update_layout(layout)
            figure_dict = figure.to_plotly_json()
        else:
            figure_dict = dict(figure)
            figure_dict.setdefault("layout", {}).update(layout)
        # Ensure we have an instance_id for DOM ids
        instance_id = instance_id or uuid.uuid4().hex[:8]
        # Fetch admin-defined filter layout if available
        try:
            # Per-user override; fallback to admin
            user_layout = BlockFilterLayout.objects.filter(block=self.block, user=user).first()
            if user_layout and isinstance(user_layout.layout, dict):
                filter_layout = dict(user_layout.layout)
            else:
                layout_tpl = BlockFilterLayoutTemplate.objects.filter(block=self.block).first()
                filter_layout = dict(layout_tpl.layout or {}) if layout_tpl and isinstance(layout_tpl.layout, dict) else None
        except Exception:
            filter_layout = None
        return {
            "block_name": self.block_name,
            "block_title": getattr(self.block, "name", self.block_name),
            "block": self.block,
            "instance_id": instance_id,
            "filter_layout": filter_layout,
            "filter_configs": filter_configs,
            "active_filter_config_id": active_filter_config.id
            if active_filter_config
            else None,
            "filter_schema": filter_schema,
            "selected_filter_values": selected_filter_values,
            "figure": figure_dict,
        }

    def _get_context(self, request, instance_id):
        """Retrieve (and cache) rendering context for this block instance.

        If ``instance_id`` is not explicitly provided (as is the case when a
        chart block is rendered on its own page), we attempt to infer a
        previously-used instance namespace from the query string. This mirrors
        the behaviour of :class:`TableBlock` so that filter selections persist
        across form submissions. Without this, the randomly generated
        ``instance_id`` used for form field names would change on each request
        and submitted filters would never be detected.
        """

        effective_instance_id = instance_id or self._detect_instance_id_from_query(request)
        cache_key = (id(request), effective_instance_id)
        if cache_key not in self._context_cache:
            self._context_cache[cache_key] = self._build_context(request, effective_instance_id)
        return self._context_cache[cache_key]

    def _detect_instance_id_from_query(self, request):
        """Best-effort extraction of ``instance_id`` from namespaced GET params.

        Looks for keys like::

            <block>__<instance>__filter_config_id
            <block>__<instance>__filters.<name>

        Returns the first detected instance id, or ``None`` if not found. This
        allows filter submissions to round-trip correctly for standalone chart
        pages where the instance namespace is generated server-side.
        """

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
            if tail.startswith("filter_config_id") or tail.startswith("filters."):
                return candidate
        return None

    def get_config(self, request, instance_id=None):
        context = dict(self._get_context(request, instance_id))
        context.pop("figure", None)
        return context

    def get_data(self, request, instance_id=None):
        context = self._get_context(request, instance_id)
        figure = context.get("figure", {})
        return {"figure": json.dumps(figure)}


class DonutChartBlock(ChartBlock, ABC):
    """Render a donut (pie) chart."""

    @abstractmethod
    def get_chart_data(self, user, filters):
        """Return mapping with ``labels`` and ``values`` lists."""

    def get_pie_default_trace(self, user):
        """Base defaults for donut/pie trace options.

        Force percentage text inside slices to avoid overflow/glitches in
        smaller embedded tiles.
        """
        return {
            "hole": 0.4,
            "textposition": "inside",
            "insidetextorientation": "radial",
            "textinfo": "percent",
        }

    def get_pie_trace_overrides(self, user):
        """Override point for apps to tweak pie trace options."""
        return {}

    def get_figure(self, user, filters):
        data = self.get_chart_data(user, filters)
        labels = data.get("labels", [])
        values = data.get("values", [])
        defaults = self.get_pie_default_trace(user) or {}
        overrides = self.get_pie_trace_overrides(user) or {}
        trace_kwargs = {**defaults, **overrides}
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, **trace_kwargs)])
        return fig


class BarChartBlock(ChartBlock, ABC):
    """Render a bar chart."""

    @abstractmethod
    def get_chart_data(self, user, filters):
        """Return mapping with ``x`` and ``y`` data lists."""

    def get_bar_default_trace(self, user):
        """Base defaults for bar trace options."""
        return {"orientation": "v"}

    def get_bar_trace_overrides(self, user):
        """Override point for apps to tweak bar trace options."""
        return {}

    def get_figure(self, user, filters):
        data = self.get_chart_data(user, filters)
        x = data.get("x", [])
        y = data.get("y", [])
        defaults = self.get_bar_default_trace(user) or {}
        overrides = self.get_bar_trace_overrides(user) or {}
        trace_kwargs = {**defaults, **overrides}
        fig = go.Figure(data=[go.Bar(x=x, y=y, **trace_kwargs)])
        return fig


class LineChartBlock(ChartBlock, ABC):
    """Render a line chart."""

    @abstractmethod
    def get_chart_data(self, user, filters):
        """Return mapping with ``x`` and ``y`` data lists."""

    def get_line_default_trace(self, user):
        """Base defaults for line trace options."""
        return {"mode": "lines"}

    def get_line_trace_overrides(self, user):
        """Override point for apps to tweak line trace options."""
        return {}

    def get_figure(self, user, filters):
        data = self.get_chart_data(user, filters)
        x = data.get("x", [])
        y = data.get("y", [])
        defaults = self.get_line_default_trace(user) or {}
        overrides = self.get_line_trace_overrides(user) or {}
        trace_kwargs = {**defaults, **overrides}
        fig = go.Figure(data=[go.Scatter(x=x, y=y, **trace_kwargs)])
        return fig


__all__ = [
    "ChartBlock",
    "DonutChartBlock",
    "BarChartBlock",
    "LineChartBlock",
]

