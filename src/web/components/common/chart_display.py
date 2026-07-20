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

import logging
from typing import Any

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st

from src.core.models.visualization.trace_build_result import RuleLine, SeparatorLine, ShadedRegion
from src.core.models.visualization.trace_config import TraceConfig
from src.web.components.plotting.interactive_plot import interactive_plotly_chart
from src.web.pages.ui.plotting.download_section import render_download_section
from src.web.rendering.matplotlib_figure_builder import apply_dual_axis, build_matplotlib_figure

logger = logging.getLogger(__name__)


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
            key=f"engine_selector_{plot_id}",
        )
        return engine_choice

    @staticmethod
    def render_plotly_chart(
        fig: go.Figure,
        plot_id: int,
        plot_name: str,
        config: dict[str, Any],
        *,
        capture_click: bool = False,
        component_generation: int = 0,
    ) -> dict[str, Any] | None:
        # [impl->req~ring5.export.plotly-scale~1]
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
            fig,
            config=plotly_config,
            key=f"chart_{plot_id}_{component_generation}",
            capture_click=capture_click,
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
        separator_lines: list[SeparatorLine] | None = None,
        shaded_regions: list[ShadedRegion] | None = None,
        rule_lines: list[RuleLine] | None = None,
    ) -> None:
        """Render a matplotlib chart derived from a Plotly figure.

        The figure itself is built by the shared UI-free builder
        (``src.web.rendering.matplotlib_figure_builder``) — the same one the
        public ring5 package uses — so the app preview and a headless export
        of the same plot are the same figure. This method only adds the
        Streamlit display and the session cache the download section reads.
        """
        mpl_state_key = f"plot.{plot_id}.mpl_fig"
        spec_state_key = f"plot.{plot_id}.mpl_spec"

        # 0. Close previous matplotlib figure to prevent memory leak
        old_fig = st.session_state.get(mpl_state_key)
        if old_fig is not None:
            plt.close(old_fig)
            del st.session_state[mpl_state_key]
        st.session_state.pop(spec_state_key, None)

        # 1. Build the figure via the single shared render sequence
        mpl_fig, spec = build_matplotlib_figure(
            plotly_fig,
            config,
            plot_type,
            traces,
            separator_lines,
            shaded_regions,
            rule_lines,
        )

        try:
            # 2. Display
            st.pyplot(mpl_fig)

            # 3. Store for download (closed on next render or session end).
            # The spec rides along for format-specific export settings. PGF
            # deliberately ignores custom preambles at the security boundary.
            st.session_state[mpl_state_key] = mpl_fig
            st.session_state[spec_state_key] = spec

            render_download_section(plot_id, plot_name, plotly_fig)
        except Exception:
            plt.close(mpl_fig)
            raise

    @staticmethod
    def _apply_matplotlib_dual_axis(twin: Any, config: dict[str, Any], spec: Any) -> None:
        """Delegate to the shared builder's dual-axis fix-up (one canonical impl)."""
        apply_dual_axis(twin, config, spec)

    @staticmethod
    def render_error(error: Exception) -> None:
        """Display an exception in the chart area."""
        st.exception(error)
