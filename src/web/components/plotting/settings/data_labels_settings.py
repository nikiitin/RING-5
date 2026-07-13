"""Data labels settings component — bar value labels and thresholds.

Extracted from ``BaseStyleUI.render_data_labels_ui()`` as a standalone
component following the component-only architecture (P1, P9).

Usage::

    component = DataLabelsSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(saved_config)
"""

import streamlit as st

from src.web.components.plotting.settings.widget_factory import (
    color_picker,
    numeric_input,
    select_option,
    slider,
    toggle,
)
from src.web.models.plot_models import PlotConfig


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
        saved_config: PlotConfig,
        key_prefix: str = "theme_",
    ) -> PlotConfig:
        """Render data labels section.

        Parameters
        ----------
        saved_config : PlotConfig
            Current saved configuration.
        key_prefix : str
            Streamlit widget key prefix (default ``"theme_"``).

        Returns
        -------
        PlotConfig
            Configuration dict with data label keys.
        """
        st.markdown("#### Data Labels")

        is_heatmap = self.plot_type == "heatmap"

        # Heatmap defaults: show_values=True, contrast mode, .4g format
        default_color_mode = saved_config.get(
            "text_color_mode", "contrast" if is_heatmap else "auto"
        )
        default_format = saved_config.get("text_format", ".4g" if is_heatmap else ".2f")

        show_values = toggle(
            "Show Values",
            saved_config,
            "show_values",
            self.plot_id,
            widget_key=f"{key_prefix}show_val_{self.plot_id}",
            default=True if is_heatmap else False,
        )

        # Progressive disclosure: only show formatting controls
        # when "Show Values" is enabled.
        if not show_values:
            return {
                "show_values": False,
                "text_color_mode": default_color_mode,
                "text_color": saved_config.get("text_color", "#000000"),
                "text_font_size": saved_config.get("text_font_size", 10),
                "text_rotation": saved_config.get("text_rotation", 0),
                "text_position": saved_config.get("text_position", "auto"),
                "text_anchor": saved_config.get("text_anchor", "auto"),
                "text_format": default_format,
                "text_display_logic": saved_config.get("text_display_logic", "all"),
                "text_threshold": float(saved_config.get("text_threshold", 0.0)),
                "text_constraint": saved_config.get("text_constraint", "none"),
            }

        text_color_mode = select_option(
            "Value Color Mode",
            ["auto", "contrast", "custom"],
            saved_config,
            "text_color_mode",
            self.plot_id,
            widget_key=f"{key_prefix}tx_col_mode_{self.plot_id}",
            default="contrast" if is_heatmap else "auto",
            help=(
                "Auto: uses theme default. Contrast:"
                " white on dark, black on light."
                " Custom: fixed color."
            ),
        )

        text_color = "#000000"
        if text_color_mode == "custom":
            text_color = color_picker(
                "Value Color",
                saved_config,
                "text_color",
                self.plot_id,
                widget_key=f"{key_prefix}tx_col_{self.plot_id}",
            )

        text_font_size = numeric_input(
            "Value Font Size",
            saved_config,
            "text_font_size",
            self.plot_id,
            widget_key=f"{key_prefix}tx_font_sz_{self.plot_id}",
            default=10,
            min_value=6,
            max_value=40,
        )

        text_rotation: int | float = 0
        if not is_heatmap:
            text_rotation = slider(
                "Value Rotation",
                saved_config,
                "text_rotation",
                self.plot_id,
                widget_key=f"{key_prefix}tx_rot_{self.plot_id}",
                default=0,
                min_value=-90,
                max_value=90,
                step=15,
            )

        text_position = "auto"
        text_anchor = "auto"
        if not is_heatmap:
            text_position = select_option(
                "Value Position",
                ["auto", "inside", "outside"],
                saved_config,
                "text_position",
                self.plot_id,
                widget_key=f"{key_prefix}tx_pos_{self.plot_id}",
            )

            text_anchor = select_option(
                "Value Anchor",
                ["auto", "top", "middle", "bottom"],
                saved_config,
                "text_anchor",
                self.plot_id,
                widget_key=f"{key_prefix}tx_anc_{self.plot_id}",
            )

        text_format = st.text_input(
            "Value Number Format (d3-format)",
            value=default_format,
            key=f"{key_prefix}tx_fmt_{self.plot_id}",
            help=("e.g. .2f for 2 decimals, .4g for significant" " digits, .1% for percentage."),
        )

        st.caption("Display Thresholds")
        text_display_logic = select_option(
            "Display Logic",
            ["all", "above_threshold", "below_threshold"],
            saved_config,
            "text_display_logic",
            self.plot_id,
            widget_key=f"{key_prefix}tx_logic_{self.plot_id}",
        )

        text_threshold = 0.0
        if text_display_logic != "all":
            text_threshold = numeric_input(
                "Threshold Value",
                saved_config,
                "text_threshold",
                self.plot_id,
                widget_key=f"{key_prefix}tx_thresh_{self.plot_id}",
                default=0.0,
            )

        text_constraint = "none"
        if not is_heatmap:
            text_constraint = select_option(
                "Size Constraint",
                ["none", "inside"],
                saved_config,
                "text_constraint",
                self.plot_id,
                widget_key=f"{key_prefix}tx_const_{self.plot_id}",
                help="If inside, text will be resized or hidden to fit within the bars.",
            )

        # Heatmap Totals (heatmap only)
        show_totals: bool = False
        totals_position: str = "right"
        totals_aggregation: str = "mean"

        if is_heatmap:
            st.markdown("---")
            st.markdown("**Totals**")
            tot_c1, tot_c2, tot_c3 = st.columns(3)
            with tot_c1:
                show_totals = toggle(
                    "Show Totals",
                    saved_config,
                    "show_totals",
                    self.plot_id,
                    widget_key=f"{key_prefix}hm_show_totals_{self.plot_id}",
                    help="Append a summary row or column to the heatmap.",
                )
            if show_totals:
                with tot_c2:
                    totals_position = select_option(
                        "Position",
                        ["right", "top"],
                        saved_config,
                        "totals_position",
                        self.plot_id,
                        widget_key=f"{key_prefix}hm_totals_pos_{self.plot_id}",
                        default="right",
                        help="Right: extra column. Top: extra row.",
                    )
                with tot_c3:
                    totals_aggregation = select_option(
                        "Totals Aggregation",
                        ["mean", "sum", "max", "min"],
                        saved_config,
                        "totals_aggregation",
                        self.plot_id,
                        widget_key=f"{key_prefix}hm_totals_agg_{self.plot_id}",
                        default="mean",
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
            "show_totals": show_totals,
            "totals_position": totals_position,
            "totals_aggregation": totals_aggregation,
        }
