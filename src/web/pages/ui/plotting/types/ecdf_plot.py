"""Engine-independent empirical cumulative distribution plot."""

from __future__ import annotations

from typing import Any, Literal, cast, override

import numpy as np
import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import LineTraceConfig
from src.core.services.visualization.palette_service import resolve_palette
from src.web.components.plotting.config import ecdf_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import build_drill_down_payload

EcdfYMode = Literal["proportion", "count"]


def _ordered_groups(series: pd.Series, configured: object = None) -> list[Any]:
    available = list(series.drop_duplicates())
    if not isinstance(configured, list):
        return available
    by_label = {str(value): value for value in available}
    labels = [str(label) for label in configured]
    ordered = [by_label[label] for label in labels if label in by_label]
    return ordered + [value for value in available if str(value) not in labels]


def _mask(series: pd.Series, value: Any) -> pd.Series:
    return series.isna() if pd.isna(value) else series == value


class EcdfPlot(BasePlot):
    """Plot cumulative or complementary empirical distributions by group."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "ecdf")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render ECDF value, grouping, axis, and marker controls."""
        return ecdf_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        # [impl->req~ring5.plot.ecdf~1]
        """Build sorted step traces with duplicate thresholds aggregated."""
        x_col = str(config["x"])
        if x_col not in data:
            raise ValueError("ECDF value column must exist in the processed data.")
        y_mode = cast(EcdfYMode, config.get("ecdf_y_mode", "proportion"))
        if y_mode not in ("proportion", "count"):
            raise ValueError("ECDF Y-axis mode must be 'proportion' or 'count'.")
        complementary = bool(config.get("ecdf_complementary", False))
        show_markers = bool(config.get("ecdf_markers", False))
        marker_size = int(config.get("marker_size", 6))
        if not 1 <= marker_size <= 30:
            raise ValueError("ECDF marker size must be between 1 and 30.")

        color_col = str(config["color"]) if config.get("color") else None
        if color_col and color_col not in data:
            raise ValueError("ECDF color column must exist in the processed data.")
        groups = (
            _ordered_groups(data[color_col], config.get("legend_order")) if color_col else [None]
        )
        palette = resolve_palette(config.get("color_palette"))
        series_styles = config.get("series_styles", {})
        traces: list[LineTraceConfig] = []

        for group_index, group in enumerate(groups):
            subset = data[_mask(data[color_col], group)] if color_col else data
            numeric = pd.to_numeric(subset[x_col], errors="coerce")
            values = numeric.loc[numeric.notna()].to_numpy(dtype=float)
            if not len(values):
                continue
            thresholds, counts = np.unique(values, return_counts=True)
            cumulative = np.cumsum(counts).astype(float)
            ordinates = float(len(values)) - cumulative if complementary else cumulative
            if y_mode == "proportion":
                ordinates = ordinates / float(len(values))
            name = str(group) if color_col else x_col
            style = series_styles.get(name, {}) if isinstance(series_styles, dict) else {}
            color = palette[group_index % len(palette)]
            if isinstance(style, dict) and style.get("use_color") and style.get("color"):
                color = str(style["color"])

            threshold_frame = pd.DataFrame({x_col: thresholds})
            drill_columns = [x_col]
            if color_col:
                threshold_frame[color_col] = group
                drill_columns.append(color_col)
            traces.append(
                LineTraceConfig(
                    name=name,
                    x=thresholds.astype(float).tolist(),
                    y=ordinates.astype(float).tolist(),
                    color=color,
                    line_shape="hv",
                    show_markers=show_markers,
                    marker_size=marker_size,
                    legendgroup=name,
                    custom_data={
                        "drilldown": build_drill_down_payload(threshold_frame, drill_columns)
                    },
                )
            )
        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Return the optional color grouping column."""
        color = config.get("color")
        return str(color) if color else None


__all__ = ["EcdfPlot"]
