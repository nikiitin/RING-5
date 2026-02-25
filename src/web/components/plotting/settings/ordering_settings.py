"""Ordering settings component — reorder X-axis, groups, legend items.

Extracted from ``BasePlot._render_ordering_ui``.
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.web.components.common.reorderable_list import (
    render_reorderable_list,
)


def render_ordering_ui(
    plot_id: int,
    saved_config: dict[str, Any],
    data: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    """Render ordering controls for X-axis, groups, and legend items.

    Args:
        plot_id: Plot identifier for unique widget keys.
        saved_config: Previously saved configuration.
        data: Data being plotted.
        config: Current configuration to update.
    """
    st.markdown("#### Ordering Control")

    # X-axis Order
    if saved_config.get("x") and saved_config["x"] in data.columns:
        with st.expander("Reorder and Rename X-axis Labels"):
            unique_x: list[str] = sorted(data[saved_config["x"]].unique().tolist())
            x_result = render_reorderable_list(
                "X-axis Order",
                unique_x,
                "xaxis",
                plot_id=plot_id,
                default_order=saved_config.get("xaxis_order"),
                enable_rename=True,
                rename_map=saved_config.get("xaxis_labels"),
            )
            order_x, renames_x = x_result  # type: ignore[misc]
            config["xaxis_order"] = order_x
            if renames_x:
                config["xaxis_labels"] = renames_x

    # Group Order
    if saved_config.get("group") and saved_config["group"] in data.columns:
        with st.expander("Reorder and Rename Groups"):
            unique_g: list[str] = sorted(data[saved_config["group"]].unique().tolist())
            g_result = render_reorderable_list(
                "Group Order",
                unique_g,
                "group",
                plot_id=plot_id,
                legend_labels=saved_config.get("legend_labels"),
                default_order=saved_config.get("group_order"),
                enable_rename=True,
                rename_map=saved_config.get("legend_labels"),
            )
            order_g, renames_g = g_result  # type: ignore[misc]
            config["group_order"] = order_g
            if renames_g:
                config["legend_labels"] = renames_g

    # Legend Order (Color)
    if saved_config.get("color") and saved_config["color"] in data.columns:
        with st.expander("Reorder and Rename Legend Items"):
            unique_c: list[str] = sorted(data[saved_config["color"]].unique().tolist())
            c_result = render_reorderable_list(
                "Legend Order",
                unique_c,
                "legend",
                plot_id=plot_id,
                legend_labels=saved_config.get("legend_labels"),
                default_order=saved_config.get("legend_order"),
                enable_rename=True,
                rename_map=saved_config.get("legend_labels"),
            )
            order_c, renames_c = c_result  # type: ignore[misc]
            config["legend_order"] = order_c
            if renames_c:
                if "legend_labels" not in config:
                    config["legend_labels"] = {}
                config["legend_labels"].update(renames_c)
