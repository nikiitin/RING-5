"""Human-first configuration controls for box plots."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import (
    detect_column_types,
    render_color_selector,
    render_xy_selectors,
)
from src.web.components.plotting.config.plot_config_components import (
    PlotConfigComponents,
)
from src.web.models.plot_models import PlotConfig

_ORIENTATION_LABELS = {"Vertical": "vertical", "Horizontal": "horizontal"}
_QUARTILE_LABELS = {
    "Linear interpolation": "linear",
    "Inclusive median": "inclusive",
    "Exclusive median": "exclusive",
}
_WHISKER_LABELS = {
    "Tukey (IQR)": "tukey",
    "Minimum to maximum": "minmax",
    "Percentile range": "percentile",
}
_POINT_LABELS = {
    "Outliers only": "outliers",
    "All observations": "all",
    "Hide points": "none",
}


def _saved_label(mapping: dict[str, str], saved: object, fallback: str) -> str:
    return next((label for label, value in mapping.items() if value == saved), fallback)


def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
    # [impl->req~ring5.plot.box~1]
    """Render column mapping and distribution controls for a box plot."""
    numeric_cols, categorical_cols = detect_column_types(data)
    orientation_label = st.radio(
        "Orientation",
        options=list(_ORIENTATION_LABELS),
        index=list(_ORIENTATION_LABELS).index(
            _saved_label(_ORIENTATION_LABELS, saved_config.get("orientation"), "Vertical")
        ),
        horizontal=True,
        key=f"box_orientation_{plot_id}",
    )
    orientation = _ORIENTATION_LABELS[orientation_label]

    col1, col2 = st.columns(2)
    with col1:
        x_column, y_column = render_xy_selectors(
            saved_config,
            plot_id,
            numeric_cols,
            categorical_cols,
            x_label="X-axis category",
            y_label="Y-axis values",
        )
        color = render_color_selector(saved_config, plot_id, categorical_cols)
    with col2:
        horizontal = orientation == "horizontal"
        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=str(saved_config.get("title", f"{y_column} by {x_column}") or ""),
            default_xlabel=str(
                saved_config.get("xlabel", y_column if horizontal else x_column) or ""
            ),
            default_ylabel=str(
                saved_config.get("ylabel", x_column if horizontal else y_column) or ""
            ),
            include_legend_title=True,
            default_legend_title=str(saved_config.get("legend_title", color or "") or ""),
        )

    st.markdown("#### Distribution summary")
    settings_1, settings_2 = st.columns(2)
    with settings_1:
        quartile_label = st.selectbox(
            "Quartile calculation",
            options=list(_QUARTILE_LABELS),
            index=list(_QUARTILE_LABELS).index(
                _saved_label(
                    _QUARTILE_LABELS,
                    saved_config.get("quartile_method"),
                    "Linear interpolation",
                )
            ),
            key=f"box_quartile_{plot_id}",
        )
        whisker_label = st.selectbox(
            "Whisker range",
            options=list(_WHISKER_LABELS),
            index=list(_WHISKER_LABELS).index(
                _saved_label(_WHISKER_LABELS, saved_config.get("whisker_mode"), "Tukey (IQR)")
            ),
            key=f"box_whisker_{plot_id}",
        )
        whisker_mode = _WHISKER_LABELS[whisker_label]
        whisker_multiplier = float(saved_config.get("whisker_multiplier", 1.5))
        whisker_percentiles = saved_config.get("whisker_percentiles", (5, 95))
        if whisker_mode == "tukey":
            whisker_multiplier = st.slider(
                "IQR multiplier",
                min_value=0.5,
                max_value=3.0,
                value=whisker_multiplier,
                step=0.25,
                key=f"box_iqr_{plot_id}",
            )
        elif whisker_mode == "percentile":
            whisker_percentiles = st.slider(
                "Whisker percentiles",
                min_value=0,
                max_value=100,
                value=tuple(whisker_percentiles),
                key=f"box_percentiles_{plot_id}",
            )
    with settings_2:
        point_label = st.selectbox(
            "Show observations",
            options=list(_POINT_LABELS),
            index=list(_POINT_LABELS).index(
                _saved_label(_POINT_LABELS, saved_config.get("point_mode"), "Outliers only")
            ),
            key=f"box_points_{plot_id}",
        )
        jitter = st.slider(
            "Point jitter",
            min_value=0.0,
            max_value=0.5,
            value=float(saved_config.get("jitter", 0.25)),
            step=0.05,
            key=f"box_jitter_{plot_id}",
        )
        box_width = st.slider(
            "Box width",
            min_value=0.2,
            max_value=0.9,
            value=float(saved_config.get("box_width", 0.6)),
            step=0.05,
            key=f"box_width_{plot_id}",
        )
        whisker_cap_width = st.slider(
            "Whisker cap width",
            min_value=0.0,
            max_value=1.0,
            value=float(saved_config.get("whisker_cap_width", 0.5)),
            step=0.1,
            key=f"box_cap_width_{plot_id}",
        )
        notched = st.checkbox(
            "Notched boxes",
            value=bool(saved_config.get("notched", False)),
            key=f"box_notched_{plot_id}",
        )
        show_mean = st.checkbox(
            "Show mean",
            value=bool(saved_config.get("show_mean", False)),
            key=f"box_mean_{plot_id}",
        )

    return {
        "x": x_column,
        "y": y_column,
        "color": color,
        "orientation": orientation,
        "quartile_method": _QUARTILE_LABELS[quartile_label],
        "whisker_mode": whisker_mode,
        "whisker_multiplier": whisker_multiplier,
        "whisker_percentiles": list(whisker_percentiles),
        "point_mode": _POINT_LABELS[point_label],
        "jitter": jitter,
        "box_width": box_width,
        "whisker_cap_width": whisker_cap_width,
        "notched": notched,
        "show_mean": show_mean,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
