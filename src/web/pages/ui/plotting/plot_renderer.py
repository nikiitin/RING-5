"""Plot rendering utilities with intelligent figure caching."""

import hashlib
import json
from typing import Any, Dict, Optional, cast

import pandas as pd
import streamlit as st

from src.core.performance import get_plot_cache, timed
from src.core.visualization.connectors.builders import (
    ConfigSpecBuilder,
    PlotlyFigureSpecBuilder,
)
from src.core.visualization.connectors.matplotlib_connector import (
    FigureSpecToMatplotlib,
)
from src.core.visualization.connectors.matplotlib_trace_renderer import (
    MatplotlibTraceRenderer,
)
from src.core.visualization.connectors.plotly_trace_extractor import (
    PlotlyTraceExtractor,
)
from src.core.visualization.resolvers import resolve_spec
from src.web.figures.engine import FigureEngine
from src.web.pages.ui.components.interactive_plot import interactive_plotly_chart
from src.web.pages.ui.plotting.download_section import render_download_section
from src.web.services.engine_manager import EngineManager, EngineMode

from .base_plot import BasePlot


class PlotRenderer:
    """Handles rendering plots and their UI elements with intelligent caching."""

    @staticmethod
    def _compute_figure_cache_key(plot_id: int, config: Dict[str, Any], data_hash: str) -> str:
        """
        Compute stable cache key for plot figure.

        Uses config hash + data hash to detect when regeneration is needed.
        Ignores transient UI state (legend positions, etc.).

        Args:
            plot_id: Unique plot identifier
            config: Plot configuration dict
            data_hash: Hash of the processed data

        Returns:
            Cache key string
        """
        # Filter out transient config that shouldn't invalidate cache
        cache_relevant_config = {
            k: v
            for k, v in config.items()
            if k
            not in {
                "xaxis_range",
                "yaxis_range",  # User zoom/pan state
            }
        }

        # Create stable JSON representation of config
        config_json = json.dumps(cache_relevant_config, sort_keys=True, default=str)
        config_hash = hashlib.md5(config_json.encode(), usedforsecurity=False).hexdigest()[:8]

        return f"plot_{plot_id}_{config_hash}_{data_hash}"

    @staticmethod
    def _compute_data_hash(data: pd.DataFrame) -> str:
        """
        Compute fast hash of DataFrame for cache invalidation.

        Uses shape + first/last row hashes for speed.

        Args:
            data: DataFrame to hash

        Returns:
            Hash string
        """
        # Fast fingerprint: shape + sample of data
        shape_str = f"{data.shape[0]}x{data.shape[1]}"

        # Hash first and last rows for change detection
        if len(data) > 0:
            first_row = str(data.iloc[0].values.tolist())
            last_row = str(data.iloc[-1].values.tolist())
            columns = str(data.columns.tolist())

            content = f"{shape_str}|{columns}|{first_row}|{last_row}"
        else:
            content = shape_str

        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]

    @staticmethod
    def render_legend_customization(
        plot: BasePlot, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """
        Render legend customization UI.

        Args:
            plot: Plot instance
            data: The data being plotted
            config: Current plot configuration

        Returns:
            Dictionary mapping original values to custom labels, or None
        """
        legend_col = plot.get_legend_column(config)

        if not legend_col:
            return None

        unique_vals = data[legend_col].unique().tolist()

        st.markdown("**Custom Legend Labels**")
        st.caption("Customize the legend labels for each value (leave blank to keep original)")

        # Initialize per-column legend mappings storage if not exists
        if not plot.legend_mappings_by_column:
            plot.legend_mappings_by_column = {}

        # Get existing mappings for this column
        existing_mappings = plot.legend_mappings_by_column.get(legend_col, {})
        legend_labels = {}

        # Create input fields for each unique value
        for val in unique_vals:
            default_value = existing_mappings.get(str(val), str(val))
            custom_label = st.text_input(
                f"Label for '{val}'",
                value=default_value,
                key=f"legend_label_{plot.plot_id}_{legend_col}_{val}",
                label_visibility="visible",
            )
            # Only add to mapping if user provided a value
            if custom_label and custom_label.strip():
                legend_labels[str(val)] = custom_label.strip()
            else:
                legend_labels[str(val)] = str(val)

        # Store mappings for THIS column specifically
        plot.legend_mappings_by_column[legend_col] = legend_labels

        # Also update the global legend_mappings for backward compatibility
        plot.legend_mappings = legend_labels

        return legend_labels

    @staticmethod
    @timed
    def render_plot(plot: BasePlot, should_generate: bool = False) -> None:
        """
        Render the plot visualization with intelligent figure caching.

        Performance: Uses config+data hash to cache generated figures.
        Only regenerates when config or data actually changes.

        Args:
            plot: Plot instance
            should_generate: Whether to force regeneration (bypasses cache)
        """
        if plot.processed_data is None:
            return

        # Compute cache key from config + data fingerprint
        data_hash = PlotRenderer._compute_data_hash(plot.processed_data)
        cache_key = PlotRenderer._compute_figure_cache_key(plot.plot_id, plot.config, data_hash)

        # Try cache first (unless forced regeneration)
        cache = get_plot_cache()
        if not should_generate and plot.last_generated_fig is None:
            cached_fig = cache.get(cache_key)
            if cached_fig is not None:
                plot.last_generated_fig = cached_fig

        # 1. Generate Figure if needed (Forced OR Cache Missing)
        if should_generate or plot.last_generated_fig is None:
            try:
                # Route through FigureEngine — single entry point for
                # creation + styling + legend labels.
                engine = FigureEngine.from_plot(
                    plot,
                    plot.plot_type,
                    styler=plot.style_manager.applicator,
                )
                fig = engine.build(plot.plot_type, plot.processed_data, plot.config)

                # Store and cache the figure
                plot.last_generated_fig = fig
                cache.set(cache_key, fig)
            except Exception as e:
                st.exception(e)
                return

        # 2. Render if we have a figure
        if plot.last_generated_fig is not None:
            try:
                fig = plot.last_generated_fig

                # ── Engine selector ──────────────────────────────────
                engine_choice = st.pills(
                    "Engine",
                    options=["plotly", "matplotlib"],
                    format_func=lambda x: (
                        ":material/interactive_space: Plotly"
                        if x == "plotly"
                        else ":material/description: LaTeX (Matplotlib)"
                    ),
                    selection_mode="single",
                    default=EngineManager.get_engine(),
                    key=f"engine_selector_{plot.plot_id}",
                )
                if engine_choice is not None:
                    EngineManager.set_engine(cast("EngineMode", engine_choice))

                # ── Branch on engine mode ────────────────────────────
                if EngineManager.is_matplotlib():
                    PlotRenderer._render_matplotlib(plot, fig)
                else:
                    PlotRenderer._render_plotly(plot, fig)

            except Exception as e:
                st.exception(e)
                # Explicit error is better for debugging main loop

    @staticmethod
    def _render_plotly(plot: BasePlot, fig: Any) -> None:
        """Render using Plotly interactive chart with relayout feedback."""
        plotly_config = {
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
                "filename": f"{plot.name}_view",
                "height": plot.config.get("height", 500),
                "width": plot.config.get("width", 800),
                "scale": plot.config.get("export_scale", 1),
            },
        }

        relayout_data = interactive_plotly_chart(
            fig, config=plotly_config, key=f"chart_{plot.plot_id}"
        )

        if relayout_data:
            last_event_key = f"plot.{plot.plot_id}.last_relayout"
            last_event = st.session_state.get(last_event_key)
            if relayout_data != last_event:
                if plot.update_from_relayout(relayout_data):
                    st.session_state[last_event_key] = relayout_data
                    st.rerun()

        render_download_section(plot.plot_id, plot.name, fig)

    @staticmethod
    def _render_matplotlib(plot: BasePlot, fig: Any) -> None:
        """Render using Matplotlib via FigureSpec pipeline.

        Steps:
          1. Build FigureSpec from the plot config + Plotly layout.
          2. Extract engine-agnostic TraceSpec from Plotly figure.
          3. Create a blank matplotlib figure from spec dimensions.
          4. Render traces from TraceSpec (no Plotly dependency).
          5. Apply spec-based styling (title, axes, grids, etc.).
          6. Display with ``st.pyplot()``.
        """
        plotly_fig = fig

        # 1. Build and resolve the FigureSpec
        spec = ConfigSpecBuilder.from_config(plot.config, plot.plot_type)
        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
        spec = resolve_spec(spec)

        # 2. Extract engine-agnostic TraceSpec from Plotly figure
        traces = PlotlyTraceExtractor.extract(plotly_fig)

        # 3. Create blank matplotlib figure
        mpl_fig, ax = FigureSpecToMatplotlib.create_figure(spec)

        # 4. Render traces from TraceSpec (no Plotly dependency)
        MatplotlibTraceRenderer.render(
            traces,
            ax,
            barmode=spec.barmode,
            palette_colors=spec.color_palette or None,
        )

        # 5. Apply spec-based styling
        FigureSpecToMatplotlib.apply(spec, ax)

        # 6. Render
        st.pyplot(mpl_fig)

        # Store for potential download
        mpl_state_key = f"plot.{plot.plot_id}.mpl_fig"
        st.session_state[mpl_state_key] = mpl_fig

        render_download_section(plot.plot_id, plot.name, fig)
