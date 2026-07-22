"""Engine-independent grouped box plot implementation."""

from __future__ import annotations

from typing import Any, Literal, cast, override

import numpy as np
import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BoxTraceConfig
from src.core.services.visualization.palette_service import resolve_palette
from src.web.components.plotting.config import box_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import build_drill_down_payload

QuartileMethod = Literal["linear", "inclusive", "exclusive"]
WhiskerMode = Literal["tukey", "minmax", "percentile"]


def _ordered_values(series: pd.Series, configured: object = None) -> list[Any]:
    available = list(series.drop_duplicates())
    if not isinstance(configured, list):
        return available
    by_label = {str(value): value for value in available}
    configured_labels = [str(label) for label in configured]
    ordered = [by_label[label] for label in configured_labels if label in by_label]
    return ordered + [value for value in available if str(value) not in configured_labels]


def _mask(series: pd.Series, value: Any) -> pd.Series:
    return series.isna() if pd.isna(value) else series == value


def _quartiles(values: np.ndarray, method: QuartileMethod) -> tuple[float, float, float]:
    if method == "linear" or len(values) == 1:
        result = np.quantile(values, (0.25, 0.5, 0.75), method="linear")
        return float(result[0]), float(result[1]), float(result[2])

    ordered = np.sort(values)
    midpoint = len(ordered) // 2
    median = float(np.median(ordered))
    if method == "inclusive" and len(ordered) % 2:
        lower_half = ordered[: midpoint + 1]
        upper_half = ordered[midpoint:]
    else:
        lower_half = ordered[:midpoint]
        upper_half = ordered[midpoint + (len(ordered) % 2) :]
    return float(np.median(lower_half)), median, float(np.median(upper_half))


def _distribution_summary(
    values: np.ndarray,
    *,
    quartile_method: QuartileMethod,
    whisker_mode: WhiskerMode,
    whisker_multiplier: float,
    whisker_percentiles: tuple[float, float],
) -> tuple[float, float, float, float, float, list[float]]:
    q1, median, q3 = _quartiles(values, quartile_method)
    if whisker_mode == "minmax":
        lower, upper = float(values.min()), float(values.max())
    elif whisker_mode == "percentile":
        percentiles = np.quantile(
            values,
            (whisker_percentiles[0] / 100, whisker_percentiles[1] / 100),
            method="linear",
        )
        lower, upper = float(percentiles[0]), float(percentiles[1])
    else:
        iqr = q3 - q1
        lower_limit = q1 - whisker_multiplier * iqr
        upper_limit = q3 + whisker_multiplier * iqr
        inside = values[(values >= lower_limit) & (values <= upper_limit)]
        lower, upper = float(inside.min()), float(inside.max())
    outliers = values[(values < lower) | (values > upper)].astype(float).tolist()
    return q1, median, q3, lower, upper, outliers


