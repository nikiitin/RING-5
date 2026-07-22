"""Engine-independent grouped violin plot implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast, override

import numpy as np
import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import ViolinTraceConfig
from src.core.services.visualization.palette_service import resolve_palette
from src.web.components.plotting.config import violin_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import build_drill_down_payload

BandwidthMethod = Literal["scott", "silverman"]
DensitySpan = Literal["soft", "hard"]
DensityScale = Literal["width", "count"]
ViolinSide = Literal["both", "positive", "negative"]
SummaryMode = Literal["none", "box", "mean", "box+mean"]


@dataclass(frozen=True)
class _Distribution:
    """One cleaned category/group distribution before density construction."""

    category: Any
    category_index: int
    group: Any
    group_index: int
    name: str
    color: str
    values: np.ndarray[Any, np.dtype[np.float64]]
    drilldown: list[dict[str, Any]]


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


def _kernel_bandwidth(
    values: np.ndarray[Any, np.dtype[np.float64]],
    method: BandwidthMethod,
    scale: float,
) -> float:
    """Return a stable absolute Gaussian-kernel bandwidth."""
    if len(values) < 2:
        return max(abs(float(values[0])) * 0.05, 1e-3) * scale
    standard_deviation = float(np.std(values, ddof=1))
    if not np.isfinite(standard_deviation) or standard_deviation <= 1e-12:
        return max(abs(float(values[0])) * 0.05, 1e-3) * scale
    sample_factor = float(len(values)) ** (-0.2)
    if method == "silverman":
        q1, q3 = np.quantile(values, (0.25, 0.75), method="linear")
        robust_sigma = float(q3 - q1) / 1.34
        sigma = min(standard_deviation, robust_sigma) if robust_sigma > 0 else standard_deviation
        return float(max(0.9 * sigma * sample_factor * scale, 1e-12))
    return float(max(standard_deviation * sample_factor * scale, 1e-12))


def _kernel_density(
    values: np.ndarray[Any, np.dtype[np.float64]],
    bandwidth: float,
    span: DensitySpan,
    points: int = 128,
) -> tuple[list[float], list[float]]:
    """Precompute a normalized Gaussian density curve without engine dependencies."""
    minimum, maximum = float(values.min()), float(values.max())
    extension = 2.5 * bandwidth if span == "soft" else 0.0
    lower, upper = minimum - extension, maximum + extension
    if lower == upper:
        lower, upper = minimum - bandwidth, maximum + bandwidth
    coordinates = np.linspace(lower, upper, points)
    scaled = (coordinates[:, None] - values[None, :]) / bandwidth
    density = np.exp(-0.5 * scaled**2).mean(axis=1) / (bandwidth * np.sqrt(2.0 * np.pi))
    peak = float(density.max())
    normalized = density / peak if peak > 0 else np.zeros_like(density)
    return coordinates.astype(float).tolist(), normalized.astype(float).tolist()


class ViolinPlot(BasePlot):
    """Compare grouped distributions as configurable kernel-density violins."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "violin")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render violin-specific mapping, density, and summary controls."""
        return violin_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        # [impl->req~ring5.plot.violin~1]
        """Build one precomputed violin trace per non-empty category and group."""
        x_col, y_col = str(config["x"]), str(config["y"])
        if x_col not in data or y_col not in data:
            raise ValueError("Violin plot columns must exist in the processed data.")

        orientation = cast(Literal["vertical", "horizontal"], config.get("orientation", "vertical"))
        bandwidth_method = cast(BandwidthMethod, config.get("bandwidth_method", "scott"))
        density_span = cast(DensitySpan, config.get("density_span", "soft"))
        density_scale = cast(DensityScale, config.get("density_scale", "width"))
        side = cast(ViolinSide, config.get("violin_side", "both"))
        point_mode = cast(Literal["all", "none"], config.get("point_mode", "none"))
        summary_mode = cast(SummaryMode, config.get("summary_mode", "box"))
        if orientation not in ("vertical", "horizontal"):
            raise ValueError("Violin orientation must be 'vertical' or 'horizontal'.")
        if bandwidth_method not in ("scott", "silverman"):
            raise ValueError("Unknown violin bandwidth method.")
        if density_span not in ("soft", "hard"):
            raise ValueError("Unknown violin density span.")
        if density_scale not in ("width", "count"):
            raise ValueError("Unknown violin density scale.")
        if side not in ("both", "positive", "negative"):
            raise ValueError("Unknown violin side.")
        if point_mode not in ("all", "none"):
            raise ValueError("Unknown violin point mode.")
        if summary_mode not in ("none", "box", "mean", "box+mean"):
            raise ValueError("Unknown violin summary mode.")

        bandwidth_scale = float(config.get("bandwidth_scale", 1.0))
        jitter = float(config.get("jitter", 0.15))
        total_width = float(config.get("violin_width", 0.8))
        if not 0.05 <= bandwidth_scale <= 10:
            raise ValueError("Violin bandwidth scale must be between 0.05 and 10.")
        if not 0 <= jitter <= 0.5:
            raise ValueError("Violin point jitter must be between 0 and 0.5.")
        if not 0 < total_width <= 1:
            raise ValueError("Violin width must be greater than 0 and at most 1.")

        categories = _ordered_values(data[x_col], config.get("xaxis_order"))
        color_col = str(config["color"]) if config.get("color") else None
        groups = (
            _ordered_values(data[color_col], config.get("legend_order")) if color_col else [None]
        )
        palette = resolve_palette(config.get("color_palette"))
        series_styles = config.get("series_styles", {})
        distributions: list[_Distribution] = []

        for category_index, category in enumerate(categories):
            category_data = data[_mask(data[x_col], category)]
            for group_index, group in enumerate(groups):
                subset = (
                    category_data[_mask(category_data[color_col], group)]
                    if color_col
                    else category_data
                )
                numeric = pd.to_numeric(subset[y_col], errors="coerce")
                valid = numeric.notna()
                values = numeric.loc[valid].to_numpy(dtype=float)
                if not len(values):
                    continue
                name = str(group if color_col else category)
                style = series_styles.get(name, {}) if isinstance(series_styles, dict) else {}
                palette_index = group_index if color_col else category_index
                color = palette[palette_index % len(palette)]
                if isinstance(style, dict) and style.get("use_color") and style.get("color"):
                    color = str(style["color"])
                distributions.append(
                    _Distribution(
                        category=category,
                        category_index=category_index,
                        group=group,
                        group_index=group_index,
                        name=name,
                        color=color,
                        values=values,
                        drilldown=build_drill_down_payload(
                            subset.loc[valid], [x_col, *([color_col] if color_col else [])]
                        ),
                    )
                )

        maximum_count = max((len(item.values) for item in distributions), default=1)
        per_group_width = total_width / max(1, len(groups))
        traces: list[ViolinTraceConfig] = []
        for item in distributions:
            bandwidth = _kernel_bandwidth(item.values, bandwidth_method, bandwidth_scale)
            density_coordinates, density = _kernel_density(item.values, bandwidth, density_span)
            q1, median, q3 = np.quantile(item.values, (0.25, 0.5, 0.75), method="linear")
            offset = (item.group_index - (len(groups) - 1) / 2) * per_group_width
            traces.append(
                ViolinTraceConfig(
                    name=item.name,
                    color=item.color,
                    values=item.values.astype(float).tolist(),
                    category=str(item.category),
                    orientation=orientation,
                    density_coordinates=density_coordinates,
                    density=density,
                    bandwidth=bandwidth,
                    bandwidth_method=bandwidth_method,
                    density_span=density_span,
                    density_scale=density_scale,
                    side=side,
                    point_mode=point_mode,
                    jitter=jitter,
                    position=float(item.category_index) + offset,
                    category_position=item.category_index,
                    violin_width=per_group_width * 0.9,
                    width_scale=(
                        len(item.values) / maximum_count if density_scale == "count" else 1.0
                    ),
                    q1=float(q1),
                    median=float(median),
                    q3=float(q3),
                    mean=float(item.values.mean()),
                    show_box=summary_mode in ("box", "box+mean"),
                    show_mean=summary_mode in ("mean", "box+mean"),
                    show_in_legend=item.category_index == 0 if color_col else True,
                    legendgroup=item.name,
                    custom_data={"drilldown": item.drilldown},
                )
            )
        category_ticks: dict[str, list[float] | list[str] | list[bool]] = {
            "vals": [float(index) for index in range(len(categories))],
            "text": [str(category) for category in categories],
        }
        return TraceBuildResult(
            traces=traces,
            custom_x_ticks=category_ticks if orientation == "vertical" else None,
            custom_y_ticks=category_ticks if orientation == "horizontal" else None,
        )

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Return the color group, or category for ungrouped violins."""
        return str(config.get("color") or config.get("x"))


__all__ = ["ViolinPlot"]
