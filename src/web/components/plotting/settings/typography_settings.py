"""Typography settings component — font sizes and colors.

Extracted from ``BaseStyleUI._render_typography_section()`` as a standalone
component following the component-only architecture (P1, P9).

Tick marks, grid dash styles, tick label distance, Y-axis title position,
and group label settings live in ``AxesSettingsComponent`` where they
semantically belong.

Usage::

    component = TypographySettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(saved_config)
"""

import streamlit as st

from src.web.components.plotting.settings.widget_factory import (
    color_picker,
    numeric_input,
)
from src.web.models.plot_models import PlotConfig


class TypographySettingsComponent:
    """Render typography controls (font sizes and colors).

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

    def render(self, saved_config: PlotConfig, key_prefix: str = "theme_") -> PlotConfig:
        """Render typography section widgets.

        Note: Title text inputs (Main Title, X-label, Y-label) are in
        the plot config UI. This section only controls font sizes and
        colors.

        Parameters
        ----------
        saved_config : PlotConfig
            Current saved configuration.
        key_prefix : str
            Streamlit widget key prefix (default ``"theme_"``).

        Returns
        -------
        PlotConfig
            Configuration dict with typography keys.
        """
        # [impl->req~ring5.figure.typography~1]
        st.markdown("#### Typography (Font Sizes & Colors)")
        typo_c1, typo_c2 = st.columns(2)

        with typo_c1:
            st.markdown("**Title Font Sizes**")
            title_font_size = numeric_input(
                "Plot Title Font Size",
                saved_config,
                "title_font_size",
                self.plot_id,
                widget_key=f"{key_prefix}title_sz_{self.plot_id}",
                default=18,
                min_value=8,
                max_value=100,
            )

            xaxis_title_font_size = numeric_input(
                "X-Axis Title Font Size",
                saved_config,
                "xaxis_title_font_size",
                self.plot_id,
                widget_key=f"{key_prefix}xaxis_title_sz_{self.plot_id}",
                default=14,
                min_value=8,
                max_value=100,
            )

            yaxis_title_font_size = numeric_input(
                "Y-Axis Title Font Size",
                saved_config,
                "yaxis_title_font_size",
                self.plot_id,
                widget_key=f"{key_prefix}yaxis_title_sz_{self.plot_id}",
                default=14,
                min_value=8,
                max_value=100,
            )

        with typo_c2:
            st.markdown("**Tick Label Sizes & Colors**")
            xaxis_tickfont_size = numeric_input(
                "X-Axis Label (Tick) Size",
                saved_config,
                "xaxis_tickfont_size",
                self.plot_id,
                widget_key=f"{key_prefix}xaxis_tick_sz_{self.plot_id}",
                default=12,
                min_value=8,
                max_value=100,
                help="Overwrites the basic X-axis font size in Advanced Options",
            )
            xaxis_tickfont_color = color_picker(
                "X-Axis Label Color",
                saved_config,
                "xaxis_tickfont_color",
                self.plot_id,
                widget_key=f"{key_prefix}xaxis_tick_col_{self.plot_id}",
                default="#444444",
            )

            yaxis_tickfont_size = numeric_input(
                "Y-Axis Label (Tick) Size",
                saved_config,
                "yaxis_tickfont_size",
                self.plot_id,
                widget_key=f"{key_prefix}yaxis_tick_sz_{self.plot_id}",
                default=12,
                min_value=8,
                max_value=100,
            )
            yaxis_tickfont_color = color_picker(
                "Y-Axis Label Color",
                saved_config,
                "yaxis_tickfont_color",
                self.plot_id,
                widget_key=f"{key_prefix}yaxis_tick_col_{self.plot_id}",
                default="#444444",
            )

        return {
            "title_font_size": title_font_size,
            "xaxis_title_font_size": xaxis_title_font_size,
            "yaxis_title_font_size": yaxis_title_font_size,
            "xaxis_tickfont_size": xaxis_tickfont_size,
            "xaxis_tickfont_color": xaxis_tickfont_color,
            "yaxis_tickfont_size": yaxis_tickfont_size,
            "yaxis_tickfont_color": yaxis_tickfont_color,
        }
