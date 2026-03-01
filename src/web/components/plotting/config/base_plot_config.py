"""Shared plot configuration utilities.

Provides reusable column selection, title/label rendering, and common
config assembly used by all per-plot-type config components.
"""

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.plot_config_components import (
    PlotConfigComponents,
)
from src.web.models.plot_models import PlotConfig


def detect_column_types(
    data: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    """Classify DataFrame columns into numeric and categorical.

    Args:
        data: DataFrame to analyse.

    Returns:
        Tuple of ``(numeric_cols, categorical_cols)``.
    """
    numeric_cols: list[str] = data.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols: list[str] = data.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()
    return numeric_cols, categorical_cols


def render_xy_selectors(
    saved_config: PlotConfig,
    plot_id: int,
    numeric_cols: list[str],
    categorical_cols: list[str],
    x_label: str = "X-axis",
    y_label: str = "Y-axis",
) -> tuple[str, str]:
    """Render standard X / Y column selectboxes.

    Args:
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.
        numeric_cols: Available numeric columns.
        categorical_cols: Available categorical columns.
        x_label: Label for the X selectbox.
        y_label: Label for the Y selectbox.

    Returns:
        ``(x_column, y_column)`` selected by the user.
    """
    x_options: list[str] = categorical_cols + numeric_cols

    x_default_idx: int = 0
    if saved_config.get("x") and saved_config["x"] in x_options:
        x_default_idx = x_options.index(saved_config["x"])

    x_column: str = st.selectbox(
        x_label,
        options=x_options,
        index=x_default_idx,
        key=f"x_{plot_id}",
    )

    y_default_idx: int = 0
    if saved_config.get("y") and saved_config["y"] in numeric_cols:
        y_default_idx = numeric_cols.index(saved_config["y"])

    y_column: str = st.selectbox(
        y_label,
        options=numeric_cols,
        index=y_default_idx,
        key=f"y_{plot_id}",
    )

    return x_column, y_column


def render_color_selector(
    saved_config: PlotConfig,
    plot_id: int,
    categorical_cols: list[str],
    label: str = "Color by (optional)",
) -> str | None:
    """Render a colour-by column selectbox.

    Args:
        saved_config: Previously saved configuration.
        plot_id: Plot identifier for widget keys.
        categorical_cols: Available categorical columns.
        label: Widget label.

    Returns:
        The selected column name, or ``None``.
    """
    color_options: list[str | None] = [None] + categorical_cols

    color_default_idx: int = 0
    if saved_config.get("color") and saved_config["color"] in categorical_cols:
        color_default_idx = color_options.index(saved_config["color"])

    color_column: str | None = st.selectbox(
        label,
        options=color_options,
        index=color_default_idx,
        key=f"color_{plot_id}",
    )
    return color_column


def render_common_config(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    """Render the standard X/Y selectors + title/labels in a two-column layout.

    This is the component-based replacement for ``BasePlot.render_common_config``.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Config dict with keys: ``x``, ``y``, ``title``, ``xlabel``, ``ylabel``,
        ``legend_title``, ``numeric_cols``, ``categorical_cols``.
    """
    numeric_cols, categorical_cols = detect_column_types(data)

    col1, col2 = st.columns(2)

    with col1:
        x_column, y_column = render_xy_selectors(
            saved_config, plot_id, numeric_cols, categorical_cols
        )

    with col2:
        default_title: str = saved_config.get("title", f"{y_column} by {x_column}") or ""
        default_xlabel: str = str(saved_config.get("xlabel", x_column) or "")
        default_ylabel: str = str(saved_config.get("ylabel", y_column) or "")
        default_legend_title: str = str(saved_config.get("legend_title", "") or "")

        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=default_title,
            default_xlabel=default_xlabel,
            default_ylabel=default_ylabel,
            include_legend_title=True,
            default_legend_title=default_legend_title,
        )

    return {
        "x": x_column,
        "y": y_column,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }


def render_common_with_color(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    """Render standard X/Y + title/labels + colour-by selector.

    Combines :func:`render_common_config` with :func:`render_color_selector`
    to eliminate duplication across ``BarPlot``, ``LinePlot``, ``ScatterPlot``.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier.

    Returns:
        Config dict with all common keys plus ``color``.
    """
    config = render_common_config(data, saved_config, plot_id)
    color = render_color_selector(saved_config, plot_id, config["categorical_cols"])
    return {**config, "color": color}
