"""Human-first configuration controls for radar charts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.web.state.ui_state_manager import WidgetKeyBuilder

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_color_selector,
    render_xy_selectors,
)
from src.web.components.plotting.config.plot_config_components import PlotConfigComponents
from src.core.models.plot_config import PlotConfig
from src.web.components.plotting.settings.widget_factory import saved_option_label

_SCALES = {
    "Start at zero when possible": "zero",
    "Fit observed values": "data",
    "Custom range": "custom",
}


def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
    # [impl->req~ring5.plot.radar~1]
    """Render mappings, shared scale, rotation, fill, and marker controls."""
    numeric_cols, categorical_cols = detect_column_types(data)
    mapping_column, label_column = st.columns(2)
    with mapping_column:
        x_column, y_column = render_xy_selectors(
            saved_config,
            plot_id,
            numeric_cols,
            categorical_cols,
            x_label="X-axis categories",
            y_label="Y-axis values",
        )
        color = render_color_selector(saved_config, plot_id, categorical_cols, "Series (optional)")
    with label_column:
        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=str(saved_config.get("title", f"{y_column} profile") or ""),
            default_xlabel=str(saved_config.get("xlabel", "") or ""),
            default_ylabel=str(saved_config.get("ylabel", y_column) or ""),
            include_legend_title=True,
            default_legend_title=str(saved_config.get("legend_title", color or "") or ""),
        )

    st.markdown("#### Radar scale and geometry")
    scale_column, geometry_column = st.columns(2)
    with scale_column:
        scale_label = st.selectbox(
            "Shared radial range",
            options=list(_SCALES),
            index=list(_SCALES).index(
                saved_option_label(
                    _SCALES,
                    saved_config.get("radar_scale_mode"),
                    "Start at zero when possible",
                )
            ),
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_scale"),
        )
        scale_mode = _SCALES[scale_label]
        radar_min = float(saved_config.get("radar_min", 0.0))
        radar_max = float(saved_config.get("radar_max", 1.0))
        if scale_mode == "custom":
            radar_min = st.number_input(
                "Radial minimum",
                value=radar_min,
                key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_min"),
            )
            radar_max = st.number_input(
                "Radial maximum",
                value=radar_max,
                key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_max"),
            )
    with geometry_column:
        start_angle = st.slider(
            "First category angle",
            min_value=0,
            max_value=360,
            value=int(saved_config.get("radar_start_angle", 90)),
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_angle"),
        )
        clockwise = st.checkbox(
            "Clockwise category order",
            value=bool(saved_config.get("radar_clockwise", True)),
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_clockwise"),
        )
        line_width = st.slider(
            "Outline width",
            min_value=0.5,
            max_value=6.0,
            value=float(saved_config.get("radar_line_width", 2.0)),
            step=0.5,
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_line_width"),
        )

    st.markdown("#### Profiles")
    profile_column, marker_column = st.columns(2)
    with profile_column:
        fill_area = st.checkbox(
            "Fill profile areas",
            value=bool(saved_config.get("radar_fill", True)),
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_fill"),
        )
        opacity = st.slider(
            "Profile opacity",
            min_value=0.1,
            max_value=1.0,
            value=float(saved_config.get("radar_opacity", 0.75)),
            step=0.05,
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_opacity"),
        )
    with marker_column:
        show_markers = st.checkbox(
            "Show category markers",
            value=bool(saved_config.get("radar_markers", True)),
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_markers"),
        )
        marker_size = st.slider(
            "Marker size",
            min_value=2,
            max_value=16,
            value=int(saved_config.get("marker_size", 6)),
            disabled=not show_markers,
            key=WidgetKeyBuilder.plot_key(plot_id, "widgets.radar_marker_size"),
        )

    return {
        "x": x_column,
        "y": y_column,
        "color": color,
        "radar_scale_mode": scale_mode,
        "radar_min": radar_min,
        "radar_max": radar_max,
        "radar_start_angle": float(start_angle),
        "radar_clockwise": clockwise,
        "radar_fill": fill_area,
        "radar_markers": show_markers,
        "radar_opacity": opacity,
        "radar_line_width": line_width,
        "marker_size": marker_size,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
