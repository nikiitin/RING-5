"""Dual-axis settings UI components for GroupedStackedBarPlot.

Extracted from GroupedStackedBarPlot to reduce class size.
Renders dual-axis display, secondary legend, and right-axis dot settings.
"""

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

    # When using separate legends, show full controls for legend2
    if not config.get("unified_legend", True):
        render_secondary_legend_controls(saved_config, config, plot_id)


def render_secondary_legend_controls(
    saved_config: PlotConfig, config: PlotConfig, plot_id: int
) -> None:
    """Render full legend controls for the secondary (right-axis) legend.

    Mirrors the primary legend controls from ``BaseStyleUI`` to give the
    user equivalent control over position, appearance, and sizing.

    Args:
        saved_config: Previously saved configuration.
        config: Current configuration dict to update in-place.
        plot_id: Plot identifier for unique widget keys.
    """
    # [impl->req~ring5.figure.dual-axis-controls~1]
    st.markdown("##### Right-Axis Legend")

    # Position & Orientation
    st.markdown("**Position & Orientation**")
    p1, p2 = st.columns(2)
    with p1:
        config["legend2_orientation"] = st.selectbox(
            "Orientation (Right Legend)",
            options=["v", "h"],
            format_func=lambda x: "Vertical" if x == "v" else "Horizontal",
            index=0 if saved_config.get("legend2_orientation", "v") == "v" else 1,
            key=f"leg2_orient_{plot_id}",
        )
        config["legend2_x"] = st.number_input(
            "X Position",
            value=float(saved_config.get("legend2_x", 1.0)),
            step=0.05,
            min_value=-0.5,
            max_value=2.0,
            format="%.2f",
            key=f"leg2_x_{plot_id}",
        )
    with p2:
        config["legend2_xanchor"] = st.selectbox(
            "X Anchor",
            options=["auto", "left", "center", "right"],
            index=["auto", "left", "center", "right"].index(
                saved_config.get("legend2_xanchor", "right")
            ),
            key=f"leg2_xanc_{plot_id}",
        )
        config["legend2_y"] = st.number_input(
            "Y Position",
            value=float(saved_config.get("legend2_y", 1.0)),
            step=0.05,
            min_value=-0.5,
            max_value=2.0,
            format="%.2f",
            key=f"leg2_y_{plot_id}",
        )

    q1, q2 = st.columns(2)
    with q1:
        config["legend2_yanchor"] = st.selectbox(
            "Y Anchor",
            options=["auto", "top", "middle", "bottom"],
            index=["auto", "top", "middle", "bottom"].index(
                saved_config.get("legend2_yanchor", "top")
            ),
            key=f"leg2_yanc_{plot_id}",
        )

    # Appearance
    st.markdown("**Appearance (Right Legend)**")
    a1, a2 = st.columns(2)
    with a1:
        config["legend2_bgcolor"] = st.color_picker(
            "Background",
            saved_config.get("legend2_bgcolor", "#ffffff"),
            key=f"leg2_bg_{plot_id}",
        )
        config["legend2_border_color"] = st.color_picker(
            "Border Color",
            saved_config.get("legend2_border_color", "#000000"),
            key=f"leg2_bord_col_{plot_id}",
        )
        config["legend2_border_width"] = st.number_input(
            "Border Width",
            min_value=0,
            max_value=5,
            value=saved_config.get("legend2_border_width", 0),
            key=f"leg2_bord_w_{plot_id}",
        )
    with a2:
        config["legend2_font_color"] = st.color_picker(
            "Font Color",
            saved_config.get("legend2_font_color", "#000000"),
            key=f"leg2_font_col_{plot_id}",
        )
        config["legend2_font_size"] = st.number_input(
            "Font Size",
            min_value=8,
            max_value=100,
            value=saved_config.get("legend2_font_size", 12),
            key=f"leg2_font_sz_{plot_id}",
        )
        config["legend2_title"] = st.text_input(
            "Legend Title",
            value=saved_config.get("legend2_title", ""),
            key=f"leg2_title_{plot_id}",
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
