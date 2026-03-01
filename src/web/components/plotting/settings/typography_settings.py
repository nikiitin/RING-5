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
        st.markdown("#### Typography (Font Sizes & Colors)")
        typo_c1, typo_c2 = st.columns(2)

        with typo_c1:
            st.markdown("**Title Font Sizes**")
            title_font_size = st.number_input(
                "Plot Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("title_font_size", 18),
                key=f"{key_prefix}title_sz_{self.plot_id}",
            )

            xaxis_title_font_size = st.number_input(
                "X-Axis Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("xaxis_title_font_size", 14),
                key=f"{key_prefix}xaxis_title_sz_{self.plot_id}",
            )

            yaxis_title_font_size = st.number_input(
                "Y-Axis Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("yaxis_title_font_size", 14),
                key=f"{key_prefix}yaxis_title_sz_{self.plot_id}",
            )

        with typo_c2:
            st.markdown("**Tick Label Sizes & Colors**")
            xaxis_tickfont_size = st.number_input(
                "X-Axis Label (Tick) Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("xaxis_tickfont_size", 12),
                key=f"{key_prefix}xaxis_tick_sz_{self.plot_id}",
                help="Overwrites the basic X-axis font size in Advanced Options",
            )
            xaxis_tickfont_color = st.color_picker(
                "X-Axis Label Color",
                saved_config.get("xaxis_tickfont_color", "#444444"),
                key=f"{key_prefix}xaxis_tick_col_{self.plot_id}",
            )

            yaxis_tickfont_size = st.number_input(
                "Y-Axis Label (Tick) Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("yaxis_tickfont_size", 12),
                key=f"{key_prefix}yaxis_tick_sz_{self.plot_id}",
            )
            yaxis_tickfont_color = st.color_picker(
                "Y-Axis Label Color",
                saved_config.get("yaxis_tickfont_color", "#444444"),
                key=f"{key_prefix}yaxis_tick_col_{self.plot_id}",
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
