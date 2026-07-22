"""Engine-independent parallel-coordinates plot implementation."""

from __future__ import annotations

from typing import Literal, cast, override

import numpy as np
import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    ParallelCoordinatesTraceConfig,
    ParallelDimensionConfig,
)
from src.web.components.plotting.config import parallel_coordinates_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import build_drill_down_payload

RangeMode = Literal["data", "zero"]
_COLOR_SCALES = {"Viridis", "Cividis", "Plasma", "Inferno", "Magma", "Turbo", "RdBu"}


def _dimension_names(value: object) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) < 2
        or any(not isinstance(column, str) or not column for column in value)
    ):
        raise ValueError("Parallel coordinates require at least two dimension columns.")
    if len(set(value)) != len(value):
        raise ValueError("Parallel-coordinate dimensions must be unique.")
    return value


def _mapping(value: object, name: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"Parallel-coordinate {name} must map dimension names to values.")
    return value


def _range(value: object, name: str) -> tuple[float, float]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(not isinstance(item, (int, float)) for item in value)
    ):
        raise ValueError(f"Parallel-coordinate {name} must contain numeric minimum and maximum.")
    lower, upper = float(value[0]), float(value[1])
    if not np.isfinite(lower) or not np.isfinite(upper) or upper <= lower:
        raise ValueError(f"Parallel-coordinate {name} maximum must exceed its minimum.")
    return lower, upper


def _encode_series(series: pd.Series) -> tuple[list[float], list[float], list[str], bool]:
    if pd.api.types.is_numeric_dtype(series):
        values = pd.to_numeric(series, errors="coerce").astype(float).tolist()
        return values, [], [], True
    labels = [str(value) for value in series.drop_duplicates()]
    encoding = {label: float(index) for index, label in enumerate(labels)}
    values = [encoding[str(value)] for value in series]
    return values, list(encoding.values()), labels, False


class ParallelCoordinatesPlot(BasePlot):
    """Compare rows across ordered numeric and categorical dimensions."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "parallel_coordinates")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render ordered dimensions, ranges, brushing, and color-scale controls."""
        return parallel_coordinates_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        # [impl->req~ring5.plot.parallel-coordinates~1]
        """Encode dimensions once and preserve their exact order for both engines."""
        dimension_names = _dimension_names(config.get("parallel_dimensions"))
        if any(column not in data for column in dimension_names):
            raise ValueError("Every parallel-coordinate dimension must exist.")
        color_column = str(config["parallel_color"]) if config.get("parallel_color") else None
        if color_column and color_column not in data:
            raise ValueError("Parallel-coordinate color column must exist.")
        required = [*dimension_names, *([color_column] if color_column else [])]
        if data[required].isna().any().any():
            raise ValueError("Parallel-coordinate dimensions and colors cannot be missing.")

        range_mode = cast(RangeMode, config.get("parallel_range_mode", "data"))
        if range_mode not in ("data", "zero"):
            raise ValueError("Unknown parallel-coordinate range mode.")
        configured_ranges = _mapping(config.get("parallel_ranges"), "ranges")
        configured_brushes = _mapping(config.get("parallel_brushes"), "brushes")
        brush_dimension = config.get("parallel_brush_dimension")
        if brush_dimension:
            if not isinstance(brush_dimension, str) or brush_dimension not in dimension_names:
                raise ValueError("Parallel-coordinate brush dimension must be selected.")
            configured_brushes[brush_dimension] = config.get("parallel_brush_range")
        aliases = _mapping(config.get("parallel_labels"), "labels")

        dimensions: list[ParallelDimensionConfig] = []
        encoded_by_column: dict[str, tuple[list[float], list[float], list[str], bool]] = {}
        for column in dimension_names:
            encoded = _encode_series(data[column])
            encoded_by_column[column] = encoded
            values, tick_values, tick_labels, numeric = encoded
            if not np.isfinite(values).all():
                raise ValueError("Parallel-coordinate values must be finite.")
            observed_min, observed_max = min(values), max(values)
            if observed_max <= observed_min:
                observed_min -= 0.5
                observed_max += 0.5
            if numeric and range_mode == "zero":
                observed_min = min(0.0, observed_min)
                observed_max = max(0.0, observed_max)
            axis_range = (
                _range(configured_ranges[column], f"range for {column}")
                if column in configured_ranges
                else (observed_min, observed_max)
            )
            brush = (
                _range(configured_brushes[column], f"brush for {column}")
                if column in configured_brushes and configured_brushes[column] is not None
                else None
            )
            label_value = aliases.get(column, column)
            if not isinstance(label_value, str):
                raise ValueError("Parallel-coordinate labels must map to strings.")
            dimensions.append(
                ParallelDimensionConfig(
                    column=column,
                    label=label_value,
                    values=values,
                    range=axis_range,
                    tick_values=tick_values,
                    tick_labels=tick_labels,
                    constraintrange=brush,
                )
            )

        color_values: list[float] | None = None
        color_ticks: list[float] = []
        color_labels: list[str] = []
        color_min, color_max = 0.0, 1.0
        if color_column:
            encoded_color = encoded_by_column.get(color_column) or _encode_series(
                data[color_column]
            )
            color_values, color_ticks, color_labels, _ = encoded_color
            if not np.isfinite(color_values).all():
                raise ValueError("Parallel-coordinate colors must be finite.")
            color_min, color_max = min(color_values), max(color_values)
            if color_max <= color_min:
                color_min -= 0.5
                color_max += 0.5
            if config.get("parallel_color_min") is not None:
                color_min = float(config["parallel_color_min"])
            if config.get("parallel_color_max") is not None:
                color_max = float(config["parallel_color_max"])
            if not np.isfinite(color_min) or not np.isfinite(color_max) or color_max <= color_min:
                raise ValueError("Parallel-coordinate color maximum must exceed its minimum.")

        colorscale = str(config.get("parallel_colorscale", "Viridis"))
        if colorscale not in _COLOR_SCALES:
            raise ValueError("Unknown parallel-coordinate color scale.")
        unselected_opacity = float(config.get("parallel_unselected_opacity", 0.08))
        if not 0 <= unselected_opacity <= 1:
            raise ValueError("Parallel-coordinate unselected opacity must be between 0 and 1.")

        trace = ParallelCoordinatesTraceConfig(
            name=color_column or "Rows",
            dimensions=dimensions,
            line_color_values=color_values,
            line_color=str(config.get("parallel_line_color", "#4c78a8")),
            colorscale=colorscale,
            reverse_colorscale=bool(config.get("parallel_reverse_colorscale", False)),
            color_min=color_min,
            color_max=color_max,
            show_colorbar=bool(config.get("parallel_show_colorbar", True)),
            colorbar_title=str(config.get("parallel_colorbar_title", color_column or "")),
            color_tick_values=color_ticks,
            color_tick_labels=color_labels,
            unselected_opacity=unselected_opacity,
            show_in_legend=False,
            custom_data={
                "drilldown": build_drill_down_payload(data, dimension_names),
            },
        )
        return TraceBuildResult(traces=[trace])

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Return the optional line-color column."""
        color = config.get("parallel_color")
        return str(color) if color else None


__all__ = ["ParallelCoordinatesPlot"]
