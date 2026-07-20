"""Heatmap plot implementation.

Builds wide-format heatmaps where:
- X-axis = configuration column (e.g. config_abbrev)
- Y-axis = metric names (selected numeric columns)
- Cell value = aggregated metric value

Optionally generates one heatmap per facet value (e.g. benchmark_name).
"""

from collections.abc import Callable
from typing import Any, Literal, cast, override

import pandas as pd
import plotly.graph_objects as go

from src.core.common.safe_format import safe_format_number
from src.core.services.visualization.palette_service import resolve_palette
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.web.components.plotting.config import heatmap_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import prepare_categorical_data

_AGG_FUNCS = Literal["mean", "sum", "min", "max", "median", "first"]


def _aggregate_series(values: pd.Series, agg_func: _AGG_FUNCS) -> float | None:
    """Aggregate numeric series according to configured function."""
    cleaned = values.dropna()
    if cleaned.empty:
        return None

    agg_map: dict[_AGG_FUNCS, Callable[[pd.Series], float]] = {
        "mean": lambda s: float(s.mean()),
        "sum": lambda s: float(s.sum()),
        "min": lambda s: float(s.min()),
        "max": lambda s: float(s.max()),
        "median": lambda s: float(s.median()),
        "first": lambda s: float(s.iloc[0]),
    }
    return agg_map[agg_func](cleaned)


def _format_value(val: float, fmt: str) -> str:
    """Format a numeric value using a Python format spec, with fallback."""
    return safe_format_number(val, fmt, default=".4g")


def _compute_total(values: list[float], agg: str) -> float | None:
    """Compute an aggregate total from a list of values."""
    if not values:
        return None
    if agg == "sum":
        return sum(values)
    if agg == "mean":
        return sum(values) / len(values)
    if agg == "max":
        return max(values)
    if agg == "min":
        return min(values)
    return None


def _palette_to_colorscale(
    colors: list[str],
) -> list[list[str | float]]:
    """Convert a list of hex colours to Plotly-format colorscale pairs.

    Each colour is evenly spaced across [0.0, 1.0].
    """
    n = len(colors)
    if n == 0:
        return [[0.0, "#000000"], [1.0, "#000000"]]
    if n == 1:
        return [[0.0, colors[0]], [1.0, colors[0]]]
    return [[i / (n - 1), c] for i, c in enumerate(colors)]