class BoxPlot(BasePlot):
    """Compare distributions across categories and optional color groups."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "box")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render box-specific mapping and distribution controls."""
        return box_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        # [impl->req~ring5.plot.box~1]
        """Build one precomputed box trace per category and color group."""
        x_col, y_col = str(config["x"]), str(config["y"])
        if x_col not in data or y_col not in data:
            raise ValueError("Box plot columns must exist in the processed data.")

        orientation = cast(Literal["vertical", "horizontal"], config.get("orientation", "vertical"))
        quartile_method = cast(QuartileMethod, config.get("quartile_method", "linear"))
        whisker_mode = cast(WhiskerMode, config.get("whisker_mode", "tukey"))
        point_mode = cast(Literal["outliers", "all", "none"], config.get("point_mode", "outliers"))
        if orientation not in ("vertical", "horizontal"):
            raise ValueError("Box orientation must be 'vertical' or 'horizontal'.")
        if quartile_method not in ("linear", "inclusive", "exclusive"):
            raise ValueError("Unknown box quartile method.")
        if whisker_mode not in ("tukey", "minmax", "percentile"):
            raise ValueError("Unknown box whisker mode.")
        if point_mode not in ("outliers", "all", "none"):
            raise ValueError("Unknown box point mode.")

        raw_percentiles = config.get("whisker_percentiles", [5, 95])
        if not isinstance(raw_percentiles, (list, tuple)) or len(raw_percentiles) != 2:
            raise ValueError("Box whisker percentiles must contain two values.")
        percentiles = (float(raw_percentiles[0]), float(raw_percentiles[1]))
        if not 0 <= percentiles[0] < percentiles[1] <= 100:
            raise ValueError("Box whisker percentiles must increase between 0 and 100.")

        whisker_multiplier = float(config.get("whisker_multiplier", 1.5))
        jitter = float(config.get("jitter", 0.25))
        point_position = float(config.get("point_position", 0.0))
        total_width = float(config.get("box_width", 0.6))
        whisker_cap_width = float(config.get("whisker_cap_width", 0.5))
        if whisker_multiplier < 0:
            raise ValueError("Box whisker multiplier cannot be negative.")
        if not 0 <= jitter <= 0.5:
            raise ValueError("Box point jitter must be between 0 and 0.5.")
        if not -1 <= point_position <= 1:
            raise ValueError("Box point position must be between -1 and 1.")
        if not 0 < total_width <= 1:
            raise ValueError("Box width must be greater than 0 and at most 1.")
        if not 0 <= whisker_cap_width <= 1:
            raise ValueError("Box whisker cap width must be between 0 and 1.")

        categories = _ordered_values(data[x_col], config.get("xaxis_order"))
        color_col = str(config["color"]) if config.get("color") else None
        groups = (
            _ordered_values(data[color_col], config.get("legend_order")) if color_col else [None]
        )
        per_group_width = total_width / max(1, len(groups))
        palette = resolve_palette(config.get("color_palette"))
        series_styles = config.get("series_styles", {})
        traces: list[BoxTraceConfig] = []

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
                clean_subset = subset.loc[valid]
                values = numeric.loc[valid].to_numpy(dtype=float)
                if not len(values):
                    continue
                q1, median, q3, lower, upper, outliers = _distribution_summary(
                    values,
                    quartile_method=quartile_method,
                    whisker_mode=whisker_mode,
                    whisker_multiplier=whisker_multiplier,
                    whisker_percentiles=percentiles,
                )
                offset = (group_index - (len(groups) - 1) / 2) * per_group_width
                name = str(group if color_col else category)
                style = series_styles.get(name, {}) if isinstance(series_styles, dict) else {}
                palette_index = group_index if color_col else category_index
                color = palette[palette_index % len(palette)]
                if isinstance(style, dict) and style.get("use_color") and style.get("color"):
                    color = str(style["color"])
                traces.append(
                    BoxTraceConfig(
                        name=name,
                        color=color,
                        values=values.astype(float).tolist(),
                        category=str(category),
                        orientation=orientation,
                        quartile_method=quartile_method,
                        q1=q1,
                        median=median,
                        q3=q3,
                        notch_lower=median - 1.57 * (q3 - q1) / np.sqrt(len(values)),
                        notch_upper=median + 1.57 * (q3 - q1) / np.sqrt(len(values)),
                        lower_whisker=lower,
                        upper_whisker=upper,
                        mean=float(values.mean()),
                        outliers=outliers,
                        point_mode=point_mode,
                        jitter=jitter,
                        point_position=point_position,
                        position=float(category_index) + offset,
                        category_position=category_index,
                        box_width=per_group_width * 0.9,
                        whisker_cap_width=whisker_cap_width,
                        notched=bool(config.get("notched", False)),
                        show_mean=bool(config.get("show_mean", False)),
                        show_in_legend=category_index == 0 if color_col else True,
                        legendgroup=name,
                        custom_data={
                            "drilldown": build_drill_down_payload(
                                clean_subset,
                                [x_col, *([color_col] if color_col else [])],
                            )
                        },
                    )
                )
        category_ticks: dict[str, list[float] | list[str] | list[bool]] = {
            "vals": [float(index) for index in range(len(categories))],
            "text": [str(category) for category in categories],
        }
        return TraceBuildResult(
            traces=traces,
            boxmode="group",
            custom_x_ticks=category_ticks if orientation == "vertical" else None,
            custom_y_ticks=category_ticks if orientation == "horizontal" else None,
        )

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Return the color group, or category when boxes are ungrouped."""
        return str(config.get("color") or config.get("x"))


__all__ = ["BoxPlot"]
