"""
Chart Presenter — renders chart area controls, engine selector, and displays.

Provides:
    - Auto-refresh toggle and manual Refresh button
    - Engine selector (Plotly / Matplotlib)
    - Plotly interactive chart rendering with relayout feedback
    - Matplotlib chart rendering via FigureConfig pipeline
    - Download section wiring
    - Error display

All Streamlit rendering for the chart area is centralised here.
The controller orchestrates figure generation and delegates all
``st.*`` display calls to this presenter.
"""

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from src.core.models.visualization.trace_config import TraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.components.plotting.interactive_plot import interactive_plotly_chart
from src.web.pages.ui.plotting.download_section import render_download_section
from src.web.rendering.config_builder import ConfigSpecBuilder, PlotlyFigureSpecBuilder
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer


class ChartPresenter:
    """
    Renders the interactive chart area: refresh controls, engine selector,
    chart display (Plotly or Matplotlib), and download section.

    All methods are ``@staticmethod`` — no instance state.

    Usage::

        controls = ChartPresenter.render_refresh_controls(
            plot_id=1, auto_refresh=True, config_changed=True
        )
        if controls["should_generate"]:
            # Controller generates figure, then:
            engine = ChartPresenter.render_engine_selector(plot_id, current)
            ChartPresenter.render_plotly_chart(fig, plot_id, name, config)
    """

    # ── Refresh controls ─────────────────────────────────────────

    @staticmethod
    def render_refresh_controls(
        plot_id: int,
        auto_refresh: bool,
        config_changed: bool,
    ) -> dict[str, Any]:
        """
        Render auto-refresh toggle and manual Refresh button.

        Args:
            plot_id: Plot ID for unique keys.
            auto_refresh: Current auto-refresh state.
            config_changed: Whether config changed since last render.

        Returns:
            Dict with:
                - auto_refresh (bool): New toggle state.
                - manual_refresh (bool): Refresh button clicked.
                - should_generate (bool): Whether to regenerate figure.
        """
        r1, r2 = st.columns([1, 3])
        with r1:
            new_auto: bool = st.toggle(
                "Auto-refresh",
                value=auto_refresh,
                key=f"auto_t_{plot_id}",
            )
        with r2:
            manual: bool = st.button("Refresh Plot", key=f"refresh_{plot_id}", width="stretch")

        should_generate: bool = manual or (new_auto and config_changed)

        return {
            "auto_refresh": new_auto,
            "manual_refresh": manual,
            "should_generate": should_generate,
        }

    # ── Engine selector ──────────────────────────────────────────

    @staticmethod
    def render_engine_selector(
        plot_id: int,
        current_engine: str,
    ) -> str | None:
        """
        Render engine-selection pills (Plotly / Matplotlib).

        Args:
            plot_id: Plot ID for unique widget key.
            current_engine: Currently active engine (``"plotly"``
                or ``"matplotlib"``).

        Returns:
            The selected engine string, or ``None`` if nothing was
            selected (e.g. user deselected).
        """
        engine_choice: str | None = st.pills(
            "Engine",
            options=["plotly", "matplotlib"],
            format_func=lambda x: (
                ":material/interactive_space: Plotly"
                if x == "plotly"
                else ":material/description: LaTeX (Matplotlib)"
            ),
            selection_mode="single",
            default=current_engine,
            key=f"engine_selector_{plot_id}",
        )
        return engine_choice

    # ── Plotly chart display ─────────────────────────────────────

    @staticmethod
    def render_plotly_chart(
        fig: go.Figure,
        plot_id: int,
        plot_name: str,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Render an interactive Plotly chart with relayout feedback.

        Displays the chart via the custom ``interactive_plotly_chart``
        component (NOT ``st.plotly_chart``), followed by the download
        section.

        Args:
            fig: Plotly ``go.Figure`` to render.
            plot_id: Plot identifier for widget keys.
            plot_name: Human-readable name for download filenames.
            config: Plot configuration (used for export defaults).

        Returns:
            Relayout event data dict if the user interacted with
            the chart (zoom, pan, legend drag), or ``None``.
        """
        plotly_config: dict[str, Any] = {
            "responsive": False,
            "editable": True,
            "edits": {
                "legendPosition": True,
                "titleText": False,
                "axisTitleText": False,
                "annotationText": False,
                "annotationPosition": False,
                "colorbarTitleText": False,
            },
            "modeBarButtonsToAdd": [
                "drawline",
                "drawopenpath",
                "drawclosedpath",
                "drawcircle",
                "drawrect",
                "eraseshape",
            ],
            "toImageButtonOptions": {
                "format": "svg",
                "filename": f"{plot_name}_view",
                "height": config.get("height", 500),
                "width": config.get("width", 800),
                "scale": config.get("export_scale", 1),
            },
        }

        relayout_data: dict[str, Any] | None = interactive_plotly_chart(
            fig, config=plotly_config, key=f"chart_{plot_id}"
        )

        render_download_section(plot_id, plot_name, fig)

        return relayout_data

    # ── Matplotlib chart display ─────────────────────────────────

    @staticmethod
    def render_matplotlib_chart(
        plotly_fig: go.Figure,
        plot_id: int,
        plot_name: str,
        config: dict[str, Any],
        plot_type: str,
        traces: list[TraceConfig] | None = None,
    ) -> None:
        """
        Render a matplotlib chart derived from a Plotly figure.

        Pipeline:
            1. Build ``FigureConfig`` from plot config + Plotly layout.
            2. Use pre-computed ``TraceConfig`` list (from ``plot.last_traces``).
            3. Create blank matplotlib figure from spec dimensions.
            4. Render traces (no Plotly dependency).
            5. Apply spec-based styling (title, axes, grids, …).
            6. Display with ``st.pyplot()``.
            7. Store for potential download.

        Args:
            plotly_fig: Plotly ``go.Figure`` used for layout enrichment.
            plot_id: Plot identifier for widget keys.
            plot_name: Human-readable name for download filenames.
            config: Plot configuration dict.
            plot_type: Plot type key (e.g. ``"bar"``, ``"line"``).
            traces: Pre-computed engine-agnostic ``TraceConfig`` list.
                Eliminates reverse extraction from the Plotly figure.
        """
        # 1. Build and resolve FigureConfig
        spec = ConfigSpecBuilder.from_config(config, plot_type)
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
        spec = resolve_config(spec)

        # 2. Use pre-computed traces (forward direction)
        if traces is None:
            traces = []

        # 3. Create blank matplotlib figure
        mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)

        # 4. Render traces
        MatplotlibTraceRenderer.render(
            traces,
            ax,
            barmode=spec.barmode,
            palette_colors=spec.color_palette or None,
            bargap=spec.dimensions.bargap,
            bargroupgap=spec.dimensions.bargroupgap,
            bar_border_width=float(config.get("bar_border_width", 0.0)),
        )

        # 5. Apply spec-based styling
        FigureSpecToMatplotlib.apply(spec, ax)

        # 6. Display
        st.pyplot(mpl_fig)

        # 7. Store for download
        mpl_state_key = f"plot.{plot_id}.mpl_fig"
        st.session_state[mpl_state_key] = mpl_fig

        render_download_section(plot_id, plot_name, plotly_fig)

    # ── Error display ────────────────────────────────────────────

    @staticmethod
    def render_error(error: Exception) -> None:
        """
        Display an exception in the chart area.

        Args:
            error: The exception to render via ``st.exception()``.
        """
        st.exception(error)
