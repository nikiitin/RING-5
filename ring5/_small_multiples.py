"""Public, headless boundary for rendering one plot as faceted panels."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.engine import EngineMode
from src.core.models.visualization.small_multiples_spec import SmallMultiplesSpec
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering.dashboard_builder import DashboardFigure
from src.web.rendering.small_multiples_builder import render_small_multiples as _render

from ring5.errors import RenderError


def render_small_multiples(
    plots: Sequence[BasePlot],
    spec: SmallMultiplesSpec,
    *,
    engine: EngineMode = "plotly",
) -> DashboardFigure:
    # [impl->req~ring5.plots.small-multiples~1]
    """Render a validated small-multiples specification headlessly.

    Args:
        plots: Live registered plots containing the plot referenced by ``spec``.
        spec: Resolved facets, panel labels, ordering, and shared-axis layout.
        engine: Rendering engine, ``"plotly"`` or ``"matplotlib"``.

    Returns:
        A complete Plotly or Matplotlib figure.

    Raises:
        RenderError: The plot is unavailable or a facet can no longer be rendered.
    """
    try:
        figure = _render(plots, spec, engine=engine)
        if engine == "matplotlib":
            import matplotlib.pyplot as plt

            plt.close(cast(MplFigure, figure))
        return figure
    except (AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise RenderError(f"Could not render small multiples: {exc}") from exc


__all__ = ["render_small_multiples"]
