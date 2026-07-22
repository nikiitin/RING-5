"""Histogram plot configuration component."""

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_common_config,
)
from src.web.models.plot_models import PlotConfig


def _detect_histogram_variables(data: pd.DataFrame) -> list[str]:
    """Detect histogram variables from DataFrame columns.

    Looks for columns with ``..`` patterns indicating bucket ranges
    (e.g. ``var..0-10``, ``var..10-20``).

    Args:
        data: DataFrame to analyse.

    Returns:
        Sorted list of unique histogram base variable names.
    """
    hist_vars: set[str] = set()
    for col in data.columns:
        col_str = str(col)
        if ".." in col_str and not col_str.endswith(".sd"):
            base_var = col_str.split("..")[0]
            hist_vars.add(base_var)
    return sorted(hist_vars)


def render(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    """Render configuration UI for a histogram plot.

    Extends the common config with histogram-specific selectors:
    histogram variable, group-by, bucket size, normalization mode,
    and cumulative toggle.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Configuration dictionary with histogram-specific keys.
    """
    # [impl->req~ring5.figure.histogram-controls~1]
    # [impl->req~ring5.figure.histogram-cumulative~1]
    config = render_common_config(data, saved_config, plot_id)

    # Detect histogram variables
    histogram_vars: list[str] = _detect_histogram_variables(data)

    if not histogram_vars:
        st.warning(
            "No histogram variables detected. "
            "Histogram variables should have columns like 'var..0-10', 'var..10-20', etc."
        )
        return {**config, "histogram_variable": None}

    # Histogram variable selection
    default_var: str | None = (
        saved_config.get("histogram_variable")
        if saved_config.get("histogram_variable") in histogram_vars
        else histogram_vars[0]
    )
    default_idx: int = histogram_vars.index(default_var) if default_var in histogram_vars else 0

    histogram_variable: str = st.selectbox(
        "Histogram Variable",
        options=histogram_vars,
        index=default_idx,
        key=f"histogram_var_{plot_id}",
        help="Select the variable with histogram bucket data",
    )

    # Group-by
    _numeric_cols, categorical_cols = detect_column_types(data)
    group_options: list[str | None] = [None] + categorical_cols

    group_default_idx: int = 0
    if saved_config.get("group_by") and saved_config["group_by"] in categorical_cols:
        group_default_idx = group_options.index(saved_config["group_by"])

    group_by: str | None = st.selectbox(
        "Group By (optional)",
        options=group_options,
        index=group_default_idx,
        key=f"histogram_group_{plot_id}",
        format_func=lambda x: "None" if x is None else x,
        help="Create multiple histograms grouped by this categorical variable",
    )

    # Bucket size
    bucket_size: int = st.number_input(
        "Bucket Size",
        min_value=1,
        value=int(saved_config.get("bucket_size", 10)),
        key=f"histogram_bucket_{plot_id}",
        help="Size of histogram buckets (for rebinning)",
    )

    # Normalization mode
    norm_options: list[str] = ["count", "probability", "percent", "density"]
    norm_default: str = saved_config.get("normalization", "count")
    norm_default_idx: int = norm_options.index(norm_default) if norm_default in norm_options else 0

    normalization: str = st.selectbox(
        "Normalization",
        options=norm_options,
        index=norm_default_idx,
        key=f"histogram_norm_{plot_id}",
        help="How to normalize histogram heights",
    )

    # Cumulative toggle
    cumulative: bool = st.checkbox(
        "Cumulative",
        value=saved_config.get("cumulative", False),
        key=f"histogram_cumulative_{plot_id}",
        help="Show cumulative distribution",
    )

    return {
        **config,
        "histogram_variable": histogram_variable,
        "group_by": group_by,
        "bucket_size": bucket_size,
        "normalization": normalization,
        "cumulative": cumulative,
    }
