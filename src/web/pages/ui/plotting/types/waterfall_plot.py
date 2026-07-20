"""Engine-independent waterfall chart implementation."""

from __future__ import annotations

from typing import Any, Literal, override

import numpy as np
import pandas as pd

from src.core.common.safe_format import safe_format_number
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import WaterfallTraceConfig
from src.web.components.plotting.config import waterfall_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot

WaterfallKind = Literal["relative", "absolute", "subtotal", "total"]
WaterfallMeasure = Literal["relative", "absolute", "total"]


def _ordered_values(series: pd.Series, configured: object = None) -> list[Any]:
    """Keep source order unless the user supplied an explicit category order."""
    available = list(series.drop_duplicates())
    if not isinstance(configured, list):
        return available
    by_label = {str(value): value for value in available}
    labels = [str(label) for label in configured]
    ordered = [by_label[label] for label in labels if label in by_label]
    return ordered + [value for value in available if str(value) not in labels]


def _mask(series: pd.Series, value: Any) -> pd.Series:
    return series.isna() if pd.isna(value) else series == value


def _label_set(value: object, field_name: str) -> set[str]:
    if value is None:
        return set()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"Waterfall {field_name} must be a list of category labels.")
    return set(value)


class WaterfallPlot(BasePlot):
    """Explain how ordered contributions build or reset a running total."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "waterfall")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render waterfall mappings, bar meanings, connectors, labels, and colors."""
        return waterfall_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        # [impl->req~ring5.plot.waterfall~1]
        """Resolve every bar to an explicit kind, start, and end before rendering."""
        x_col, y_col = str(config["x"]), str(config["y"])
        if x_col not in data or y_col not in data:
            raise ValueError("Waterfall chart columns must exist in the processed data.")

        categories = _ordered_values(data[x_col], config.get("xaxis_order"))
        absolute_labels = _label_set(config.get("waterfall_absolute"), "absolute steps")
        subtotal_labels = _label_set(config.get("waterfall_subtotals"), "subtotals")
        overlap = absolute_labels & subtotal_labels
        if overlap:
            raise ValueError("A waterfall category cannot be both absolute and subtotal.")

        bar_width = float(config.get("waterfall_bar_width", 0.7))
        connector_width = float(config.get("waterfall_connector_width", 1.0))
        opacity = float(config.get("waterfall_opacity", 0.9))
        if not 0.1 <= bar_width <= 1:
            raise ValueError("Waterfall bar width must be between 0.1 and 1.")
        if not 0.25 <= connector_width <= 10:
            raise ValueError("Waterfall connector width must be between 0.25 and 10.")
        if not 0.05 <= opacity <= 1:
            raise ValueError("Waterfall opacity must be between 0.05 and 1.")

        labels: list[str] = []
        values: list[float] = []
        measures: list[WaterfallMeasure] = []
        kinds: list[WaterfallKind] = []
        starts: list[float] = []
        ends: list[float] = []
        input_rows: list[pd.DataFrame] = []
        current = 0.0

        numeric = pd.to_numeric(data[y_col], errors="coerce")
        for category in categories:
            category_label = str(category)
            matching_mask = _mask(data[x_col], category)
            matching = numeric.loc[matching_mask]
            if category_label in subtotal_labels:
                start, end, value = 0.0, current, 0.0
                measure: WaterfallMeasure = "total"
                kind: WaterfallKind = "subtotal"
            else:
                if not matching.notna().any():
                    raise ValueError(
                        f"Waterfall category {category_label!r} has no numeric values."
                    )
                value = float(matching.mean())
                if not np.isfinite(value):
                    raise ValueError("Waterfall values must be finite.")
                if category_label in absolute_labels:
                    start, end, current = 0.0, value, value
                    measure, kind = "absolute", "absolute"
                else:
                    start, end = current, current + value
                    current = end
                    measure, kind = "relative", "relative"
            labels.append(category_label)
            values.append(value)
            measures.append(measure)
            kinds.append(kind)
            starts.append(start)
            ends.append(end)
            input_rows.append(data.loc[matching_mask])

        if bool(config.get("waterfall_final_total", True)):
            total_label = str(config.get("waterfall_total_label", "Total")).strip()
            if not total_label:
                raise ValueError("Waterfall total label cannot be empty.")
            labels.append(total_label)
            values.append(0.0)
            measures.append("total")
            kinds.append("total")
            starts.append(0.0)
            ends.append(current)
            input_rows.append(data)

        number_format = str(config.get("waterfall_number_format", ".4g"))
        value_labels = [
            safe_format_number(
                values[index] if kind == "relative" else ends[index],
                number_format,
                default=".4g",
            )
            for index, kind in enumerate(kinds)
        ]
        drilldown = [
            {x_col: label} if kind in ("relative", "absolute") else {}
            for label, kind in zip(labels, kinds)
        ]
        trace = WaterfallTraceConfig(
            name=y_col,
            categories=labels,
            values=values,
            measures=measures,
            kinds=kinds,
            starts=starts,
            ends=ends,
            connector_visible=bool(config.get("waterfall_connectors", True)),
            connector_color=str(config.get("waterfall_connector_color", "#666666")),
            connector_width=connector_width,
            increasing_color=str(config.get("waterfall_increasing_color", "#2ca02c")),
            decreasing_color=str(config.get("waterfall_decreasing_color", "#d62728")),
            total_color=str(config.get("waterfall_total_color", "#4c78a8")),
            bar_width=bar_width,
            opacity=opacity,
            show_values=bool(config.get("waterfall_show_values", True)),
            value_labels=value_labels,
            show_in_legend=False,
            custom_data={
                "drilldown": drilldown,
                "source_row_counts": [len(rows) for rows in input_rows],
            },
        )
        return TraceBuildResult(traces=[trace])

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Waterfall bar meaning is encoded by fixed semantic colors."""
        return None


__all__ = ["WaterfallPlot"]