class HeatmapPlot(BasePlot):
    """Heatmap plot — 2D grid of a statistic across two config axes."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "heatmap")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for heatmap plot."""
        return heatmap_config.render(data, saved_config, self.plot_id)

    @override
    def apply_common_layout(self, fig: go.Figure, config: PlotConfig) -> go.Figure:
        """Apply common layout, then restrict X-axis categories to filtered values.

        The ordering settings provide ``xaxis_order`` with ALL unique X values
        from the unfiltered data.  The Plotly connector converts that into
        ``xaxis.categoryarray``, which forces Plotly to display categories that
        the heatmap trace does not contain — producing empty ticks and
        displacing the rendered cells.

        After the base layout is applied we override ``categoryarray`` with
        only the col_labels actually present in the heatmap traces.
        """
        fig = super().apply_common_layout(fig, config)
        if self.last_traces and self.last_traces.traces:
            first = self.last_traces.traces[0]
            if isinstance(first, HeatmapTraceConfig) and first.col_labels:
                fig.update_xaxes(categoryorder="array", categoryarray=first.col_labels)
        return fig

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Produce one or more heatmap traces from data and config."""
        # [impl->req~ring5.figure.heatmap-controls~1]
        # [impl->req~ring5.figure.heatmap-summary-controls~1]
        # [impl->req~ring5.plot.heatmap~1]
        x_col: str = config["x"]
        metric_columns: list[str] = [
            str(metric)
            for metric in config.get("metric_columns", [])
            if isinstance(metric, str) and metric in data.columns
        ]
        facet_col_raw = config.get("facet_col")
        facet_col: str | None = str(facet_col_raw) if facet_col_raw else None
        aggregation: str = config.get("aggregation", "mean")
        reverse_cs: bool = config.get("reverse_colorscale", False)

        # Resolve colorscale from the shared color palette.
        # Backward compat: if config carries a legacy string colorscale
        # (e.g. "Viridis") and no palette, keep the string.
        colorscale: str | list[list[str | float]]
        legacy_cs = config.get("colorscale")
        palette_name = config.get("color_palette")
        if palette_name:
            palette_colors = resolve_palette(palette_name)
            colorscale = _palette_to_colorscale(palette_colors)
        elif isinstance(legacy_cs, str) and legacy_cs:
            colorscale = legacy_cs
        else:
            palette_colors = resolve_palette("wong")
            colorscale = _palette_to_colorscale(palette_colors)

        if reverse_cs:
            if isinstance(colorscale, list):
                colorscale = [[1.0 - float(pos), color] for pos, color in reversed(colorscale)]
            else:
                colorscale = colorscale + "_r"

        # Backward compat: old configs used "show_cell_values", new uses "show_values"
        show_values: bool = bool(config.get("show_values", config.get("show_cell_values", True)))
        text_format: str = config.get("text_format", ".4g")
        text_color_mode: str = config.get("text_color_mode", "contrast")
        text_font_size: int = int(config.get("text_font_size", 10))
        text_color: str = config.get("text_color", "#000000")
        text_display_logic: str = config.get("text_display_logic", "all")
        text_threshold: float = float(config.get("text_threshold", 0.0))
        agg_func = cast(_AGG_FUNCS, aggregation)
        if not metric_columns:
            return TraceBuildResult(traces=[])

        # Work on a copy with categorical x / facet columns cast to string
        df = prepare_categorical_data(data, [x_col, facet_col])

        # Apply filters
        x_filter: list[str] | None = config.get("x_filter")
        facet_filter: list[str] | None = config.get("group_filter")

        if x_filter:
            df = df[df[x_col].isin(x_filter)]
        if facet_col and facet_filter:
            df = df[df[facet_col].isin(facet_filter)]

        if df.empty:
            return TraceBuildResult(traces=[])

        # Shared ordering rule: explicit xaxis_order first, then remaining sorted.
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            order_with_overrides,
        )

        x_labels_internal: list[str] = order_with_overrides(
            df[x_col].dropna().astype(str).unique(), config.get("xaxis_order")
        )

        x_renames = config.get("xaxis_labels", {})
        display_x_labels = [str(x_renames.get(x, x)) for x in x_labels_internal]

        metric_renames = config.get("metric_labels", {})
        display_metric_labels = [str(metric_renames.get(m, m)) for m in metric_columns]

        traces: list[HeatmapTraceConfig] = []

        grouped_frames: list[tuple[str, pd.DataFrame]]
        if facet_col and facet_col in df.columns:
            grouped_frames = [
                (str(facet_value), group_df.copy())
                for facet_value, group_df in df.groupby(facet_col, sort=True)
            ]
        else:
            grouped_frames = [("", df)]

        # Apply custom facet ordering
        facet_order: list[str] | None = config.get("facet_order")
        if facet_order and len(grouped_frames) > 1:
            order_map = {v: i for i, v in enumerate(facet_order)}
            grouped_frames.sort(key=lambda pair: order_map.get(pair[0], len(order_map)))

        facet_labels: dict[str, str] = config.get("facet_labels", {}) or {}

        for facet_value, group_df in grouped_frames:
            z_values: list[list[float | None]] = []
            text_values: list[list[str]] | None = [] if show_values else None
            drilldown_values: list[list[dict[str, Any]]] = []

            for metric in metric_columns:
                row: list[float | None] = []
                text_row: list[str] = []
                drilldown_row: list[dict[str, Any]] = []

                for x_value in x_labels_internal:
                    cell_series = group_df.loc[group_df[x_col] == x_value, metric]
                    cell_val = _aggregate_series(cell_series, agg_func)
                    row.append(cell_val)
                    filters: dict[str, Any] = {x_col: x_value}
                    if facet_col:
                        filters[facet_col] = facet_value
                    drilldown_row.append(filters)

                    if show_values:
                        cell_text = ""
                        if cell_val is not None:
                            # Apply threshold logic
                            show_cell = True
                            if text_display_logic == "above_threshold":
                                show_cell = cell_val > text_threshold
                            elif text_display_logic == "below_threshold":
                                show_cell = cell_val < text_threshold

                            if show_cell:
                                cell_text = _format_value(cell_val, text_format)
                        text_row.append(cell_text)

                z_values.append(row)
                drilldown_values.append(drilldown_row)
                if text_values is not None:
                    text_values.append(text_row)

            # Totals: append extra row or column to the z-matrix
            facet_display_x = list(display_x_labels)
            facet_display_metrics = list(display_metric_labels)
            if config.get("show_totals"):
                totals_pos = config.get("totals_position", "right")
                totals_agg = config.get("totals_aggregation", "mean")
                if totals_pos == "right":
                    for row_idx, z_row in enumerate(z_values):
                        non_null = [v for v in z_row if v is not None]
                        total = _compute_total(non_null, totals_agg)
                        z_row.append(total)
                        drilldown_values[row_idx].append(
                            {facet_col: facet_value} if facet_col else {}
                        )
                        if text_values is not None:
                            text_values[row_idx].append(
                                "" if total is None else _format_value(total, text_format)
                            )
                    facet_display_x.append("Total")
                elif totals_pos == "top":
                    total_row: list[float | None] = []
                    total_text: list[str] = []
                    for col_idx in range(len(facet_display_x)):
                        col_vals: list[float] = [
                            z_values[r][col_idx]  # type: ignore[misc]
                            for r in range(len(z_values))
                            if z_values[r][col_idx] is not None
                        ]
                        total = _compute_total(col_vals, totals_agg)
                        total_row.append(total)
                        total_text.append(
                            "" if total is None else _format_value(total, text_format)
                        )
                    z_values.insert(0, total_row)
                    total_drilldown: list[dict[str, Any]] = []
                    for x_value in x_labels_internal:
                        filters = {x_col: x_value}
                        if facet_col:
                            filters[facet_col] = facet_value
                        total_drilldown.append(filters)
                    drilldown_values.insert(0, total_drilldown)
                    if text_values is not None:
                        text_values.insert(0, total_text)
                    facet_display_metrics.insert(0, "Total")

            display_facet = facet_labels.get(facet_value, facet_value)
            if facet_col and display_facet:
                trace_name = display_facet
            else:
                trace_name = "Heatmap"
            traces.append(
                HeatmapTraceConfig(
                    name=trace_name,
                    col_labels=facet_display_x,
                    row_labels=facet_display_metrics,
                    z=z_values,
                    colorscale=colorscale,
                    show_values=show_values,
                    text=text_values,
                    text_font_size=text_font_size,
                    text_color_mode=text_color_mode,
                    text_color=text_color,
                    totals_position=(
                        config.get("totals_position", "") if config.get("show_totals") else ""
                    ),
                    totals_count=1 if config.get("show_totals") else 0,
                    custom_data={"drilldown": drilldown_values},
                )
            )

        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Heatmap has no legend column — color is the z-value."""
        return None
