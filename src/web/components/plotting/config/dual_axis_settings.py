"""Dual-axis display and right-axis trace settings for grouped stacks."""

import streamlit as st

from src.web.models.plot_models import PlotConfig


def render_dual_axis_display_settings(
    saved_config: PlotConfig, config: PlotConfig, plot_id: int
) -> None:
    """Render dual-axis display settings: grid, typography, legend.

    Shown only when ``dual_axis`` is True.

    Args:
        saved_config: Previously saved configuration.
        config: Current configuration dict to update in-place.
        plot_id: Plot identifier for unique widget keys.
    """
    # [impl->req~ring5.figure.dual-axis-controls~1]
    st.markdown("#### Dual Axis Display")

    # Grid Lines
    st.markdown("**Grid Lines**")
    g1, g2 = st.columns(2)
    with g1:
        config["show_y_grid"] = st.checkbox(
            "Show Left Y-axis Grid",
            value=saved_config.get("show_y_grid", True),
            key=f"show_left_grid_{plot_id}",
        )
    with g2:
        config["y2show_y_grid"] = st.checkbox(
            "Show Right Y-axis Grid",
            value=saved_config.get("y2show_y_grid", False),
            key=f"show_right_grid_{plot_id}",
        )

    # Secondary Y-axis Typography
    _pri_title_fs: int = int(saved_config.get("yaxis_title_font_size", 14))
    _pri_tick_fs: int = int(saved_config.get("yaxis_tickfont_size", 12))
    _pri_tick_col: str = saved_config.get("yaxis_tickfont_color", "#444444")
    _pri_standoff: int = int(saved_config.get("yaxis_title_standoff", 0))

    st.markdown("**Right Y-Axis Typography**")
    t1, t2 = st.columns(2)
    with t1:
        config["yaxis2_title_font_size"] = st.number_input(
            "Right Y-Axis Title Font Size",
            min_value=8,
            max_value=100,
            value=saved_config.get("yaxis2_title_font_size", _pri_title_fs),
            key=f"y2_title_sz_{plot_id}",
        )
        config["yaxis2_title_standoff"] = st.slider(
            "Right Y-Axis Title Standoff",
            min_value=0,
            max_value=100,
            value=saved_config.get("yaxis2_title_standoff", _pri_standoff),
            key=f"y2_title_standoff_{plot_id}",
            help="Distance between the right Y-axis ticks and the title.",
        )
    with t2:
        config["yaxis2_tickfont_size"] = st.number_input(
            "Right Y-Axis Tick Size",
            min_value=8,
            max_value=100,
            value=saved_config.get("yaxis2_tickfont_size", _pri_tick_fs),
            key=f"y2_tick_sz_{plot_id}",
        )
        config["yaxis2_tickfont_color"] = st.color_picker(
            "Right Y-Axis Tick Color",
            saved_config.get("yaxis2_tickfont_color", _pri_tick_col),
            key=f"y2_tick_col_{plot_id}",
        )

    # Legend Unification
    st.markdown("**Legend**")
    config["unified_legend"] = st.checkbox(
        "Unified Legend (all items in one legend)",
        value=saved_config.get("unified_legend", True),
        key=f"unified_legend_{plot_id}",
        help=(
            "When enabled, left and right axis items share a single legend "
            "with full position and styling controls.  When disabled, each "
            "axis group gets its own legend."
        ),
    )


def render_right_axis_dot_settings(
    saved_config: PlotConfig, config: PlotConfig, plot_id: int
) -> None:
    """Render dot & line settings for the right (secondary) Y-axis.

    Only displayed when ``dual_axis`` is True and ``right_axis_type``
    is ``"dots"``.

    Args:
        saved_config: Previously saved configuration.
        config: Current configuration dict to update in-place.
        plot_id: Plot identifier for unique widget keys.
    """
    # [impl->req~ring5.figure.dual-axis-controls~1]
    st.markdown("#### Right-Axis Dot & Line Settings")
    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        config["right_show_lines"] = st.checkbox(
            "Show lines (right axis)",
            value=saved_config.get("right_show_lines", True),
            key=f"right_show_lines_{plot_id}",
        )
    with dc2:
        symbols: list[str] = [
            "circle",
            "square",
            "diamond",
            "cross",
            "x",
            "triangle-up",
            "triangle-down",
        ]
        config["right_dot_symbol"] = st.selectbox(
            "Dot Symbol (right)",
            options=symbols,
            index=(
                symbols.index(saved_config.get("right_dot_symbol", "circle"))
                if saved_config.get("right_dot_symbol") in symbols
                else 0
            ),
            key=f"right_dot_sym_{plot_id}",
        )
    with dc3:
        config["right_dot_size"] = st.number_input(
            "Dot Size (right)",
            min_value=2,
            max_value=30,
            value=saved_config.get("right_dot_size", 10),
            key=f"right_dot_size_{plot_id}",
        )

    dc4, _ = st.columns(2)
    with dc4:
        config["right_line_width"] = st.number_input(
            "Line Width (right)",
            min_value=1,
            max_value=10,
            value=saved_config.get("right_line_width", 2),
            key=f"right_line_w_{plot_id}",
            disabled=not config.get("right_show_lines", True),
        )
