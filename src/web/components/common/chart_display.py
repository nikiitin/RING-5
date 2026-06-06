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

from src.core.models.visualization.trace_build_result import SeparatorLine, ShadedRegion
from src.core.models.visualization.trace_config import HeatmapTraceConfig, TraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.components.plotting.interactive_plot import interactive_plotly_chart
from src.web.pages.ui.plotting.download_section import render_download_section
from src.web.rendering._heatmap_utils import compute_nice_range, compute_z_extent
from src.web.rendering._render_result import MatplotlibRenderResult
from src.web.rendering.config_builder import ConfigSpecBuilder, PlotlyFigureSpecBuilder
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer

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
        separator_lines: list[SeparatorLine] | None = None,
        shaded_regions: list[ShadedRegion] | None = None,
    ) -> None:
        """Render a matplotlib chart derived from a Plotly figure."""
        mpl_state_key = f"plot.{plot_id}.mpl_fig"

        # 0. Close previous matplotlib figure to prevent memory leak
        old_fig = st.session_state.get(mpl_state_key)
        if old_fig is not None:
            plt.close(old_fig)
            del st.session_state[mpl_state_key]

        # 1. Build and resolve FigureConfig
        spec = ConfigSpecBuilder.from_config(config, plot_type)
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
        spec = resolve_config(spec)

        # 2. Use pre-computed traces (forward direction)
        if traces is None:
            traces = []

        # 2a. Detect multi-heatmap and delegate to specialised renderer
        heatmap_traces = [t for t in traces if isinstance(t, HeatmapTraceConfig)]
        if len(heatmap_traces) > 1:
            ChartDisplayComponent._render_multi_heatmap(
                plotly_fig,
                plot_id,
                plot_name,
                config,
                plot_type,
                traces,
                heatmap_traces,
                spec,
            )
            return

        # 3. Create blank matplotlib figure
        mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)

        try:
            # 4. Render traces
            render_result = MatplotlibTraceRenderer.render(
                traces,
                ax,
                barmode=spec.barmode,
                palette_colors=spec.color_palette or None,
                bargap=spec.dimensions.bargap,
                bargroupgap=spec.dimensions.bargroupgap,
                bar_border_width=float(config.get("bar_border_width", 0.0)),
            )

            # 5. Apply spec-based styling
            FigureSpecToMatplotlib.apply(spec, ax, render_result)

            # 5b. Draw engine-agnostic bar-group separators / shading bands so
            # they match the Plotly figure (dual-engine parity).
            FigureSpecToMatplotlib.draw_layout_shapes(
                ax, separator_lines or [], shaded_regions or []
            )

            # 5c. Dual-axis parity: matplotlib already renders right-axis traces
            # on a twin axis (ax._ring5_twin); give it the secondary Y-title and a
            # legend for the right-axis series, mirroring what Plotly does via
            # apply_dual_axis_titles / apply_separate_legends. (Plotly rendering is
            # left unchanged — this only fills the matplotlib gap.)
            twin = getattr(ax, "_ring5_twin", None)
            if twin is not None:
                ChartDisplayComponent._apply_matplotlib_dual_axis(twin, config, spec)

            # 6. Display
            st.pyplot(mpl_fig)

            # 7. Store for download (closed on next render or session end)
            st.session_state[mpl_state_key] = mpl_fig

            render_download_section(plot_id, plot_name, plotly_fig)
        except Exception:
            plt.close(mpl_fig)
            raise

    @staticmethod
    def _apply_matplotlib_dual_axis(twin: Any, config: dict[str, Any], spec: Any) -> None:
        """Give the matplotlib twin (right) axis its Y-title and a legend.

        matplotlib already renders right-axis traces on the twin; this fills the
        remaining gap so dual-axis charts match Plotly (secondary title +
        right-axis series in a legend). Plotly rendering is unchanged.
        """
        typo = spec.typography

        ylabel_right = config.get("ylabel_right")
        if ylabel_right:
            label_kwargs: dict[str, Any] = {}
            if typo is not None and typo.font_size_y2label > 0:
                label_kwargs["fontsize"] = typo.font_size_y2label
            if typo is not None and typo.bold_y2label:
                label_kwargs["fontweight"] = "bold"
            twin.set_ylabel(str(ylabel_right), **label_kwargs)

        # A legend for the right-axis (twin) series — matplotlib's primary
        # legend on the base axes only sees the left-axis handles.
        handles, labels = twin.get_legend_handles_labels()
        if handles:
            legend_kwargs: dict[str, Any] = {"loc": "upper right", "framealpha": 0.85}
            if typo is not None and typo.font_size_legend2 > 0:
                legend_kwargs["fontsize"] = typo.font_size_legend2
            twin.legend(handles, labels, **legend_kwargs)

    @staticmethod
    def render_error(error: Exception) -> None:
        """Display an exception in the chart area."""
        st.exception(error)

    @staticmethod
    def _render_multi_heatmap(
        plotly_fig: go.Figure,
        plot_id: int,
        plot_name: str,
        config: dict[str, Any],
        plot_type: str,
        all_traces: list[TraceConfig],
        heatmap_traces: list[HeatmapTraceConfig],
        spec: Any,
    ) -> None:
        """Render multiple heatmap traces as separate matplotlib subplots.

        Each heatmap gets its own axes row.  Colorbars are handled by
        ``FigureSpecToMatplotlib.apply_multi_heatmap_colorbars()``.
        """
        mpl_state_key = f"plot.{plot_id}.mpl_fig"

        old_fig = st.session_state.get(mpl_state_key)
        if old_fig is not None:
            plt.close(old_fig)
            del st.session_state[mpl_state_key]

        n = len(heatmap_traces)
        mpl_fig, axes_list = FigureSpecToMatplotlib.create_multi_figure(spec, n)

        # Compute shared vmin/vmax from ColorbarConfig
        cbar_cfg = spec.legends[0].colorbar if spec.legends else None
        if (
            cbar_cfg
            and cbar_cfg.range_mode == "manual"
            and cbar_cfg.zmin is not None
            and cbar_cfg.zmax is not None
        ):
            vmin, vmax = float(cbar_cfg.zmin), float(cbar_cfg.zmax)
        else:
            raw_min, raw_max = compute_z_extent(heatmap_traces)
            nticks = cbar_cfg.nticks if cbar_cfg else 5
            vmin, vmax, _ = compute_nice_range(raw_min, raw_max, nticks)

        shared = cbar_cfg.shared if cbar_cfg else True

        try:
            render_results: list[MatplotlibRenderResult] = []
            for i, trace in enumerate(heatmap_traces):
                ax = axes_list[i]
                # Per-trace range when not shared
                if shared:
                    t_vmin, t_vmax = vmin, vmax
                else:
                    t_min, t_max = compute_z_extent([trace])
                    nticks = cbar_cfg.nticks if cbar_cfg else 5
                    t_vmin, t_vmax, _ = compute_nice_range(t_min, t_max, nticks)

                rr = MatplotlibTraceRenderer.render(
                    [trace],
                    ax,
                    heatmap_vmin=t_vmin,
                    heatmap_vmax=t_vmax,
                )
                render_results.append(rr)

                # Apply styling per-axes (skip colorbar — handled below)
                FigureSpecToMatplotlib.apply(spec, ax, render_result=None)
                ax.set_title(trace.name)

            # Apply colorbars
            FigureSpecToMatplotlib.apply_multi_heatmap_colorbars(
                spec,
                mpl_fig,
                axes_list,
                render_results,
            )

            st.pyplot(mpl_fig)
            st.session_state[mpl_state_key] = mpl_fig
            render_download_section(plot_id, plot_name, plotly_fig)
        except Exception:
            plt.close(mpl_fig)
            raise
