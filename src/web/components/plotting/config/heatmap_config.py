"""Heatmap plot configuration component.

Renders configuration for wide-format heatmaps where:
- X-axis = configuration column (e.g. config_abbrev)
- Y-axis = selected metric columns (e.g. l0_ctrl*_aborted_cycles)
- Cell value = aggregated metric value

Optionally splits the chart into one heatmap per facet value
(e.g. benchmark_name).
"""

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
)
from src.web.components.plotting.config.plot_config_components import (
    PlotConfigComponents,
)
from src.web.models.plot_models import PlotConfig


def _sync_auto_xlabel(saved_config: PlotConfig, plot_id: int, x_column: str) -> None:
    """Follow X mapping changes while preserving a custom axis label."""
    previous_x = saved_config.get("x")
    if not isinstance(previous_x, str) or previous_x == x_column:
        return
    widget_key = f"xlabel_{plot_id}"
    current_value = st.session_state.get(widget_key, saved_config.get("xlabel"))
    if current_value == previous_x:
        st.session_state[widget_key] = x_column


def render(
    data: pd.DataFrame,
    saved_config: PlotConfig,
    plot_id: int,
) -> PlotConfig:
    """Render configuration UI for a heatmap plot.

    The heatmap expects wide-format data:
    - **X-axis**: a categorical (or numeric) column for columns
    - **Y-axis metrics**: one or more numeric columns as heatmap rows
    - **Split by (optional)**: categorical column to generate one heatmap per value

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Configuration dictionary.
    """
    # [impl->req~ring5.figure.heatmap-controls~1]
    numeric_cols, categorical_cols = detect_column_types(data)
    all_cols: list[str] = categorical_cols + numeric_cols

    col1, col2 = st.columns(2)

    with col1:
        # X-axis selector (config column for heatmap columns)
        x_default_idx: int = 0
        if saved_config.get("x") and saved_config["x"] in all_cols:
            x_default_idx = all_cols.index(saved_config["x"])

        x_column: str = st.selectbox(
            "X-axis (columns)",
            options=all_cols,
            index=x_default_idx,
            key=f"x_{plot_id}",
            help="Configuration column displayed along the X-axis.",
        )

        facet_options: list[str] = ["(none)"] + [c for c in categorical_cols if c != x_column]
        default_facet = str(saved_config.get("facet_col", "") or "")
        if default_facet and default_facet in facet_options:
            facet_default_idx = facet_options.index(default_facet)
        elif "benchmark_name" in facet_options:
            facet_default_idx = facet_options.index("benchmark_name")
        else:
            facet_default_idx = 0

        facet_col_raw: str = st.selectbox(
            "Split by (one heatmap per value)",
            options=facet_options,
            index=facet_default_idx,
            key=f"hm_facet_{plot_id}",
            help="Use benchmark_name to create one heatmap per benchmark.",
        )
        facet_col: str | None = None if facet_col_raw == "(none)" else facet_col_raw

        metric_defaults: list[str] = []
        saved_metrics = saved_config.get("metric_columns")
        if isinstance(saved_metrics, list):
            metric_defaults = [str(c) for c in saved_metrics if str(c) in numeric_cols]
        if not metric_defaults:
            auto_metrics = [c for c in numeric_cols if c.startswith("l0_ctrl")]
            metric_defaults = (
                auto_metrics if auto_metrics else numeric_cols[: min(8, len(numeric_cols))]
            )

        # Sanitize multiselect session state before rendering.
        # Streamlit >= 1.53 raises StreamlitInvalidOptionError when session state
        # holds values that are no longer present in options (e.g. after a pipeline
        # update removes columns that were previously selected as Y-axis metrics).
        # Filtering invalid entries here preserves the valid subset and prevents the
        # exception from propagating — which would otherwise hide the "Show Totals"
        # checkbox rendered below and block all figure regeneration.
        _mc_key = f"hm_metrics_{plot_id}"
        if _mc_key in st.session_state:
            _mc_state = st.session_state[_mc_key]
            if isinstance(_mc_state, list):
                _mc_valid = [v for v in _mc_state if v in numeric_cols]
                if len(_mc_valid) != len(_mc_state):
                    st.session_state[_mc_key] = _mc_valid

        metric_columns: list[str] = st.multiselect(
            "Y-axis Metrics (rows)",
            options=numeric_cols,
            default=metric_defaults,
            key=f"hm_metrics_{plot_id}",
            help="Each selected numeric column becomes one row in the heatmap.",
        )

    _sync_auto_xlabel(saved_config, plot_id, x_column)

    with col2:
        default_title: str = saved_config.get("title", "Heatmap") or ""
        default_xlabel: str = str(saved_config.get("xlabel", x_column) or "")
        default_ylabel: str = str(saved_config.get("ylabel", "Metrics") or "")

        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=default_title,
            default_xlabel=default_xlabel,
            default_ylabel=default_ylabel,
        )

    # Heatmap options
    st.markdown("**Heatmap Options**")

    agg_options = ["mean", "sum", "min", "max", "median", "first"]
    agg_default_idx: int = 0
    if saved_config.get("aggregation") in agg_options:
        agg_default_idx = agg_options.index(saved_config["aggregation"])

    aggregation: str = (
        st.selectbox(
            "Aggregation",
            options=agg_options,
            index=agg_default_idx,
            key=f"hm_agg_{plot_id}",
            help=("How to aggregate when multiple rows share " "the same (X, Y) combination."),
        )
        or "mean"
    )

    # Filters
    # Pass facet_col directly (None when no facet selected) so only
    # the X filter renders — avoids a confusing duplicate filter widget.
    x_filter, facet_filter = PlotConfigComponents.render_filter_multiselects(
        data=data,
        x_col=x_column,
        group_col=facet_col,
        saved_config=saved_config,
        plot_id=plot_id,
        x_label="Filter X values",
        group_label="Filter split values",
    )

    return {
        "x": x_column,
        "metric_columns": metric_columns,
        "facet_col": facet_col,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
        "aggregation": aggregation,
        "x_filter": x_filter,
        "group_filter": facet_filter,
    }
