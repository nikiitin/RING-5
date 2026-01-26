"""Plot rendering utilities."""

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.plotting.export import ExportService
from src.web.ui.components.interactive_plot import interactive_plotly_chart

from .base_plot import BasePlot


class PlotRenderer:
    """Handles rendering plots and their UI elements."""

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
    def render_plot(plot: BasePlot, should_generate: bool = False) -> None:
        """
        Render the plot visualization.

        Args:
            plot: Plot instance
            should_generate: Whether to regenerate the figure
        """
        # 1. Generate Figure if needed (Forced OR Cache Missing)
        if (should_generate or plot.last_generated_fig is None) and plot.processed_data is not None:
            try:
                fig = plot.create_figure(plot.processed_data, plot.config)
                fig = plot.apply_common_layout(fig, plot.config)

                # Apply legend labels
                legend_labels = plot.config.get("legend_labels")
                if legend_labels:
                    fig = plot.apply_legend_labels(fig, legend_labels)

                # Store the figure
                plot.last_generated_fig = fig
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
                            # Cannot modify widget keys immediately because they were already rendered in this frame.
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
        Render download button for the plot.

        Args:
            plot: Plot instance
            fig: Plotly figure
        """
        ExportService.render_download_button(
            plot_name=plot.name,
            plot_id=plot.plot_id,
            fig=fig,
            config=plot.config,
            key_prefix="dl_btn",
        )
