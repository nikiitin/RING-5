"""Typography settings component — font sizes, colors, and tick marks.

Extracted from ``BaseStyleUI._render_typography_section()`` as a standalone
component following the component-only architecture (P1, P9).

Usage::

    component = TypographySettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(saved_config)
"""

from typing import Any

import streamlit as st


class TypographySettingsComponent:
    """Render typography controls (font sizes, colors, tick marks).

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

    def render(self, saved_config: dict[str, Any], key_prefix: str = "theme_") -> dict[str, Any]:
        """Render typography section widgets.

        Note: Title text inputs (Main Title, X-label, Y-label) are in
        the plot config UI. This section only controls font sizes,
        colors, and axis label appearance.

        Parameters
        ----------
        saved_config : dict[str, Any]
            Current saved configuration.
        key_prefix : str
            Streamlit widget key prefix (default ``"theme_"``).

        Returns
        -------
        dict[str, Any]
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

            st.markdown("**Y-Axis Title Position**")
            yaxis_title_standoff = st.slider(
                "Y-Axis Title Standoff (Spacing)",
                min_value=0,
                max_value=100,
                value=saved_config.get("yaxis_title_standoff", 0),
                key=f"{key_prefix}yaxis_title_standoff_{self.plot_id}",
                help="Distance between Y-axis ticks and the title.",
            )

            yaxis_title_vshift = st.slider(
                "Y-Axis Title Vertical Shift",
                min_value=-300,
                max_value=300,
                value=saved_config.get("yaxis_title_vshift", 0),
                key=f"{key_prefix}yaxis_title_vshift_{self.plot_id}",
                help=(
                    "Move title up (+) or down (-) along"
                    " the axis. Note: Disables native"
                    " auto-margins for title."
                ),
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

            st.markdown("**Tick Marks & Grid Lines**")
            show_xtick_marks = st.checkbox(
                "Show X-Axis Tick Marks",
                value=saved_config.get("show_xtick_marks", True),
                key=f"{key_prefix}x_show_ticks_{self.plot_id}",
            )
            dash_options = [
                "solid",
                "dot",
                "dash",
                "longdash",
                "dashdot",
                "longdashdot",
            ]
            xtick_dash_idx = 0
            if saved_config.get("xtick_dash", "solid") in dash_options:
                xtick_dash_idx = dash_options.index(saved_config.get("xtick_dash", "solid"))

            xtick_dash: str = "solid"
            if show_xtick_marks:
                xtick_dash = (
                    st.selectbox(
                        "X-Axis Grid Dash Style",
                        options=dash_options,
                        index=xtick_dash_idx,
                        key=f"{key_prefix}x_tickdash_{self.plot_id}",
                    )
                    or "solid"
                )

            show_ytick_marks = st.checkbox(
                "Show Y-Axis Tick Marks",
                value=saved_config.get("show_ytick_marks", True),
                key=f"{key_prefix}y_show_ticks_{self.plot_id}",
            )
            ytick_dash_idx = 0
            if saved_config.get("ytick_dash", "solid") in dash_options:
                ytick_dash_idx = dash_options.index(saved_config.get("ytick_dash", "solid"))

            ytick_dash: str = "solid"
            if show_ytick_marks:
                ytick_dash = (
                    st.selectbox(
                        "Y-Axis Grid Dash Style",
                        options=dash_options,
                        index=ytick_dash_idx,
                        key=f"{key_prefix}y_tickdash_{self.plot_id}",
                    )
                    or "solid"
                )

            st.markdown("**Label Spacing & Alternating**")
            xtick_pad = st.number_input(
                "X-Axis Tick Label Distance (px)",
                min_value=0.0,
                max_value=50.0,
                value=float(saved_config.get("xtick_pad", 5.0)),
                step=1.0,
                key=f"{key_prefix}xtick_pad_{self.plot_id}",
                help="Distance between X-axis tick marks and their labels.",
            )
            group_label_alternate = st.checkbox(
                "Alternate Group Labels (up/down)",
                value=saved_config.get("group_label_alternate", True),
                key=f"{key_prefix}grp_alt_{self.plot_id}",
                help="Stagger group labels to avoid overlap.",
            )
            group_label_alt_spacing = st.number_input(
                "Alt. Label Row Spacing",
                min_value=0.0,
                max_value=0.5,
                value=float(saved_config.get("group_label_alt_spacing", 0.05)),
                step=0.01,
                key=f"{key_prefix}grp_alt_sp_{self.plot_id}",
                help="Vertical distance between alternating label rows.",
            )

        return {
            "title_font_size": title_font_size,
            "xaxis_title_font_size": xaxis_title_font_size,
            "yaxis_title_font_size": yaxis_title_font_size,
            "yaxis_title_standoff": yaxis_title_standoff,
            "yaxis_title_vshift": yaxis_title_vshift,
            "xaxis_tickfont_size": xaxis_tickfont_size,
            "xaxis_tickfont_color": xaxis_tickfont_color,
            "yaxis_tickfont_size": yaxis_tickfont_size,
            "yaxis_tickfont_color": yaxis_tickfont_color,
            "show_xtick_marks": show_xtick_marks,
            "xtick_dash": xtick_dash,
            "show_ytick_marks": show_ytick_marks,
            "ytick_dash": ytick_dash,
            "xtick_pad": xtick_pad,
            "group_label_alternate": group_label_alternate,
            "group_label_alt_spacing": group_label_alt_spacing,
        }
