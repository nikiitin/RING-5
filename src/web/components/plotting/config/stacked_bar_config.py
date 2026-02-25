"""Stacked bar plot configuration component."""

from typing import Any

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import detect_column_types
from src.web.components.plotting.config.plot_config_components import PlotConfigComponents


def render(
    data: pd.DataFrame,
    saved_config: dict[str, Any],
    plot_id: int,
) -> dict[str, Any]:
    """Render configuration UI for a stacked bar plot.

    Fully custom layout: X-axis selector, multi-select Y columns
    (statistics to stack), X filter, and title/labels.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Configuration dictionary with ``x``, ``y_columns``, ``x_filter``,
        ``title``, ``xlabel``, ``ylabel``, ``legend_title``.
    """
    numeric_cols, _categorical_cols = detect_column_types(data)
    all_cols: list[str] = data.columns.tolist()

    x_col: str = st.selectbox(
        "X-Axis (Categories)",
        options=all_cols,
        index=all_cols.index(saved_config["x"]) if saved_config.get("x") in all_cols else 0,
        key=f"stacked_x_{plot_id}",
    )

    # Statistics multi-select
    y_cols: list[str] = PlotConfigComponents.render_statistics_multiselect(
        numeric_cols=numeric_cols,
        saved_config=saved_config,
        plot_id=plot_id,
    )

    # X filter
    x_values, _ = PlotConfigComponents.render_filter_multiselects(
        data=data,
        x_col=x_col,
        group_col=None,
        saved_config=saved_config,
        plot_id=plot_id,
    )

    # Title & Labels
    default_title: str = saved_config.get("title", f"Stacked Statistics by {x_col}")
    default_xlabel: str = str(saved_config.get("xlabel", x_col) or "")
    default_ylabel: str = str(saved_config.get("ylabel", "Value") or "")

    label_config = PlotConfigComponents.render_title_labels_section(
        saved_config=saved_config,
        plot_id=plot_id,
        default_title=default_title,
        default_xlabel=default_xlabel,
        default_ylabel=default_ylabel,
        include_legend_title=True,
        default_legend_title=saved_config.get("legend_title", "Statistics"),
    )

    return {
        "x": x_col,
        "y_columns": y_cols,
        "x_filter": x_values,
        **label_config,
    }
