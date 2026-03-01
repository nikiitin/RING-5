"""Dual-axis bar + dot/line plot configuration component."""

from typing import Any

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_color_selector,
)
from src.web.components.plotting.config.plot_config_components import (
    PlotConfigComponents,
)
from src.web.models.plot_models import PlotConfig


def render(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    """Render configuration UI for a dual-axis bar + dot/line plot.

    Fully custom layout: X-axis, colour-by, separate Y-bar and Y-dot
    selectors, right Y-axis label, and dot/line settings.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Configuration dictionary with dual-axis-specific keys.
    """
    numeric_cols, categorical_cols = detect_column_types(data)

    # --- X-axis & Colour ---
    col1, col2 = st.columns(2)
    with col1:
        x_options: list[str] = categorical_cols + numeric_cols
        x_default_idx: int = 0
        if saved_config.get("x") and saved_config["x"] in x_options:
            x_default_idx = x_options.index(saved_config["x"])

        x_column: str = st.selectbox(
            "X-axis",
            options=x_options,
            index=x_default_idx,
            key=f"x_{plot_id}",
        )

    with col2:
        color_column: str | None = render_color_selector(saved_config, plot_id, categorical_cols)

    # --- Y-axes ---
    st.markdown("##### Y-axis Columns")
    yc1, yc2 = st.columns(2)
    with yc1:
        y_bar_idx: int = 0
        if saved_config.get("y_bar") and saved_config["y_bar"] in numeric_cols:
            y_bar_idx = numeric_cols.index(saved_config["y_bar"])

        y_bar: str = st.selectbox(
            "Y-axis (Bars – left)",
            options=numeric_cols,
            index=y_bar_idx,
            key=f"y_bar_{plot_id}",
        )

    with yc2:
        y_dot_idx: int = min(1, len(numeric_cols) - 1) if len(numeric_cols) > 1 else 0
        if saved_config.get("y_dot") and saved_config["y_dot"] in numeric_cols:
            y_dot_idx = numeric_cols.index(saved_config["y_dot"])

        y_dot: str = st.selectbox(
            "Y-axis (Dots – right)",
            options=numeric_cols,
            index=y_dot_idx,
            key=f"y_dot_{plot_id}",
        )

    # --- Titles & Labels ---
    default_title: str = saved_config.get("title", f"{y_bar} vs {y_dot}")
    default_xlabel: str = saved_config.get("xlabel", x_column)
    default_ylabel_bar: str = saved_config.get("ylabel_bar", y_bar)
    default_ylabel_dot: str = saved_config.get("ylabel_dot", y_dot)
    default_legend_title: str = saved_config.get("legend_title", "")

    label_config: dict[str, Any] = PlotConfigComponents.render_title_labels_section(
        saved_config=saved_config,
        plot_id=plot_id,
        default_title=default_title,
        default_xlabel=default_xlabel,
        default_ylabel=default_ylabel_bar,
        include_legend_title=True,
        default_legend_title=default_legend_title,
    )

    ylabel_dot: str = st.text_input(
        "Right Y-axis Label",
        value=default_ylabel_dot,
        key=f"ylabel_dot_{plot_id}",
    )

    # --- Dot/Line Options ---
    st.markdown("##### Dot & Line Settings")
    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        show_lines: bool = st.checkbox(
            "Show lines connecting dots",
            value=saved_config.get("show_lines", True),
            key=f"show_lines_{plot_id}",
        )
    with dc2:
        dot_symbol_options: list[str] = [
            "circle",
            "square",
            "diamond",
            "cross",
            "x",
            "triangle-up",
            "triangle-down",
        ]
        dot_symbol_idx: int = 0
        if saved_config.get("dot_symbol") and saved_config["dot_symbol"] in dot_symbol_options:
            dot_symbol_idx = dot_symbol_options.index(saved_config["dot_symbol"])

        dot_symbol: str = st.selectbox(
            "Dot Symbol",
            options=dot_symbol_options,
            index=dot_symbol_idx,
            key=f"dot_symbol_{plot_id}",
        )
    with dc3:
        dot_size: int = st.number_input(
            "Dot Size",
            min_value=2,
            max_value=30,
            value=saved_config.get("dot_size", 10),
            key=f"dot_size_{plot_id}",
        )

    dc4, dc5 = st.columns(2)
    with dc4:
        line_width: int = st.number_input(
            "Line Width",
            min_value=1,
            max_value=10,
            value=saved_config.get("line_width", 2),
            key=f"line_width_{plot_id}",
            disabled=not show_lines,
        )
    with dc5:
        dot_color: str | None = None
        if not color_column:
            dot_color = st.color_picker(
                "Dot Color",
                value=saved_config.get("dot_color", "#EF553B"),
                key=f"dot_color_{plot_id}",
            )

    return {
        "x": x_column,
        "y": y_bar,
        "y_bar": y_bar,
        "y_dot": y_dot,
        "color": color_column,
        "title": label_config["title"],
        "xlabel": label_config["xlabel"],
        "ylabel": label_config["ylabel"],
        "ylabel_bar": label_config["ylabel"],
        "ylabel_dot": ylabel_dot,
        "legend_title": label_config["legend_title"],
        "show_lines": show_lines,
        "dot_symbol": dot_symbol,
        "dot_size": dot_size,
        "dot_color": dot_color,
        "line_width": line_width,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
