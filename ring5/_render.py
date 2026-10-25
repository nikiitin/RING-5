"""Render a registered plot through one neutral preparation and a native engine."""

from __future__ import annotations

from typing import Union

import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.engine import VALID_ENGINES, EngineMode
from src.web.pages.ui.plotting.base_plot import BasePlot
from ring5.errors import RenderError

Figure = Union[go.Figure, MplFigure]


def render_figure(plot: BasePlot, *, engine: EngineMode = "plotly") -> Figure:
    """Render *plot* with the requested engine, headlessly.

    The plot must carry ``processed_data`` and ``config`` (exactly what the
    web UI requires before rendering). Engine choice is an explicit
    argument — the public API never consults the web layer's session-state
    engine toggle.

    Args:
        plot: A configured plot (``Session.create_plot`` or a portfolio
            restore both produce one).
        engine: ``"plotly"`` or ``"matplotlib"``.

    Returns:
        A ``plotly.graph_objects.Figure`` or ``matplotlib.figure.Figure``.
        Matplotlib figures are deregistered from pyplot's global manager
        (no accumulation in long-running scripts; ``savefig`` still works)
        and carry the resolved ``FigureConfig`` as ``fig._ring5_spec`` so
        PGF export can apply the LaTeX preamble.

    Raises:
        RenderError: The engine, data, trace family, or configuration cannot be rendered.
    """
    # [impl->req~ring5.figure.accessible-themes~1]
    if engine not in VALID_ENGINES:
        raise RenderError(f"Unknown engine {engine!r}. Choose from {sorted(VALID_ENGINES)}.")
    if plot.processed_data is None:
        raise RenderError(f"Plot '{plot.name}' has no processed data to render.")

    try:
        from src.web.rendering.figure_preparation import prepare_figure
        from src.web.rendering.matplotlib_figure_builder import (
            build_matplotlib_figure_from_prepared,
        )
        from src.web.rendering.plotly_figure_builder import build_plotly_figure

        prepared = prepare_figure(
            plot.processed_data, plot.config, plot.plot_type, plot.create_traces
        )
        if engine == "plotly":
            figure = build_plotly_figure(prepared)
            plot.publish_figure(figure, prepared)
            return figure

        mpl_figure, _ = build_matplotlib_figure_from_prepared(prepared)
        plot.publish_figure(mpl_figure, prepared)
        return mpl_figure
    except (AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise RenderError(
            f"Could not render plot '{plot.name}' ({plot.plot_type}) with {engine}: {exc}"
        ) from exc
