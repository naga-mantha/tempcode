from __future__ import annotations

from typing import Tuple

from plotly import graph_objects as go

from django_bi.blocks.block_types.chart.chart_block import ChartBlock


class DialChartBlock(ChartBlock):
    """Generic dial (gauge) chart block using Plotly's Indicator.

    Subclasses must implement:
      - get_value(user, filters) -> float  (0..100)
      - get_target(user, filters) -> float (0..100), optional; default 100
    They may override :meth:`get_gauge_overrides` to tweak gauge styling.
    """

    def __init__(self, block_name: str, default_layout: dict | None = None):
        super().__init__(block_name, default_layout=default_layout or {
            "margin": {"l": 30, "r": 30, "t": 30, "b": 10},
        })

    # ----- subclass hooks --------------------------------------------------
    def get_value(self, user, filters) -> float:
        raise NotImplementedError

    def get_target(self, user, filters) -> float:
        return 100.0

    def get_gauge_overrides(self, user, filters) -> dict:
        """Return plotly gauge overrides; shallow-merged onto defaults."""
        return {}

    # ----- figure builder --------------------------------------------------
    def get_figure(self, user, filters):
        value = float(self.get_value(user, filters) or 0.0)
        target = float(self.get_target(user, filters) or 0.0)
        # clamp
        value = max(0.0, min(100.0, value))
        target = max(0.0, min(100.0, target))

        # default gauge styling with a threshold marker at target
        defaults = {
            "mode": "gauge+number",
            "value": value,
            "number": {"suffix": "%"},
            "gauge": {
                "axis": {"range": [0, 100]},
                "bar": {"color": "#1E88E5"},
                "steps": [
                    {"range": [0, target], "color": "#C8E6C9"},  # green-ish up to target
                    {"range": [target, 100], "color": "#FFCDD2"},  # red-ish beyond
                ],
                "threshold": {
                    "line": {"color": "#C62828", "width": 3},
                    "thickness": 0.9,
                    "value": target,
                },
            },
        }
        overrides = self.get_gauge_overrides(user, filters) or {}
        trace = go.Indicator(**{**defaults, **overrides})
        fig = go.Figure(data=[trace])
        return fig

