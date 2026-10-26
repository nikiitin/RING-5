"""Histogram plot configuration component."""

import pandas as pd
import streamlit as st

from src.core.common.distribution_metadata import inspect_distribution_layouts
from src.core.models.native_distribution_layout import (
    NativeDistributionLayout,
    OpaqueDistributionLayout,
)
from src.web.state.ui_state_manager import WidgetKeyBuilder

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_common_config,
)
from src.core.models.plot_config import PlotConfig


def _detect_histogram_variables(data: pd.DataFrame) -> list[str]:
    """Discover declared logical layouts and ordinary generic column prefixes.

    Args:
        data: DataFrame to analyse.

    Returns:
        Sorted logical keys and generic histogram names, without native prefix aliases.

    Raises:
        TypeError: Reserved layout metadata has an invalid type.
        ValueError: A declared layout or its numeric physical bindings are invalid.
    """
    layouts = inspect_distribution_layouts(data)
    hist_vars = set(layouts)
    declared_columns = {binding.column for layout in layouts.values() for binding in layout.columns}
    declared_prefixes = {column.split("..")[0] for column in declared_columns if ".." in column}
    for col in data.columns:
        if col in declared_columns:
            continue
        col_str = str(col)
        if ".." in col_str and not col_str.endswith(".sd"):
            base_var = col_str.split("..")[0]
            if base_var not in declared_prefixes:
                hist_vars.add(base_var)
    return sorted(hist_vars)


def render(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    """Render configuration UI for a histogram plot.

    Declared native cells retain their coordinates and expose count/mass/CDF
    controls. Ordinary interval histograms retain continuous rebinning controls.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Configuration dictionary with histogram-specific keys.
    """
    # [impl->req~ring5.figure.histogram-controls~2]
    # [impl->req~ring5.figure.histogram-cumulative~2]
    histogram_vars: list[str] = _detect_histogram_variables(data)

    if not histogram_vars:
        st.warning(
            "No histogram variables detected. "
            "Histogram variables should have columns like 'var..0-9', 'var..10-19', etc."
        )
        return {
            **render_common_config(data, saved_config, plot_id),
            "histogram_variable": None,
        }

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
        key=WidgetKeyBuilder.plot_key(plot_id, "widgets.histogram_var"),
        help="Select the variable with histogram bucket data",
    )

    layout = inspect_distribution_layouts(data).get(histogram_variable)
    common_saved = saved_config.copy()
    if type(layout) is NativeDistributionLayout:
        if not saved_config.get("xlabel"):
            common_saved["xlabel"] = saved_config.get("xaxis_title") or "Native bucket"
        st.info(
            "Native buckets are discrete storage cells. "
            "Their labels do not define continuous intervals."
        )
    elif type(layout) is OpaqueDistributionLayout:
        st.warning(
            "These Distribution source labels have no declared native grid. Parse Distribution "
            "output with minimum, maximum, bucket_size and zero_policy to render its cells."
        )
    config = render_common_config(data, common_saved, plot_id)

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
        key=WidgetKeyBuilder.plot_key(plot_id, "widgets.histogram_group"),
        format_func=lambda x: "None" if x is None else x,
        help="Create multiple histograms grouped by this categorical variable",
    )

    if layout is None:
        config["bucket_size"] = st.number_input(
            "Bucket Size",
            min_value=1,
            value=int(saved_config.get("bucket_size", 10)),
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.histogram_bucket"),
            help="Size of histogram buckets (for rebinning)",
        )
    else:
        config.pop("bucket_size", None)

    cumulative: bool = st.checkbox(
        "Cumulative",
        value=saved_config.get("cumulative", False),
        key=WidgetKeyBuilder.plot_key(plot_id, "widgets.histogram_cumulative"),
        help="Show cumulative distribution",
    )

    # Normalization mode
    norm_options: list[str] = ["count", "probability", "percent"]
    if layout is None or cumulative:
        norm_options.append("density")
    norm_default: str = saved_config.get("normalization", "count")
    norm_default_idx: int = norm_options.index(norm_default) if norm_default in norm_options else 0

    normalization: str = st.selectbox(
        "Normalization",
        options=norm_options,
        index=norm_default_idx,
        key=WidgetKeyBuilder.plot_key(plot_id, "widgets.histogram_norm"),
        format_func=lambda mode: ("CDF" if layout is not None and mode == "density" else mode),
        help="How to normalize histogram heights",
    )

    return {
        **config,
        "histogram_variable": histogram_variable,
        "group_by": group_by,
        "normalization": normalization,
        "cumulative": cumulative,
    }
