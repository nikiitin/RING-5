"""Grouped stacked bar plot configuration component."""

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
    """Render configuration UI for a grouped stacked bar plot.

    Fully custom layout: Major / Minor grouping selectors, multi-select Y
    columns, dual-axis section, and filter multi-selects.

    Args:
        data: DataFrame to plot.
        saved_config: Previously saved configuration.
        plot_id: Unique plot identifier for widget keys.

    Returns:
        Configuration dictionary with all grouped-stacked-specific keys.
    """
    numeric_cols, categorical_cols = detect_column_types(data)

    col1, col2 = st.columns(2)

    with col1:
        # X-axis (Major Group)
        x_options: list[str] = categorical_cols + numeric_cols
        x_default_idx: int = 0
        if saved_config.get("x") and saved_config["x"] in x_options:
            x_default_idx = x_options.index(saved_config["x"])

        x_column: str = st.selectbox(
            "Major Grouping (Outer)",
            options=x_options,
            index=x_default_idx,
            key=f"x_{plot_id}",
            help="The main outer category (e.g., Benchmark)",
        )

        # Sub-group (Minor Group)
        filtered_cols: list[str] = [col for col in categorical_cols if col is not None]
        options_list: list[str | None] = [None] + filtered_cols
        group_default_idx: int = 0
        if saved_config.get("group") and saved_config["group"] in categorical_cols:
            group_default_idx = categorical_cols.index(saved_config["group"])

        group_column: str | None = st.selectbox(
            "X-Axis / Minor Grouping (Inner)",
            options=options_list,
            index=group_default_idx + 1 if saved_config.get("group") else 0,
            key=f"group_{plot_id}",
            help=(
                "The variable displayed on the X-axis"
                " within the major group"
                " (e.g., Configuration)"
            ),
        )

    with col2:
        # Y-axis (Statistics to stack)
        default_ys: list[str] = saved_config.get("y_columns", [])
        default_ys = [y for y in default_ys if y in numeric_cols]

        y_columns: list[str] = st.multiselect(
            "Statistics to Stack (Y-axis)",
            options=numeric_cols,
            default=default_ys,
            key=f"y_multiselect_{plot_id}",
            help="Select multiple statistics to stack on top of each other",
        )

        # Title & Labels
        default_title: str = saved_config.get("title", f"Stacked Statistics by {x_column}")
        default_xlabel: str = str(saved_config.get("xlabel", x_column) or "")
        default_ylabel: str = str(saved_config.get("ylabel", "Value") or "")

        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=default_title,
            default_xlabel=default_xlabel,
            default_ylabel=default_ylabel,
            include_legend_title=True,
            default_legend_title=saved_config.get("legend_title", ""),
        )
        title: str = label_config["title"]
        xlabel: str = label_config["xlabel"]
        ylabel: str = label_config["ylabel"]
        legend_title: str = label_config["legend_title"]

    # ── Dual Axis ──────────────────────────────────────────
    st.markdown("#### Dual Axis (Secondary Y)")
    dual_axis: bool = st.checkbox(
        "Enable Secondary Y-axis",
        value=saved_config.get("dual_axis", False),
        key=f"dual_axis_{plot_id}",
        help=(
            "Adds a right Y-axis with its own columns. "
            "Use with Split-Apply shaper for independent transforms."
        ),
    )

    y_columns_right: list[str] = []
    right_axis_type: str = "bars"
    ylabel_right: str = ""

    if dual_axis:
        da1, da2 = st.columns(2)
        with da1:
            right_axis_type = (
                st.segmented_control(
                    "Right-axis trace type",
                    options=["bars", "dots"],
                    default=saved_config.get("right_axis_type", "bars"),
                    key=f"right_type_{plot_id}",
                )
                or "bars"
            )
        with da2:
            ylabel_right = (
                st.text_input(
                    "Right Y-axis Label",
                    value=saved_config.get("ylabel_right", ""),
                    key=f"ylabel_right_{plot_id}",
                )
                or ""
            )

        available_right: list[str] = [c for c in numeric_cols if c not in y_columns]
        default_right: list[str] = [
            c for c in saved_config.get("y_columns_right", []) if c in available_right
        ]
        y_columns_right = st.multiselect(
            "Right Y-axis columns",
            options=available_right,
            default=default_right,
            key=f"y_right_{plot_id}",
            help="Numeric columns plotted on the secondary (right) Y-axis.",
        )

    # ── Filters ────────────────────────────────────────────
    st.markdown("#### Filter Data")
    x_values, group_values = PlotConfigComponents.render_filter_multiselects(
        data=data,
        x_col=x_column,
        group_col=group_column,
        saved_config=saved_config,
        plot_id=plot_id,
        x_label=f"Filter {x_column} (X-axis)" if x_column else "Filter X values",
        group_label=(f"Filter {group_column} (Sub-group)" if group_column else "Filter Groups"),
    )

    return {
        "x": x_column,
        "group": group_column,
        "y_columns": y_columns,
        "y": y_columns[0] if y_columns else None,
        "title": title,
        "xlabel": xlabel,
        "ylabel": ylabel,
        "legend_title": legend_title,
        "x_filter": x_values,
        "group_filter": group_values,
        "dual_axis": dual_axis,
        "right_axis_type": right_axis_type,
        "y_columns_right": y_columns_right,
        "ylabel_right": ylabel_right,
        "_needs_advanced": True,
    }
