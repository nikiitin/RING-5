"""Ordering settings component — reorder X-axis, groups, legend items.

Extracted from ``BasePlot._render_ordering_ui``.
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.web.components.common.reorderable_list import (
    render_reorderable_list,
)
from src.web.components.common.bounded_options import bounded_unique_strings
from src.web.models.plot_models import PlotConfig


class OrderingSettingsComponent:
    """Render ordering controls for X-axis, groups, and legend items.

    Parameters
    ----------
    plot_id : int
        Unique plot identifier for Streamlit widget keys.
    plot_type : str
        Plot type identifier.
    """

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame,
        config: PlotConfig,
    ) -> None:
        """Render ordering controls for X-axis, groups, and legend items.

        Args:
            saved_config: Previously saved configuration.
            data: Data being plotted.
            config: Current configuration to update.
        """
        # [impl->req~ring5.figure.ordering-renaming~1]
        st.markdown("#### Ordering Control")

        # X-axis Order
        if saved_config.get("x") and saved_config["x"] in data.columns:
            with st.expander("Reorder and Rename X-axis Labels"):
                unique_x, truncated = bounded_unique_strings(data[saved_config["x"]])
                if truncated:
                    st.warning("Ordering options were capped for safety.")
                x_result = render_reorderable_list(
                    "X-axis Order",
                    unique_x,
                    "xaxis",
                    plot_id=self.plot_id,
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
                unique_g, truncated = bounded_unique_strings(data[saved_config["group"]])
                if truncated:
                    st.warning("Group ordering options were capped for safety.")
                g_result = render_reorderable_list(
                    "Group Order",
                    unique_g,
                    "group",
                    plot_id=self.plot_id,
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
                unique_c, truncated = bounded_unique_strings(data[saved_config["color"]])
                if truncated:
                    st.warning("Legend ordering options were capped for safety.")
                c_result = render_reorderable_list(
                    "Legend Order",
                    unique_c,
                    "legend",
                    plot_id=self.plot_id,
                    legend_labels=saved_config.get("legend_labels"),
                    default_order=saved_config.get("legend_order"),
                    enable_rename=True,
                    rename_map=saved_config.get("legend_labels"),
                )
                order_c, renames_c = c_result  # type: ignore[misc]
                config["legend_order"] = order_c
                if renames_c and isinstance(renames_c, dict):
                    if "legend_labels" not in config:
                        config["legend_labels"] = {}
                    # Ensure we have a dict to appease mypy
                    labels_dict = config["legend_labels"]
                    if isinstance(labels_dict, dict):
                        labels_dict.update(renames_c)
                    else:
                        config["legend_labels"] = dict(renames_c)

        # Stacked Series Order (y_columns — "Non-tx", "Commit", etc.)
        y_cols: list[str] = saved_config.get("y_columns", [])
        if y_cols:
            series_styles: dict[str, Any] = saved_config.get("series_styles", {})
            series_rename_map: dict[str, str] = {
                k: str(series_styles[k].get("name", k))
                for k in y_cols
                if k in series_styles and series_styles[k].get("name")
            }
            with st.expander("Reorder and Rename Stacked Series"):
                current_order: list[str] = list(y_cols)
                s_result = render_reorderable_list(
                    "Series Order",
                    current_order,
                    "series",
                    plot_id=self.plot_id,
                    enable_rename=True,
                    rename_map=series_rename_map or None,
                )
                new_order, series_renames = s_result  # type: ignore[misc]
                if new_order != current_order:
                    config["y_columns"] = new_order
                if series_renames and isinstance(series_renames, dict):
                    if "series_styles" not in config:
                        config["series_styles"] = {}
                    for k, v in series_renames.items():
                        if k not in config["series_styles"]:
                            config["series_styles"][k] = {"name": v}
                        else:
                            config["series_styles"][k]["name"] = v

        # Heatmap Y-axis Metrics
        metric_cols: list[str] = saved_config.get("metric_columns", [])
        if metric_cols:
            with st.expander("Reorder and Rename Y-axis Metrics"):
                hm_result = render_reorderable_list(
                    "Y-axis Metric Order",
                    list(metric_cols),
                    "hm_metrics",
                    plot_id=self.plot_id,
                    enable_rename=True,
                    rename_map=saved_config.get("metric_labels"),
                )
                order_hm, renames_hm = hm_result  # type: ignore[misc]
                config["metric_columns"] = order_hm
                if renames_hm:
                    config["metric_labels"] = renames_hm

        # Heatmap Facet Order (split-by column)
        facet_col: str | None = saved_config.get("facet_col")
        if facet_col and facet_col in data.columns:
            with st.expander("Reorder and Rename Facets"):
                unique_facets: list[str] = sorted(data[facet_col].astype(str).unique().tolist())
                f_result = render_reorderable_list(
                    "Facet Order",
                    unique_facets,
                    "facet",
                    plot_id=self.plot_id,
                    default_order=saved_config.get("facet_order"),
                    enable_rename=True,
                    rename_map=saved_config.get("facet_labels"),
                )
                order_f, renames_f = f_result  # type: ignore[misc]
                config["facet_order"] = order_f
                if renames_f:
                    config["facet_labels"] = renames_f


def render_ordering_ui(
    plot_id: int,
    saved_config: PlotConfig,
    data: pd.DataFrame,
    config: PlotConfig,
) -> None:
    """Deprecated: use OrderingSettingsComponent."""
    OrderingSettingsComponent(plot_id, "").render(saved_config, data, config)
