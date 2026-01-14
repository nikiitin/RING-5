"""Plot rendering utilities."""

from typing import Any, Dict, Optional

import pandas as pd
import plotly.io as pio
import streamlit as st

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

                # Display the plot using custom interactive component
                # This enables capturing zoom/pan/drag events to sync with backend
                from src.web.ui.components.interactive_plot import (
                    interactive_plotly_chart,
                )

                # Reconstruct config for interactivity
                # We enforce editable=True (scoped) to allow legend dragging
                # but we can restrict other edits via 'edits' if needed in future
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
                            # We can't modify widget keys here because they were already rendered in this frame.
                            updates = {}
                            for prefix in ["", "theme_"]:
                                # Position Keys
                                x_key = f"{prefix}leg_x_sm_{plot.plot_id}"
                                y_key = f"{prefix}leg_y_sm_{plot.plot_id}"

                                # Anchor Keys (Critical for preventing jump/drift)
                                x_anc_key = f"{prefix}leg_xanc_{plot.plot_id}"
                                y_anc_key = f"{prefix}leg_yanc_{plot.plot_id}"

                                # We blindly stage updates; if the key doesn't exist next run, it's harmless
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
                # Fallback to standard chart if custom component fails?
                # For now, explicit error is better for debugging main loop

    @staticmethod
    def _render_download_button(plot: BasePlot, fig) -> None:
        """
        Render download button for the plot.

        Args:
            plot: Plot instance
            fig: Plotly figure
        """
        download_format = plot.config.get("download_format", "html")

        if download_format == "html":
            # Export as interactive HTML
            html_str = pio.to_html(fig, include_plotlyjs=True)
            st.download_button(
                label="Download Interactive HTML",
                data=html_str,
                file_name=f"{plot.name}.html",
                mime="text/html",
            )
        elif download_format in ["png", "pdf", "svg"]:
            try:
                try:
                    # High-fidelity export using kaleido if available
                    import io

                    import kaleido  # noqa: F401

                    buf = io.BytesIO()
                    # Scale based on user config (default 1 for WYSIWYG match)
                    scale = plot.config.get("export_scale", 1)
                    fig.write_image(buf, format=download_format, scale=scale)
                    buf.seek(0)

                    mime_map = {
                        "pdf": "application/pdf",
                        "png": "image/png",
                        "svg": "image/svg+xml",
                    }
                    mime = mime_map.get(download_format, "application/octet-stream")

                    st.download_button(
                        label=f"Download {download_format.upper()} (High Res)",
                        data=buf,
                        file_name=f"{plot.name}.{download_format}",
                        mime=mime,
                        key=f"dl_btn_{plot.plot_id}_{download_format}_hires",
                    )
                    return  # Success, skip fallback

                except Exception as e:
                    # Provide feedback on fallback but don't crash
                    if "kaleido" in str(e) or isinstance(e, ImportError):
                        print(f"Kaleido export failed, using fallback: {e}")
                    else:
                        st.warning(f"High-fidelity export failed ({e}), using fallback renderer.")

                # Fallback: Convert plotly figure to static image using matplotlib backend
                import io

                import matplotlib.pyplot as plt

                # Extract data from plotly figure
                width_inches = plot.config.get("width", 800) / 100
                height_inches = plot.config.get("height", 500) / 100

                mpl_fig = plt.figure(figsize=(width_inches, height_inches))
                ax = mpl_fig.add_subplot(111)

                # Extract data from plotly figure directly (avoid to_dict binary encoding)
                for trace in fig.data:
                    if trace.type in ["bar", "scatter"]:
                        x_data = trace.x
                        y_data = trace.y
                        label = trace.name or ""

                        if trace.type == "bar":
                            if x_data is not None:
                                ax.bar(range(len(x_data)), y_data, label=label, alpha=0.7)
                        else:  # scatter/line
                            ax.plot(x_data, y_data, label=label, marker="o")

                ax.set_title(plot.config.get("title", ""))
                ax.set_xlabel(plot.config.get("xlabel", ""))
                ax.set_ylabel(plot.config.get("ylabel", ""))
                if len(fig.data) > 1:
                    ax.legend()
                ax.grid(True, alpha=0.3)

                # Save to bytes
                buf = io.BytesIO()
                if download_format == "png":
                    mpl_fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
                    mime = "image/png"
                else:
                    mpl_fig.savefig(buf, format="pdf", bbox_inches="tight")
                    mime = "application/pdf"

                plt.close(mpl_fig)
                buf.seek(0)

                st.download_button(
                    label=f"Download {download_format.upper()}",
                    data=buf,
                    file_name=f"{plot.name}.{download_format}",
                    mime=mime,
                    key=f"dl_btn_{plot.plot_id}_{download_format}_fallback",
                )
            except Exception as e:
                st.error(f"Failed to generate {download_format.upper()}: {e}")
                st.exception(e)  # Show full traceback for debugging
                st.info("HTML download is always available as a fallback")
