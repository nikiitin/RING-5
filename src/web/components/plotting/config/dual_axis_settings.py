"""Right-axis trace controls for grouped stacked bar plots."""

import streamlit as st

from src.web.state.ui_state_manager import WidgetKeyBuilder

from src.core.models.plot_config import PlotConfig


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
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.appearance.right_show_lines"),
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
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.appearance.right_dot_sym"),
        )
    with dc3:
        config["right_dot_size"] = st.number_input(
            "Dot Size (right)",
            min_value=2,
            max_value=30,
            value=saved_config.get("right_dot_size", 10),
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.appearance.right_dot_size"),
        )

    dc4, _ = st.columns(2)
    with dc4:
        config["right_line_width"] = st.number_input(
            "Line Width (right)",
            min_value=1,
            max_value=10,
            value=saved_config.get("right_line_width", 2),
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.appearance.right_line_w"),
            disabled=not config.get("right_show_lines", True),
        )
