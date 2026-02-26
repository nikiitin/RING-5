"""Chart display component — renders chart area controls, engine selector, and displays.

Provides:
    - Auto-refresh toggle and manual Refresh button
    - Engine selector (Plotly / Matplotlib)
    - Plotly interactive chart rendering with relayout feedback
    - Matplotlib chart rendering via FigureConfig pipeline
    - Download section wiring
    - Error display

All Streamlit rendering for the chart area is centralised here.
The controller orchestrates figure generation and delegates all
``st.*`` display calls to this component.
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


class ChartDisplayComponent:
    """
    Renders the interactive chart area: refresh controls, engine selector,
    chart display (Plotly or Matplotlib), and download section.

    All methods are ``@staticmethod`` — no instance state.
    """

    @staticmethod
    def render_refresh_controls(
        plot_id: int,
        auto_refresh: bool,
        config_changed: bool,
    ) -> dict[str, Any]:
        """Render auto-refresh toggle and manual Refresh button.

        Returns:
            Dict with auto_refresh, manual_refresh, should_generate.
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

    @staticmethod
    def render_engine_selector(
        plot_id: int,
        current_engine: str,
    ) -> str | None:
        """Render engine-selection pills (Plotly / Matplotlib)."""
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

    @staticmethod
    def render_plotly_chart(
        fig: go.Figure,
        plot_id: int,
        plot_name: str,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Render an interactive Plotly chart with relayout feedback."""
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

    @staticmethod
    def render_matplotlib_chart(
        plotly_fig: go.Figure,
        plot_id: int,
        plot_name: str,
        config: dict[str, Any],
        plot_type: str,
        traces: list[TraceConfig] | None = None,
    ) -> None:
        """Render a matplotlib chart derived from a Plotly figure."""
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

    @staticmethod
    def render_error(error: Exception) -> None:
        """Display an exception in the chart area."""
        st.exception(error)
