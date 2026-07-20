"""Public, headless boundary for rendering multi-plot dashboards."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from matplotlib.figure import Figure as MplFigure
from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.core.models.visualization.engine import EngineMode
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering.dashboard_builder import DashboardFigure
from src.web.rendering.dashboard_builder import render_dashboard as _build_dashboard

from ring5.errors import RenderError


def render_dashboard(
    plots: Sequence[BasePlot],
    spec: DashboardSpec,
    *,
    engine: EngineMode = "plotly",
) -> DashboardFigure:
    # [impl->req~ring5.plots.multi-panel-dashboard~1]
    """Render a validated dashboard with Plotly or Matplotlib.

    Args:
        plots: Live registered plots referenced by ``spec``.
        spec: Validated dashboard grid and presentation settings.
        engine: Rendering engine, ``"plotly"`` or ``"matplotlib"``.

    Returns:
        A complete Plotly or Matplotlib dashboard figure.

    Raises:
        RenderError: A referenced plot is unavailable or rendering fails.
    """
    try:
        figure = _build_dashboard(plots, spec, engine=engine)
        if engine == "matplotlib":
            import matplotlib.pyplot as plt

            plt.close(cast(MplFigure, figure))
        return figure
    except (AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise RenderError(f"Could not render dashboard: {exc}") from exc


__all__ = ["render_dashboard"]
