"""Engine-independent grouped and stacked area chart implementation."""

from __future__ import annotations

from typing import Any, Literal, cast, override

import numpy as np
import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import LineTraceConfig
from src.core.services.visualization.palette_service import resolve_palette
from src.web.components.plotting.config import area_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import build_drill_down_payload

AreaMode = Literal["overlay", "stack", "normalize"]
AreaInterpolation = Literal["linear", "hv", "vh"]
MissingMode = Literal["gap", "zero", "interpolate"]


def _ordered_values(series: pd.Series, configured: object = None) -> list[Any]:
    available = list(series.drop_duplicates())
    if isinstance(configured, list):
        by_label = {str(value): value for value in available}
        labels = [str(label) for label in configured]
        ordered = [by_label[label] for label in labels if label in by_label]
        return ordered + [value for value in available if str(value) not in labels]
    if pd.api.types.is_numeric_dtype(series):
        return sorted(available)
    return available


def _mask(series: pd.Series, value: Any) -> pd.Series:
    return series.isna() if pd.isna(value) else series == value


def _resolve_missing(
    values: list[float], mode: MissingMode
) -> np.ndarray[Any, np.dtype[np.float64]]:
    series = pd.Series(values, dtype=float)
    if mode == "zero":
        series = series.fillna(0.0)
    elif mode == "interpolate":
        series = series.interpolate(method="linear", limit_direction="both")
    return cast(
        np.ndarray[Any, np.dtype[np.float64]],
        series.to_numpy(dtype=np.float64),
    )


class AreaPlot(BasePlot):
    """Show change over an ordered axis with optional group stacking."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "area")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render area mapping, arrangement, interpolation, and missing-value controls."""
        return area_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        # [impl->req~ring5.plot.area~1]
        """Build overlay or cumulative area traces with explicit fill baselines."""
        x_col, y_col = str(config["x"]), str(config["y"])
        if x_col not in data or y_col not in data:
            raise ValueError("Area chart columns must exist in the processed data.")
        mode = cast(AreaMode, config.get("area_mode", "overlay"))
        interpolation = cast(AreaInterpolation, config.get("area_interpolation", "linear"))
        missing = cast(MissingMode, config.get("area_missing", "gap"))
        if mode not in ("overlay", "stack", "normalize"):
            raise ValueError("Unknown area arrangement mode.")
        if interpolation not in ("linear", "hv", "vh"):
            raise ValueError("Unknown area interpolation mode.")
        if missing not in ("gap", "zero", "interpolate"):
            raise ValueError("Unknown area missing-value mode.")
        opacity = float(config.get("area_opacity", 0.55))
        if not 0.05 <= opacity <= 1:
            raise ValueError("Area opacity must be between 0.05 and 1.")

        color_col = str(config["color"]) if config.get("color") else None
        if color_col and color_col not in data:
            raise ValueError("Area color column must exist in the processed data.")
        x_values = _ordered_values(data[x_col], config.get("xaxis_order"))
        groups = (
            _ordered_values(data[color_col], config.get("legend_order")) if color_col else [None]
        )
        palette = resolve_palette(config.get("color_palette"))
        series_styles = config.get("series_styles", {})
        prepared: list[tuple[Any, str, str, np.ndarray[Any, np.dtype[np.float64]]]] = []

        for group_index, group in enumerate(groups):
            subset = data[_mask(data[color_col], group)] if color_col else data
            y_numeric = pd.to_numeric(subset[y_col], errors="coerce")
            raw_values: list[float] = []
            for x_value in x_values:
                matching = y_numeric.loc[_mask(subset[x_col], x_value)]
                raw_values.append(float(matching.mean()) if matching.notna().any() else np.nan)
            resolved = _resolve_missing(raw_values, missing)
            if not np.isfinite(resolved).any():
                continue
            name = str(group) if color_col else y_col
            style = series_styles.get(name, {}) if isinstance(series_styles, dict) else {}
            color = palette[group_index % len(palette)]
            if isinstance(style, dict) and style.get("use_color") and style.get("color"):
                color = str(style["color"])
            prepared.append((group, name, color, resolved))

        if mode == "normalize" and any(
            bool(np.any(values[np.isfinite(values)] < 0)) for _, _, _, values in prepared
        ):
            raise ValueError("Normalized area charts require non-negative values.")

        safe_values = [np.nan_to_num(values, nan=0.0) for _, _, _, values in prepared]
        totals = np.sum(safe_values, axis=0) if safe_values else np.zeros(len(x_values))
        baseline = np.zeros(len(x_values), dtype=float)
        traces: list[LineTraceConfig] = []
        for index, (group, name, color, values) in enumerate(prepared):
            if mode == "normalize":
                contribution = np.divide(
                    safe_values[index] * 100.0,
                    totals,
                    out=np.zeros_like(totals),
                    where=totals != 0,
                )
                upper = baseline + contribution
            elif mode == "stack":
                upper = baseline + safe_values[index]
            else:
                upper = values
            fill_base = (
                baseline.astype(float).tolist() if mode != "overlay" else [0.0] * len(x_values)
            )

            drill_frame = pd.DataFrame({x_col: x_values})
            drill_columns = [x_col]
            if color_col:
                drill_frame[color_col] = group
                drill_columns.append(color_col)
            traces.append(
                LineTraceConfig(
                    name=name,
                    x=x_values,
                    y=upper.astype(float).tolist(),
                    color=color,
                    opacity=opacity,
                    line_shape=interpolation,
                    show_markers=False,
                    fill="tozeroy" if index == 0 or mode == "overlay" else "tonexty",
                    fill_base=fill_base,
                    legendgroup=name,
                    custom_data={"drilldown": build_drill_down_payload(drill_frame, drill_columns)},
                )
            )
            if mode != "overlay":
                baseline = upper
        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Return the optional color grouping column."""
        color = config.get("color")
        return str(color) if color else None


__all__ = ["AreaPlot"]
