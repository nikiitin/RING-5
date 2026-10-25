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

from src.web.state.ui_state_manager import WidgetKeyBuilder

from matplotlib.figure import Figure as MplFigure
from src.web.models.render_artifact import RenderArtifact
from src.web.components.plotting.interactive_plot import interactive_plotly_chart
from src.web.pages.ui.plotting.download_section import render_download_section


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
        # [impl->req~ring5.plots.refresh-cache~1]
        r1, r2 = st.columns([1, 3])
        with r1:
            new_auto: bool = st.toggle(
                "Auto-refresh",
                value=auto_refresh,
                key=WidgetKeyBuilder.plot_key(plot_id, "widgets.auto_refresh"),
            )
        with r2:
            manual: bool = st.button(
                "Refresh Plot",
                key=WidgetKeyBuilder.plot_key(plot_id, "widgets.refresh"),
                width="stretch",
            )

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
        # [impl->req~ring5.render.engine-selection~1]
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
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.engine_selector"),
        )
        return engine_choice

    @staticmethod
    def render_plotly_chart(
        artifact: RenderArtifact,
        plot_id: int,
        plot_name: str,
        *,
        capture_click: bool = False,
        component_generation: int = 0,
    ) -> dict[str, Any] | None:
        # [impl->req~ring5.export.plotly-scale~1]
        """Display the exact Plotly artifact and its matching export inputs."""
        fig, config = artifact.figure, artifact.config
        if not isinstance(fig, go.Figure):
            raise TypeError("Plotly display requires its published Plotly artifact.")
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
            fig,
            config=plotly_config,
            key=WidgetKeyBuilder.plot_key(plot_id, f"widgets.chart_{component_generation}"),
            capture_click=capture_click,
        )

        render_download_section(plot_id, plot_name, artifact)

        return relayout_data

    @staticmethod
    def render_matplotlib_chart(artifact: RenderArtifact, plot_id: int, plot_name: str) -> None:
        """Display an already-built native artifact without rebuilding or caching it."""
        if not isinstance(artifact.figure, MplFigure):
            raise TypeError("Matplotlib display requires its published native artifact.")
        st.pyplot(artifact.figure)
        render_download_section(plot_id, plot_name, artifact)

    @staticmethod
    def render_error(error: Exception) -> None:
        """Display an exception in the chart area."""
        st.exception(error)
