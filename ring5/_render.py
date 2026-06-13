"""Headless figure rendering — the exact sequences the web UI executes.

One function, two engines. The plotly path is byte-identical
(``fig.to_json()``) to what the running app produces; the matplotlib path
delegates to the SAME shared builder the web component uses
(``src.web.rendering.matplotlib_figure_builder``), so the two cannot
drift. The Streamlit display/caching the web adds around it is the only
difference — and the audit proved it does not affect the produced bytes.
"""

from __future__ import annotations

from typing import Union

import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.engine import VALID_ENGINES, EngineMode
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure

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
        ValueError: Unknown engine, or the plot has no processed data.
    """
    if engine not in VALID_ENGINES:
        raise ValueError(f"Unknown engine {engine!r}. Choose from {sorted(VALID_ENGINES)}.")
    if plot.processed_data is None:
        raise ValueError(f"Plot '{plot.name}' has no processed data to render.")

    # UI sequence (render_controller.py): create_figure + apply_common_layout.
    # Both engines need this — the styled plotly figure is also the
    # enrichment source for the matplotlib spec.
    plotly_fig = plot.create_figure(plot.processed_data, plot.config)
    plotly_fig = plot.apply_common_layout(plotly_fig, plot.config)
    plot.last_generated_fig = plotly_fig

    if engine == "plotly":
        return plotly_fig

    import matplotlib.pyplot as plt

    traces_result = plot.last_traces
    mpl_fig, spec = build_matplotlib_figure(
        plotly_fig,
        plot.config,
        plot.plot_type,
        list(traces_result.traces) if traces_result is not None else [],
        list(traces_result.separator_lines) if traces_result else [],
        list(traces_result.shaded_regions) if traces_result else [],
        list(traces_result.rule_lines) if traces_result else [],
    )

    # Deregister from pyplot: headless callers loop over many plots
    # (render_portfolio), and pyplot would otherwise pin every figure in
    # its global manager. The Figure object stays fully usable (savefig).
    plt.close(mpl_fig)

    mpl_fig._ring5_spec = spec  # type: ignore[attr-defined]
    return mpl_fig
