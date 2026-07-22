"""Human-first configuration controls for violin plots."""

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

_ORIENTATIONS = {"Vertical": "vertical", "Horizontal": "horizontal"}
_BANDWIDTHS = {"Scott's rule": "scott", "Silverman's rule": "silverman"}
_SPANS = {"Include smoothed tails": "soft", "Observed range only": "hard"}
_SCALES = {"Equal maximum width": "width", "Scale by sample count": "count"}
_SIDES = {"Both sides": "both", "Right / upper side": "positive", "Left / lower side": "negative"}
_SUMMARIES = {
    "Box and median": "box",
    "Mean line": "mean",
    "Box and mean": "box+mean",
    "None": "none",
}


def _saved_label(mapping: dict[str, str], saved: object, fallback: str) -> str:
    return next((label for label, value in mapping.items() if value == saved), fallback)


def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
    # [impl->req~ring5.plot.violin~1]
    """Render mapping, density, observation, and summary controls."""
    numeric_cols, categorical_cols = detect_column_types(data)
    orientation_label = st.radio(
        "Orientation",
        options=list(_ORIENTATIONS),
        index=list(_ORIENTATIONS).index(
            _saved_label(_ORIENTATIONS, saved_config.get("orientation"), "Vertical")
        ),
        horizontal=True,
        key=f"violin_orientation_{plot_id}",
    )
    orientation = _ORIENTATIONS[orientation_label]

    columns, labels = st.columns(2)
    with columns:
        x_column, y_column = render_xy_selectors(
            saved_config,
            plot_id,
            numeric_cols,
            categorical_cols,
            x_label="X-axis category",
            y_label="Y-axis values",
        )
        color = render_color_selector(saved_config, plot_id, categorical_cols)
    with labels:
        horizontal = orientation == "horizontal"
        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=str(
                saved_config.get("title", f"{y_column} distribution by {x_column}") or ""
            ),
            default_xlabel=str(
                saved_config.get("xlabel", y_column if horizontal else x_column) or ""
            ),
            default_ylabel=str(
                saved_config.get("ylabel", x_column if horizontal else y_column) or ""
            ),
            include_legend_title=True,
            default_legend_title=str(saved_config.get("legend_title", color or "") or ""),
        )

    st.markdown("#### Density shape")
    density_left, density_right = st.columns(2)
    with density_left:
        bandwidth_label = st.selectbox(
            "Bandwidth rule",
            options=list(_BANDWIDTHS),
            index=list(_BANDWIDTHS).index(
                _saved_label(_BANDWIDTHS, saved_config.get("bandwidth_method"), "Scott's rule")
            ),
            key=f"violin_bandwidth_method_{plot_id}",
        )
        bandwidth_scale = st.slider(
            "Smoothing multiplier",
            min_value=0.25,
            max_value=3.0,
            value=float(saved_config.get("bandwidth_scale", 1.0)),
            step=0.05,
            help="Lower values reveal more detail; higher values produce a smoother density.",
            key=f"violin_bandwidth_scale_{plot_id}",
        )
        span_label = st.selectbox(
            "Density extent",
            options=list(_SPANS),
            index=list(_SPANS).index(
                _saved_label(_SPANS, saved_config.get("density_span"), "Include smoothed tails")
            ),
            key=f"violin_span_{plot_id}",
        )
    with density_right:
        scale_label = st.selectbox(
            "Width comparison",
            options=list(_SCALES),
            index=list(_SCALES).index(
                _saved_label(_SCALES, saved_config.get("density_scale"), "Equal maximum width")
            ),
            key=f"violin_scale_{plot_id}",
        )
        side_label = st.selectbox(
            "Density side",
            options=list(_SIDES),
            index=list(_SIDES).index(
                _saved_label(_SIDES, saved_config.get("violin_side"), "Both sides")
            ),
            key=f"violin_side_{plot_id}",
        )
        violin_width = st.slider(
            "Violin width",
            min_value=0.2,
            max_value=0.95,
            value=float(saved_config.get("violin_width", 0.8)),
            step=0.05,
            key=f"violin_width_{plot_id}",
        )

    st.markdown("#### Summary and observations")
    summary_column, point_column = st.columns(2)
    with summary_column:
        summary_label = st.selectbox(
            "Inner summary",
            options=list(_SUMMARIES),
            index=list(_SUMMARIES).index(
                _saved_label(_SUMMARIES, saved_config.get("summary_mode"), "Box and median")
            ),
            key=f"violin_summary_{plot_id}",
        )
    with point_column:
        show_points = st.checkbox(
            "Show observations",
            value=saved_config.get("point_mode") == "all",
            key=f"violin_points_{plot_id}",
        )
        jitter = st.slider(
            "Observation jitter",
            min_value=0.0,
            max_value=0.5,
            value=float(saved_config.get("jitter", 0.15)),
            step=0.05,
            disabled=not show_points,
            key=f"violin_jitter_{plot_id}",
        )

    return {
        "x": x_column,
        "y": y_column,
        "color": color,
        "orientation": orientation,
        "bandwidth_method": _BANDWIDTHS[bandwidth_label],
        "bandwidth_scale": bandwidth_scale,
        "density_span": _SPANS[span_label],
        "density_scale": _SCALES[scale_label],
        "violin_side": _SIDES[side_label],
        "summary_mode": _SUMMARIES[summary_label],
        "point_mode": "all" if show_points else "none",
        "jitter": jitter,
        "violin_width": violin_width,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
