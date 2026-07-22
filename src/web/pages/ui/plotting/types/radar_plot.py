"""Engine-independent shared-scale radar chart implementation."""

from __future__ import annotations

from typing import Any, Literal, cast, override

import numpy as np
import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import RadarTraceConfig
from src.core.services.visualization.palette_service import resolve_palette
from src.web.components.plotting.config import radar_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import build_drill_down_payload

ScaleMode = Literal["data", "zero", "custom"]


def _ordered_values(series: pd.Series, configured: object = None) -> list[Any]:
    available = list(series.drop_duplicates())
    if not isinstance(configured, list):
        return available
    by_label = {str(value): value for value in available}
    labels = [str(label) for label in configured]
    ordered = [by_label[label] for label in labels if label in by_label]
    return ordered + [value for value in available if str(value) not in labels]


def _mask(series: pd.Series, value: Any) -> pd.Series:
    return series.isna() if pd.isna(value) else series == value


class RadarPlot(BasePlot):
    """Compare multivariate profiles on one shared radial scale."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "radar")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render radar mapping, scale, geometry, fill, and marker controls."""
        return radar_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        # [impl->req~ring5.plot.radar~1]
        """Build closed profiles with a scale resolved once across every series."""
        x_col, y_col = str(config["x"]), str(config["y"])
        if x_col not in data or y_col not in data:
            raise ValueError("Radar chart columns must exist in the processed data.")
        categories = _ordered_values(data[x_col], config.get("xaxis_order"))
        if len(categories) < 3:
            raise ValueError("Radar charts require at least three categories.")
        scale_mode = cast(ScaleMode, config.get("radar_scale_mode", "zero"))
        if scale_mode not in ("data", "zero", "custom"):
            raise ValueError("Unknown radar scale mode.")
        start_angle = float(config.get("radar_start_angle", 90.0))
        opacity = float(config.get("radar_opacity", 0.75))
        marker_size = int(config.get("marker_size", 6))
        line_width = float(config.get("radar_line_width", 2.0))
        if not 0 <= start_angle <= 360:
            raise ValueError("Radar start angle must be between 0 and 360 degrees.")
        if not 0.05 <= opacity <= 1:
            raise ValueError("Radar opacity must be between 0.05 and 1.")
        if not 1 <= marker_size <= 30:
            raise ValueError("Radar marker size must be between 1 and 30.")
        if not 0.25 <= line_width <= 10:
            raise ValueError("Radar line width must be between 0.25 and 10.")

        color_col = str(config["color"]) if config.get("color") else None
        if color_col and color_col not in data:
            raise ValueError("Radar color column must exist in the processed data.")
        groups = (
            _ordered_values(data[color_col], config.get("legend_order")) if color_col else [None]
        )
        prepared: list[tuple[Any, str, list[float]]] = []
        finite_values: list[float] = []
        for group in groups:
            subset = data[_mask(data[color_col], group)] if color_col else data
            numeric = pd.to_numeric(subset[y_col], errors="coerce")
            values: list[float] = []
            for category in categories:
                matching = numeric.loc[_mask(subset[x_col], category)]
                value = float(matching.mean()) if matching.notna().any() else np.nan
                values.append(value)
                if np.isfinite(value):
                    finite_values.append(value)
            if any(np.isfinite(value) for value in values):
                prepared.append((group, str(group) if color_col else y_col, values))
        if not finite_values:
            return TraceBuildResult()

        if scale_mode == "custom":
            radial_min = float(config.get("radar_min", 0.0))
            radial_max = float(config.get("radar_max", 1.0))
        else:
            radial_min, radial_max = min(finite_values), max(finite_values)
            if scale_mode == "zero" and radial_min >= 0:
                radial_min = 0.0
        if not np.isfinite(radial_min) or not np.isfinite(radial_max) or radial_max <= radial_min:
            raise ValueError("Radar maximum must be finite and greater than its minimum.")

        palette = resolve_palette(config.get("color_palette"))
        series_styles = config.get("series_styles", {})
        traces: list[RadarTraceConfig] = []
        for index, (group, name, values) in enumerate(prepared):
            style = series_styles.get(name, {}) if isinstance(series_styles, dict) else {}
            color = palette[index % len(palette)]
            if isinstance(style, dict) and style.get("use_color") and style.get("color"):
                color = str(style["color"])
            resolved = [value if np.isfinite(value) else radial_min for value in values]
            drill_frame = pd.DataFrame({x_col: categories})
            drill_columns = [x_col]
            if color_col:
                drill_frame[color_col] = group
                drill_columns.append(color_col)
            traces.append(
                RadarTraceConfig(
                    name=name,
                    color=color,
                    opacity=opacity,
                    categories=[str(category) for category in categories],
                    values=resolved,
                    radial_min=radial_min,
                    radial_max=radial_max,
                    start_angle=start_angle,
                    clockwise=bool(config.get("radar_clockwise", True)),
                    fill_area=bool(config.get("radar_fill", True)),
                    show_markers=bool(config.get("radar_markers", True)),
                    marker_size=marker_size,
                    line_width=line_width,
                    legendgroup=name,
                    custom_data={"drilldown": build_drill_down_payload(drill_frame, drill_columns)},
                )
            )
        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Return the optional series grouping column."""
        color = config.get("color")
        return str(color) if color else None


__all__ = ["RadarPlot"]
