"""Plot rendering utilities with intelligent figure caching."""

import hashlib
import json
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.core.performance import get_plot_cache, timed
from src.plotting.export import LaTeXExportService
from src.web.ui.components.interactive_plot import interactive_plotly_chart

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
                "legend_x",
                "legend_y",
                "legend_xanchor",
                "legend_yanchor",
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
                fig = plot.create_figure(plot.processed_data, plot.config)
                fig = plot.apply_common_layout(fig, plot.config)

                # Apply legend labels
                legend_labels = plot.config.get("legend_labels")
                if legend_labels:
                    fig = plot.apply_legend_labels(fig, legend_labels)

                # Store and cache the figure
                plot.last_generated_fig = fig
                cache.set(cache_key, fig)
            except Exception as e:
                st.error(f"Error generating plot: {e}")
                return

        # 2. Render if we have a figure
        if plot.last_generated_fig is not None:
            try:
                fig = plot.last_generated_fig

                # Reconstruct config for interactivity
                # Enforce editable=True (scoped) to allow legend dragging
                # but restrict other edits via 'edits' if needed in future
                plotly_config = {
                    "responsive": False,
                    "editable": True,  # Required for legend dragging
                    "edits": {
                        "legendPosition": True,
                        "titleText": False,
                        "axisTitleText": False,
                        "annotationText": False,
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

                # Update backend config if user interacted
                if relayout_data:
                    # Prevent infinite loops by checking if we already processed this exact event
                    last_event_key = f"last_relayout_{plot.plot_id}"
                    last_event = st.session_state.get(last_event_key)

                    if relayout_data != last_event:
                        if plot.update_from_relayout(relayout_data):
                            # Store updates for the next run to avoid "widget instantiated" errors
                            # Cannot modify widget keys immediately because they were already rendered in this frame.  # noqa: E501
                            updates = {}
                            for prefix in ["", "theme_"]:
                                # Position Keys
                                x_key = f"{prefix}leg_x_sm_{plot.plot_id}"
                                y_key = f"{prefix}leg_y_sm_{plot.plot_id}"

                                # Anchor Keys (Critical for preventing jump/drift)
                                x_anc_key = f"{prefix}leg_xanc_{plot.plot_id}"
                                y_anc_key = f"{prefix}leg_yanc_{plot.plot_id}"

                                # Stage updates; missing keys are ignored by session state
                                if "legend_x" in plot.config:
                                    updates[x_key] = plot.config["legend_x"]
                                if "legend_y" in plot.config:
                                    updates[y_key] = plot.config["legend_y"]

                                # Sync Anchors if they changed
                                if "legend_xanchor" in plot.config:
                                    updates[x_anc_key] = plot.config["legend_xanchor"]
                                if "legend_yanchor" in plot.config:
                                    updates[y_anc_key] = plot.config["legend_yanchor"]

                            if updates:
                                st.session_state["pending_plot_updates"] = updates

                            st.session_state[last_event_key] = relayout_data
                            st.rerun()

                # Download button
                PlotRenderer._render_download_button(plot, fig)

            except Exception as e:
                st.error(f"Error generating plot: {e}")
                # Explicit error is better for debugging main loop

    @staticmethod
    def _render_download_button(plot: BasePlot, fig: Any) -> None:
        """
        Render export dialog for publication-quality LaTeX export.

        Provides dropdown selection for journal presets and format,
        then generates downloadable file using MatplotlibConverter.

        Args:
            plot: Plot instance
            fig: Plotly figure with user's interactive adjustments
        """
        with st.expander("📥 Export for LaTeX", expanded=False):
            st.markdown("**Publication-Quality Export**")
            st.caption(
                "Export to LaTeX-optimized formats. "
                "Preserves your legend positions, zoom, and layout adjustments."
            )

            # Initialize service
            service = LaTeXExportService()
            presets = service.list_presets()

            # UI for export settings
            col1, col2 = st.columns(2)

            with col1:
                preset_name = st.selectbox(
                    "Journal Preset",
                    options=presets,
                    index=0,  # Default to first preset
                    help="Select journal/conference column width preset",
                )

            with col2:
                format_choice = st.selectbox(
                    "Export Format",
                    options=["pdf", "pgf", "eps"],
                    index=0,  # Default to PDF
                    help=(
                        "• PDF: Recommended for most use cases\n"
                        "• PGF: Best for direct LaTeX inclusion\n"
                        "• EPS: Legacy format"
                    ),
                )

            # Export button
            if st.button("Generate Export", use_container_width=True):
                with st.spinner(f"Generating {format_choice.upper()}..."):
                    # Call service
                    result = service.export(fig, preset=preset_name, format=format_choice)

                    if result["success"] and result["data"] is not None:
                        # Success - provide download
                        file_extension = result["format"]
                        file_name = f"figure.{file_extension}"

                        st.download_button(
                            label=f"Download {file_extension.upper()}",
                            data=result["data"],  # Now guaranteed non-None
                            file_name=file_name,
                            mime=_get_mime_type(file_extension),
                            use_container_width=True,
                        )

                        st.success(f"✓ Export successful " f"({len(result['data']) / 1024:.1f} KB)")
                    else:
                        # Error - show message
                        error_msg = result.get("error", "Unknown error")
                        st.error(f"Export failed: {error_msg}")
                        st.info(
                            "Tip: Ensure LaTeX is installed on your system " "for PGF/EPS formats."
                        )


def _get_mime_type(file_extension: str) -> str:
    """Get MIME type for file extension."""
    mime_types = {
        "pdf": "application/pdf",
        "pgf": "application/x-tex",
        "eps": "application/postscript",
    }
    return mime_types.get(file_extension, "application/octet-stream")
