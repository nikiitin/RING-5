"""Human-first configuration controls for ECDF plots."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_color_selector,
)
from src.web.components.plotting.config.plot_config_components import PlotConfigComponents
from src.web.models.plot_models import PlotConfig

_DISPLAY_MODES = {
    "Cumulative distribution": False,
    "Complementary (survival)": True,
}
_Y_MODES = {"Proportion (0 to 1)": "proportion", "Observation count": "count"}


def _saved_label(mapping: Mapping[str, object], saved: object, fallback: str) -> str:
    return next((label for label, value in mapping.items() if value == saved), fallback)


def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
    # [impl->req~ring5.plot.ecdf~1]
    """Render numeric mapping, grouping, cumulative mode, and marker controls."""
    numeric_cols, categorical_cols = detect_column_types(data)
    mapping_column, label_column = st.columns(2)
    with mapping_column:
        saved_x = saved_config.get("x")
        x_index = numeric_cols.index(saved_x) if saved_x in numeric_cols else 0
        x_column = st.selectbox(
            "X-axis values",
            options=numeric_cols,
            index=x_index,
            key=f"x_{plot_id}",
        )
        color = render_color_selector(saved_config, plot_id, categorical_cols)
    with label_column:
        default_y_label = (
            "Cumulative proportion"
            if saved_config.get("ecdf_y_mode", "proportion") == "proportion"
            else "Cumulative observations"
        )
        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=str(saved_config.get("title", f"Distribution of {x_column}") or ""),
            default_xlabel=str(saved_config.get("xlabel", x_column) or ""),
            default_ylabel=str(saved_config.get("ylabel", default_y_label) or ""),
            include_legend_title=True,
            default_legend_title=str(saved_config.get("legend_title", color or "") or ""),
        )

    st.markdown("#### Cumulative display")
    display_column, marker_column = st.columns(2)
    with display_column:
        display_options: list[str] = list(_DISPLAY_MODES)
        display_label = (
            st.radio(
                "Direction",
                options=display_options,
                index=display_options.index(
                    _saved_label(
                        _DISPLAY_MODES,
                        bool(saved_config.get("ecdf_complementary", False)),
                        "Cumulative distribution",
                    )
                ),
                key=f"ecdf_direction_{plot_id}",
            )
            or "Cumulative distribution"
        )
        y_mode_options: list[str] = list(_Y_MODES)
        y_mode_label = (
            st.radio(
                "Y-axis meaning",
                options=y_mode_options,
                index=y_mode_options.index(
                    _saved_label(
                        _Y_MODES,
                        saved_config.get("ecdf_y_mode", "proportion"),
                        "Proportion (0 to 1)",
                    )
                ),
                key=f"ecdf_y_mode_{plot_id}",
            )
            or "Proportion (0 to 1)"
        )
    with marker_column:
        show_markers = st.checkbox(
            "Show observed thresholds",
            value=bool(saved_config.get("ecdf_markers", False)),
            key=f"ecdf_markers_{plot_id}",
        )
        marker_size = st.slider(
            "Marker size",
            min_value=2,
            max_value=16,
            value=int(saved_config.get("marker_size", 6)),
            disabled=not show_markers,
            key=f"ecdf_marker_size_{plot_id}",
        )

    return {
        "x": x_column,
        "color": color,
        "ecdf_complementary": _DISPLAY_MODES[display_label],
        "ecdf_y_mode": _Y_MODES[y_mode_label],
        "ecdf_markers": show_markers,
        "marker_size": marker_size,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
