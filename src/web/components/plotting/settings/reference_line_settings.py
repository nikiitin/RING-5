"""Reference line settings component — horizontal reference line controls.

Extracted from ``BasePlot._render_reference_line_ui``.
"""

import pandas as pd
import streamlit as st

from src.web.models.plot_models import PlotConfig


class ReferenceLineSettingsComponent:
    """Render UI controls for a horizontal reference line.

    Allows the user to toggle a red horizontal reference line and
    configure its Y position, color, width, and style.

    Parameters
    ----------
    plot_id : int
        Unique plot identifier for Streamlit widget keys.
    plot_type : str
        Plot type identifier.
    """

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None,
        config: PlotConfig,
    ) -> None:
        """Render reference line controls.

        Args:
            saved_config: Previously saved configuration.
            data: The data being plotted (needed for conditional display).
            config: Configuration dictionary to populate.
        """
        st.markdown("#### Reference Line")
        ref_enabled = st.checkbox(
            "Show reference line",
            value=saved_config.get("reference_line_enabled", False),
            key=f"ref_line_enabled_{self.plot_id}",
            help=(
                "Draw a horizontal dashed line at a specific Y value. "
                "Useful to highlight a baseline (e.g. Y=1 after "
                "normalization)."
            ),
        )
        config["reference_line_enabled"] = ref_enabled

        if ref_enabled and data is not None:
            with st.expander("Reference Line Settings", expanded=True):
                col3, col4, col5 = st.columns(3)
                with col3:
                    ref_y = st.number_input(
                        "Y position",
                        value=float(saved_config.get("reference_line_y", 1.0)),
                        step=0.1,
                        format="%.2f",
                        key=f"ref_line_y_{self.plot_id}",
                        help=("Y-axis value where the line is drawn " "(1.0 for normalized data)"),
                    )
                with col4:
                    ref_color = st.color_picker(
                        "Line color",
                        value=saved_config.get("reference_line_color", "#FF0000"),
                        key=f"ref_line_color_{self.plot_id}",
                    )
                with col5:
                    ref_width = st.slider(
                        "Line width",
                        min_value=0.5,
                        max_value=4.0,
                        value=float(saved_config.get("reference_line_width", 1.5)),
                        step=0.5,
                        key=f"ref_line_width_{self.plot_id}",
                    )

                ref_style = st.selectbox(
                    "Line style",
                    options=["dash", "dot", "dashdot", "solid"],
                    index=["dash", "dot", "dashdot", "solid"].index(
                        saved_config.get("reference_line_style", "dash")
                    ),
                    key=f"ref_line_style_{self.plot_id}",
                )

                config["reference_line_y"] = ref_y
                config["reference_line_color"] = ref_color
                config["reference_line_width"] = ref_width
                config["reference_line_style"] = ref_style


def render_reference_line_ui(
    plot_id: int,
    saved_config: PlotConfig,
    data: pd.DataFrame | None,
    config: PlotConfig,
) -> None:
    """Deprecated: use ReferenceLineSettingsComponent."""
    ReferenceLineSettingsComponent(plot_id, "").render(saved_config, data, config)
