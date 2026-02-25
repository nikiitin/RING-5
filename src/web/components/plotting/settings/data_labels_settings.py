"""Data labels settings component — bar value labels and thresholds.

Extracted from ``BaseStyleUI.render_data_labels_ui()`` as a standalone
component following the component-only architecture (P1, P9).

Usage::

    component = DataLabelsSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(saved_config)
"""

from typing import Any

import streamlit as st


class DataLabelsSettingsComponent:
    """Render data label configuration widgets.

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
        saved_config: dict[str, Any],
        key_prefix: str = "theme_",
    ) -> dict[str, Any]:
        """Render data labels section.

        Parameters
        ----------
        saved_config : dict[str, Any]
            Current saved configuration.
        key_prefix : str
            Streamlit widget key prefix (default ``"theme_"``).

        Returns
        -------
        dict[str, Any]
            Configuration dict with data label keys.
        """
        st.markdown("#### Data Labels")

        show_values = st.checkbox(
            "Show Values",
            value=saved_config.get("show_values", False),
            key=f"{key_prefix}show_val_{self.plot_id}",
        )

        text_color_mode = st.selectbox(
            "Value Color Mode",
            options=["auto", "contrast", "custom"],
            index=(
                ["auto", "contrast", "custom"].index(saved_config.get("text_color_mode", "auto"))
                if saved_config.get("text_color_mode", "auto") in ["auto", "contrast", "custom"]
                else 0
            ),
            key=f"{key_prefix}tx_col_mode_{self.plot_id}",
            help=(
                "Auto: uses theme default. Contrast:"
                " white on dark, black on light."
                " Custom: fixed color."
            ),
        )

        text_color = "#000000"
        if text_color_mode == "custom":
            text_color = st.color_picker(
                "Value Color",
                saved_config.get("text_color", "#000000"),
                key=f"{key_prefix}tx_col_{self.plot_id}",
            )

        text_font_size = st.number_input(
            "Value Font Size",
            min_value=6,
            max_value=40,
            value=saved_config.get("text_font_size", 10),
            key=f"{key_prefix}tx_font_sz_{self.plot_id}",
        )

        text_rotation = st.slider(
            "Value Rotation",
            -90,
            90,
            saved_config.get("text_rotation", 0),
            15,
            key=f"{key_prefix}tx_rot_{self.plot_id}",
        )

        text_position = st.selectbox(
            "Value Position",
            options=["auto", "inside", "outside"],
            index=(
                ["auto", "inside", "outside"].index(saved_config.get("text_position", "auto"))
                if saved_config.get("text_position", "auto") in ["auto", "inside", "outside"]
                else 0
            ),
            key=f"{key_prefix}tx_pos_{self.plot_id}",
        )

        text_anchor = st.selectbox(
            "Value Anchor",
            options=["auto", "top", "middle", "bottom"],
            index=(
                ["auto", "top", "middle", "bottom"].index(saved_config.get("text_anchor", "auto"))
                if saved_config.get("text_anchor", "auto") in ["auto", "top", "middle", "bottom"]
                else 0
            ),
            key=f"{key_prefix}tx_anc_{self.plot_id}",
        )

        text_format = st.text_input(
            "Value Number Format (d3-format)",
            value=saved_config.get("text_format", ".2f"),
            key=f"{key_prefix}tx_fmt_{self.plot_id}",
            help=("e.g. .2f for 2 decimals, .2s for scientific" " suffix, .1% for percentage."),
        )

        st.caption("Display Thresholds")
        text_display_logic = st.selectbox(
            "Display Logic",
            options=["all", "above_threshold", "below_threshold"],
            index=(
                ["all", "above_threshold", "below_threshold"].index(
                    saved_config.get("text_display_logic", "all")
                )
                if saved_config.get("text_display_logic", "all")
                in ["all", "above_threshold", "below_threshold"]
                else 0
            ),
            key=f"{key_prefix}tx_logic_{self.plot_id}",
        )

        text_threshold = 0.0
        if text_display_logic != "all":
            text_threshold = st.number_input(
                "Threshold Value",
                value=float(saved_config.get("text_threshold", 0.0)),
                key=f"{key_prefix}tx_thresh_{self.plot_id}",
            )

        text_constraint = st.selectbox(
            "Size Constraint",
            options=["none", "inside"],
            index=(
                ["none", "inside"].index(saved_config.get("text_constraint", "none"))
                if saved_config.get("text_constraint", "none") in ["none", "inside"]
                else 0
            ),
            key=f"{key_prefix}tx_const_{self.plot_id}",
            help=("If inside, text will be resized or hidden" " to fit within the bars."),
        )

        return {
            "show_values": show_values,
            "text_color_mode": text_color_mode,
            "text_color": text_color,
            "text_font_size": text_font_size,
            "text_rotation": text_rotation,
            "text_position": text_position,
            "text_anchor": text_anchor,
            "text_format": text_format,
            "text_display_logic": text_display_logic,
            "text_threshold": text_threshold,
            "text_constraint": text_constraint,
        }
