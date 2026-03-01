"""Heatmap plot implementation.

Builds wide-format heatmaps where:
- X-axis = configuration column (e.g. config_abbrev)
- Y-axis = metric names (selected numeric columns)
- Cell value = aggregated metric value

Optionally generates one heatmap per facet value (e.g. benchmark_name).
"""

from collections.abc import Callable
from typing import Literal, cast, override

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.web.components.plotting.config import heatmap_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot

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


class HeatmapPlot(BasePlot):
    """Heatmap plot — 2D grid of a statistic across two config axes."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "heatmap")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for heatmap plot."""
        return heatmap_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Produce one or more heatmap traces from data and config."""
        x_col: str = config["x"]
        metric_columns: list[str] = [
            str(metric)
            for metric in config.get("metric_columns", [])
            if isinstance(metric, str) and metric in data.columns
        ]
        facet_col_raw = config.get("facet_col")
        facet_col: str | None = str(facet_col_raw) if facet_col_raw else None
        aggregation: str = config.get("aggregation", "mean")
        colorscale: str = config.get("colorscale", "Viridis")
        reverse_cs: bool = config.get("reverse_colorscale", False)
        show_values: bool = config.get("show_cell_values", True)
        agg_func = cast(_AGG_FUNCS, aggregation)
        if not metric_columns:
            return TraceBuildResult(traces=[])

        # Work on a copy
        df = data.copy()

        # Apply filters
        x_filter: list[str] | None = config.get("x_filter")
        facet_filter: list[str] | None = config.get("facet_filter")

        df[x_col] = df[x_col].astype(str)
        if facet_col and facet_col in df.columns:
            df[facet_col] = df[facet_col].astype(str)

        if x_filter:
            df = df[df[x_col].isin(x_filter)]
        if facet_col and facet_filter:
            df = df[df[facet_col].isin(facet_filter)]

        if df.empty:
            return TraceBuildResult(traces=[])

        if reverse_cs:
            colorscale = colorscale + "_r"

        x_labels_internal: list[str] = sorted(df[x_col].dropna().astype(str).unique().tolist())
        if config.get("xaxis_order"):
            ordered_x = [str(x) for x in config["xaxis_order"]]
            x_labels_internal = [x for x in ordered_x if x in x_labels_internal] + [
                x for x in x_labels_internal if x not in ordered_x
            ]

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

        for facet_value, group_df in grouped_frames:
            z_values: list[list[float | None]] = []
            text_values: list[list[str]] | None = [] if show_values else None

            for metric in metric_columns:
                row: list[float | None] = []
                text_row: list[str] = []

                for x_value in x_labels_internal:
                    cell_series = group_df.loc[group_df[x_col] == x_value, metric]
                    cell_val = _aggregate_series(cell_series, agg_func)
                    row.append(cell_val)

                    if show_values:
                        text_row.append("" if cell_val is None else f"{cell_val:.4g}")

                z_values.append(row)
                if text_values is not None:
                    text_values.append(text_row)

            trace_name = f"{facet_col}={facet_value}" if facet_col and facet_value else "Heatmap"
            traces.append(
                HeatmapTraceConfig(
                    name=trace_name,
                    col_labels=display_x_labels,
                    row_labels=display_metric_labels,
                    z=z_values,
                    colorscale=colorscale,
                    show_values=show_values,
                    text=text_values,
                )
            )

        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Heatmap has no legend column — color is the z-value."""
        return None
