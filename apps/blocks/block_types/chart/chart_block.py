"""Chart block implementations using Plotly."""

import json
from abc import ABC, abstractmethod

import plotly.graph_objects as go

from apps.blocks.base import BaseBlock
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
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

    def render(self, request):
        """Clear cached context and render the block."""
        self._context_cache.clear()
        return super().render(request)

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
        """Return layout overrides for the chart."""
        return dict(self.default_layout)

    def has_view_permission(self, user):
        """Placeholder for future permission checks."""
        return True

    # ----- filtering helpers ----------------------------------------------------
    def get_filter_config_queryset(self, user):
        return BlockFilterConfig.objects.filter(user=user, block=self.block)

    def _select_filter_config(self, request):
        user = request.user
        ns = f"{self.block_name}__"
        filter_config_id = request.GET.get(f"{ns}filter_config_id") or request.GET.get("filter_config_id")
        filter_configs = self.get_filter_config_queryset(user)
        active_filter_config = None
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                pass
        if not active_filter_config:
            active_filter_config = filter_configs.filter(is_default=True).first()
        return filter_configs, active_filter_config

    def _resolve_filters(self, request, active_filter_config):
        user = request.user
        try:
            raw_schema = self.get_filter_schema(request)
        except TypeError:
            raw_schema = self.get_filter_schema(user)
        filter_schema = self._resolve_filter_schema(raw_schema, user)
        base_values = active_filter_config.values if active_filter_config else {}
        ns_prefix = f"{self.block_name}__filters."
        selected_filter_values = self._collect_filters(
            request.GET, filter_schema, base=base_values, prefix=ns_prefix, allow_flat=False
        )
        return filter_schema, selected_filter_values

    # ----- context building -----------------------------------------------------
    def _build_context(self, request):
        user = request.user
        if not self.has_view_permission(user):
            raise PermissionDenied

        filter_configs, active_filter_config = self._select_filter_config(request)
        filter_schema, selected_filter_values = self._resolve_filters(
            request, active_filter_config
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
        return {
            "block_name": self.block_name,
            "filter_configs": filter_configs,
            "active_filter_config_id": active_filter_config.id
            if active_filter_config
            else None,
            "filter_schema": filter_schema,
            "selected_filter_values": selected_filter_values,
            "figure": figure_dict,
        }

    def _get_context(self, request):
        cache_key = id(request)
        if cache_key not in self._context_cache:
            self._context_cache = {cache_key: self._build_context(request)}
        return self._context_cache[cache_key]

    def get_config(self, request):
        context = dict(self._get_context(request))
        context.pop("figure", None)
        return context

    def get_data(self, request):
        context = self._get_context(request)
        figure = context.get("figure", {})
        return {"figure": json.dumps(figure)}


class DonutChartBlock(ChartBlock, ABC):
    """Render a donut (pie) chart."""

    @abstractmethod
    def get_chart_data(self, user, filters):
        """Return mapping with ``labels`` and ``values`` lists."""

    def get_figure(self, user, filters):
        data = self.get_chart_data(user, filters)
        labels = data.get("labels", [])
        values = data.get("values", [])
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
        return fig


class BarChartBlock(ChartBlock, ABC):
    """Render a bar chart."""

    @abstractmethod
    def get_chart_data(self, user, filters):
        """Return mapping with ``x`` and ``y`` data lists."""

    def get_figure(self, user, filters):
        data = self.get_chart_data(user, filters)
        x = data.get("x", [])
        y = data.get("y", [])
        fig = go.Figure(data=[go.Bar(x=x, y=y)])
        return fig


class LineChartBlock(ChartBlock, ABC):
    """Render a line chart."""

    @abstractmethod
    def get_chart_data(self, user, filters):
        """Return mapping with ``x`` and ``y`` data lists."""

    def get_figure(self, user, filters):
        data = self.get_chart_data(user, filters)
        x = data.get("x", [])
        y = data.get("y", [])
        fig = go.Figure(data=[go.Scatter(x=x, y=y, mode="lines")])
        return fig


__all__ = [
    "ChartBlock",
    "DonutChartBlock",
    "BarChartBlock",
    "LineChartBlock",
]

