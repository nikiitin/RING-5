"""Right-axis trace controls for grouped stacked bar plots."""

import streamlit as st

from src.web.models.plot_models import PlotConfig


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
