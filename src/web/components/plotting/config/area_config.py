"""Human-first configuration controls for area charts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_color_selector,
    render_xy_selectors,
)
from src.web.components.plotting.config.plot_config_components import PlotConfigComponents
from src.web.models.plot_models import PlotConfig

_MODES = {"Overlay": "overlay", "Stack values": "stack", "100% stacked": "normalize"}
_INTERPOLATIONS = {"Linear": "linear", "Step after": "hv", "Step before": "vh"}
_MISSING = {"Leave gaps": "gap", "Fill with zero": "zero", "Interpolate": "interpolate"}


def _saved_label(mapping: dict[str, str], saved: object, fallback: str) -> str:
    return next((label for label, value in mapping.items() if value == saved), fallback)


def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
    # [impl->req~ring5.plot.area~1]
    """Render mappings plus arrangement, curve, missing-value, and opacity controls."""
    numeric_cols, categorical_cols = detect_column_types(data)
    mapping_column, label_column = st.columns(2)
    with mapping_column:
        x_column, y_column = render_xy_selectors(
            saved_config, plot_id, numeric_cols, categorical_cols
        )
        color = render_color_selector(saved_config, plot_id, categorical_cols)
    with label_column:
        normalized = saved_config.get("area_mode") == "normalize"
        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=str(saved_config.get("title", f"{y_column} across {x_column}") or ""),
            default_xlabel=str(saved_config.get("xlabel", x_column) or ""),
            default_ylabel=str(
                saved_config.get("ylabel", "Percent" if normalized else y_column) or ""
            ),
            include_legend_title=True,
            default_legend_title=str(saved_config.get("legend_title", color or "") or ""),
        )

    st.markdown("#### Area display")
    arrangement_column, curve_column = st.columns(2)
    with arrangement_column:
        mode_label = st.radio(
            "Arrangement",
            options=list(_MODES),
            index=list(_MODES).index(
                _saved_label(_MODES, saved_config.get("area_mode"), "Overlay")
            ),
            key=f"area_mode_{plot_id}",
        )
        opacity = st.slider(
            "Fill opacity",
            min_value=0.1,
            max_value=1.0,
            value=float(saved_config.get("area_opacity", 0.55)),
            step=0.05,
            key=f"area_opacity_{plot_id}",
        )
    with curve_column:
        interpolation_label = st.selectbox(
            "Curve between points",
            options=list(_INTERPOLATIONS),
            index=list(_INTERPOLATIONS).index(
                _saved_label(
                    _INTERPOLATIONS,
                    saved_config.get("area_interpolation"),
                    "Linear",
                )
            ),
            key=f"area_interpolation_{plot_id}",
        )
        missing_label = st.selectbox(
            "Missing values",
            options=list(_MISSING),
            index=list(_MISSING).index(
                _saved_label(_MISSING, saved_config.get("area_missing"), "Leave gaps")
            ),
            key=f"area_missing_{plot_id}",
        )

    return {
        "x": x_column,
        "y": y_column,
        "color": color,
        "area_mode": _MODES[mode_label],
        "area_interpolation": _INTERPOLATIONS[interpolation_label],
        "area_missing": _MISSING[missing_label],
        "area_opacity": opacity,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
