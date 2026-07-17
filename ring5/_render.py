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
        RenderError: The engine is invalid or the plot has no processed data.
    """
    if engine not in VALID_ENGINES:
        raise RenderError(f"Unknown engine {engine!r}. Choose from {sorted(VALID_ENGINES)}.")
    if plot.processed_data is None:
        raise RenderError(f"Plot '{plot.name}' has no processed data to render.")

    try:
        if engine == "plotly":
            # UI sequence (render_controller.py): create_figure + apply_common_layout.
            plotly_fig = plot.create_figure(plot.processed_data, plot.config)
            plotly_fig = plot.apply_common_layout(plotly_fig, plot.config)
            plot.last_generated_fig = plotly_fig
            plot.last_figure_cache_key = None
            return plotly_fig

        # Matplotlib: build straight from the engine-agnostic traces — NO Plotly figure is
        # constructed (the two engines are independent). create_traces + the same legend
        # relabel create_figure would apply, then the traces-direct matplotlib builder.
        import matplotlib.pyplot as plt

        from src.web.pages.ui.plotting.base_plot import _relabel_traces
        from src.web.rendering.matplotlib_figure_builder import (
            build_matplotlib_figure_from_traces,
        )

        traces_result = plot.create_traces(plot.processed_data, plot.config)
        traces_result = _relabel_traces(traces_result, plot.config.get("legend_labels"))
        plot.last_traces = traces_result

        mpl_fig, spec = build_matplotlib_figure_from_traces(
            plot.config, plot.plot_type, traces_result
        )

        # Deregister from pyplot: headless callers loop over many plots
        # (render_portfolio), and pyplot would otherwise pin every figure in
        # its global manager. The Figure object stays fully usable (savefig).
        plt.close(mpl_fig)

        mpl_fig._ring5_spec = spec  # type: ignore[attr-defined]
        return mpl_fig
    except (AttributeError, IndexError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise RenderError(
            f"Could not render plot '{plot.name}' ({plot.plot_type}) with {engine}: {exc}"
        ) from exc
