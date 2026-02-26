"""Heatmap plot configuration component.

Renders configuration for wide-format heatmaps where:
- X-axis = configuration column (e.g. config_abbrev)
- Y-axis = selected metric columns (e.g. l0_ctrl*_aborted_cycles)
- Cell value = aggregated metric value

Optionally splits the chart into one heatmap per facet value
(e.g. benchmark_name).
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
)
from src.web.components.plotting.config.plot_config_components import (
    PlotConfigComponents,
)


def render(
    data: pd.DataFrame,
    saved_config: dict[str, Any],
    plot_id: int,
) -> dict[str, Any]:
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

        metric_columns: list[str] = st.multiselect(
            "Y-axis Metrics (rows)",
            options=numeric_cols,
            default=metric_defaults,
            key=f"hm_metrics_{plot_id}",
            help="Each selected numeric column becomes one row in the heatmap.",
        )

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

    # ── Heatmap options ─────────────────────────────────────────
    st.markdown("**Heatmap Options**")
    opt_c1, opt_c2 = st.columns(2)

    with opt_c1:
        colorscale_options = [
            "Viridis",
            "Plasma",
            "Inferno",
            "Magma",
            "Cividis",
            "Blues",
            "Reds",
            "Greens",
            "YlOrRd",
            "RdBu",
            "Spectral",
            "Hot",
            "Greys",
        ]
        cs_default_idx: int = 0
        if saved_config.get("colorscale") in colorscale_options:
            cs_default_idx = colorscale_options.index(saved_config["colorscale"])

        colorscale: str = (
            st.selectbox(
                "Color Scale",
                options=colorscale_options,
                index=cs_default_idx,
                key=f"hm_colorscale_{plot_id}",
                help="Color palette for the heatmap.",
            )
            or "Viridis"
        )

        show_values = st.checkbox(
            "Show Cell Values",
            value=saved_config.get("show_cell_values", True),
            key=f"hm_show_vals_{plot_id}",
            help="Display numeric values inside each cell.",
        )

    with opt_c2:
        reverse_colorscale = st.checkbox(
            "Reverse Color Scale",
            value=saved_config.get("reverse_colorscale", False),
            key=f"hm_rev_cs_{plot_id}",
            help="Reverse the direction of the color scale.",
        )

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

    # ── Filters ─────────────────────────────────────────────────
    facet_for_filter = facet_col if facet_col else x_column
    x_filter, facet_filter = PlotConfigComponents.render_filter_multiselects(
        data=data,
        x_col=x_column,
        group_col=facet_for_filter,
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
        "colorscale": colorscale,
        "reverse_colorscale": reverse_colorscale,
        "show_cell_values": show_values,
        "aggregation": aggregation,
        "x_filter": x_filter,
        "facet_filter": facet_filter,
    }
