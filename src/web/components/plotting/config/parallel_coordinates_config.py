"""Human-first configuration controls for parallel-coordinate plots."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.web.components.plotting.config.base_plot_config import detect_column_types
from src.web.components.plotting.config.plot_config_components import PlotConfigComponents
from src.web.models.plot_models import PlotConfig

_COLOR_SCALES = ["Viridis", "Cividis", "Plasma", "Inferno", "Magma", "Turbo", "RdBu"]
_RANGE_MODES = {"Fit each dimension": "data", "Include zero on numeric axes": "zero"}


def _saved_dimensions(saved: object, columns: list[str]) -> list[str]:
    if isinstance(saved, list):
        selected = [value for value in saved if isinstance(value, str) and value in columns]
        if len(selected) >= 2:
            return selected
    return columns[: min(4, len(columns))]


def _saved_label(mapping: dict[str, str], saved: object, fallback: str) -> str:
    return next((label for label, value in mapping.items() if value == saved), fallback)


def render(data: pd.DataFrame, saved_config: PlotConfig, plot_id: int) -> PlotConfig:
    # [impl->req~ring5.plot.parallel-coordinates~1]
    """Render ordered dimensions, numeric ranges, brushing, and color controls."""
    numeric_cols, categorical_cols = detect_column_types(data)
    all_columns = list(data.columns)
    mapping_column, title_column = st.columns(2)
    with mapping_column:
        dimensions = st.multiselect(
            "Dimensions (drag selections to order)",
            options=all_columns,
            default=_saved_dimensions(saved_config.get("parallel_dimensions"), all_columns),
            key=f"parallel_dimensions_{plot_id}",
        )
        color_options: list[str | None] = [None, *all_columns]
        saved_color = saved_config.get("parallel_color")
        color = st.selectbox(
            "Line color dimension (optional)",
            options=color_options,
            index=color_options.index(saved_color) if saved_color in color_options else 0,
            key=f"parallel_color_{plot_id}",
        )
    with title_column:
        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=plot_id,
            default_title=str(saved_config.get("title", "Compare rows across dimensions") or ""),
            default_xlabel="",
            default_ylabel="",
            include_legend_title=False,
        )

    st.markdown("#### Dimensions and ranges")
    range_column, brush_column = st.columns(2)
    with range_column:
        saved_mode = _saved_label(
            _RANGE_MODES, saved_config.get("parallel_range_mode"), "Fit each dimension"
        )
        range_choice = st.radio(
            "Numeric axis ranges",
            options=list(_RANGE_MODES),
            index=list(_RANGE_MODES).index(saved_mode),
            key=f"parallel_range_mode_{plot_id}",
        )
        st.caption(
            "Python workflows can set an exact [minimum, maximum] for each axis with "
            "parallel_ranges."
        )
    selected_numeric = [column for column in dimensions if column in numeric_cols]
    with brush_column:
        brush_options: list[str | None] = [None, *selected_numeric]
        saved_brush = saved_config.get("parallel_brush_dimension")
        brush_dimension = st.selectbox(
            "Brush one numeric dimension (optional)",
            options=brush_options,
            index=brush_options.index(saved_brush) if saved_brush in brush_options else 0,
            key=f"parallel_brush_dimension_{plot_id}",
        )
        brush_range: tuple[float, float] | None = None
        if brush_dimension:
            numeric = pd.to_numeric(data[brush_dimension], errors="coerce")
            lower, upper = float(numeric.min()), float(numeric.max())
            if upper <= lower:
                upper = lower + 1.0
            saved_range = saved_config.get("parallel_brush_range")
            default_range: tuple[float, float] = (lower, upper)
            if isinstance(saved_range, (list, tuple)) and len(saved_range) == 2:
                default_range = (float(saved_range[0]), float(saved_range[1]))
            brush_range = st.slider(
                "Visible brush range",
                min_value=lower,
                max_value=upper,
                value=default_range,
                key=f"parallel_brush_range_{plot_id}",
            )

    st.markdown("#### Brush and color scale")
    color_column, opacity_column = st.columns(2)
    with color_column:
        colorscale = st.selectbox(
            "Color scale",
            options=_COLOR_SCALES,
            index=(
                _COLOR_SCALES.index(saved_config.get("parallel_colorscale", "Viridis"))
                if saved_config.get("parallel_colorscale", "Viridis") in _COLOR_SCALES
                else 0
            ),
            disabled=color is None,
            key=f"parallel_colorscale_{plot_id}",
        )
        reverse = st.checkbox(
            "Reverse color scale",
            value=bool(saved_config.get("parallel_reverse_colorscale", False)),
            disabled=color is None,
            key=f"parallel_reverse_colorscale_{plot_id}",
        )
        show_colorbar = st.checkbox(
            "Show color scale legend",
            value=bool(saved_config.get("parallel_show_colorbar", True)),
            disabled=color is None,
            key=f"parallel_show_colorbar_{plot_id}",
        )
        line_color = st.color_picker(
            "Line color without a scale",
            value=str(saved_config.get("parallel_line_color", "#4c78a8")),
            disabled=color is not None,
            key=f"parallel_line_color_{plot_id}",
        )
    with opacity_column:
        unselected_opacity = st.slider(
            "Rows outside the brush",
            min_value=0.0,
            max_value=0.5,
            value=float(saved_config.get("parallel_unselected_opacity", 0.08)),
            step=0.01,
            key=f"parallel_unselected_opacity_{plot_id}",
        )

    return {
        "x": dimensions[0] if dimensions else "",
        "y": selected_numeric[0] if selected_numeric else "",
        "parallel_dimensions": dimensions,
        "parallel_color": color,
        "parallel_range_mode": _RANGE_MODES[range_choice],
        "parallel_brush_dimension": brush_dimension,
        "parallel_brush_range": list(brush_range) if brush_range else None,
        "parallel_colorscale": colorscale,
        "parallel_reverse_colorscale": reverse,
        "parallel_show_colorbar": show_colorbar,
        "parallel_line_color": line_color,
        "parallel_unselected_opacity": unselected_opacity,
        **label_config,
        "numeric_cols": numeric_cols,
        "categorical_cols": categorical_cols,
    }
