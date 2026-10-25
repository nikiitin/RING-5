"""Histogram plot implementation."""

from typing import cast, override

import math

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config import histogram_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import build_drill_down_payload
from src.web.pages.ui.plotting.utils.ordering import order_with_overrides
from src.web.pages.ui.plotting.utils.histogram_bins import (
    HistogramBin,
    aggregate_histogram_observations,
    rebin_histogram,
)


class HistogramPlot(BasePlot):
    """
    Histogram plot for visualizing distribution data.

    Supports:
    - Single or multiple histograms (grouped by categorical variable)
    - Configurable bucket sizes (rebinning)
    - Multiple normalization modes (count, probability, percent)
    - Histogram variables with bucket ranges
    """

    def __init__(self, plot_id: int, name: str):
        """
        Initialize histogram plot.

        Args:
            plot_id: Unique identifier for the plot
            name: Display name for the plot
        """
        super().__init__(plot_id, name, "histogram")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for histogram plot."""
        return histogram_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """
        Create histogram trace configurations.

        Args:
            data: The data to plot
            config: Configuration dictionary

        Returns:
            TraceBuildResult with BarTraceConfig traces and barmode

        Raises:
            ValueError: If histogram variable not found in data
        """
        # [impl->req~ring5.figure.histogram-controls~1]
        # [impl->req~ring5.plot.histogram~1]
        histogram_var = config.get("histogram_variable")
        if not histogram_var:
            raise ValueError("No histogram variable specified")

        # Extract histogram bucket columns
        bucket_cols = [
            col
            for col in data.columns
            if col.startswith(f"{histogram_var}..") and not col.endswith(".sd")
        ]

        if not bucket_cols:
            raise ValueError(f"No histogram bucket columns found for variable: {histogram_var}")

        columns = bucket_cols
        labels = [column.split("..", 1)[1] for column in columns]
        group_by = config.get("group_by")
        if group_by and group_by not in data.columns:
            raise ValueError(f"Histogram grouping column is missing: {group_by!r}.")
        groups = (
            order_with_overrides(data[str(group_by)].dropna().unique(), config.get("legend_order"))
            if group_by
            else [""]
        )
        traces: list[BarTraceConfig] = []
        display_bins: list[HistogramBin] = []
        centers: list[float] = []
        for group in groups:
            source = data[data[str(group_by)].astype(str) == str(group)] if group_by else data
            numeric = source[columns].apply(pd.to_numeric, errors="raise")
            observed_bins, values = aggregate_histogram_observations(
                labels, numeric.to_numpy(dtype=float, na_value=float("nan")).tolist()
            )
            requested_width = config.get("bucket_size")
            display_bins, values = rebin_histogram(
                observed_bins,
                values,
                float(requested_width) if requested_width is not None else None,
            )
            widths = [bucket.width for bucket in display_bins]
            fallback_width = next((width for width in widths if width is not None), 1.0)
            centers = [
                (
                    (bucket.lower + bucket.upper) / 2
                    if bucket.lower is not None and bucket.upper is not None
                    else (
                        bucket.lower + fallback_width / 2
                        if bucket.lower is not None
                        else cast(float, bucket.upper) - fallback_width / 2
                    )
                )
                for bucket in display_bins
            ]
            drilldown = (
                build_drill_down_payload(source.head(1), [str(group_by)]) if group_by else [{}]
            )
            traces.append(
                BarTraceConfig(
                    name=str(group) if group_by else str(histogram_var),
                    x=[
                        bucket.label or str(center)
                        for bucket, center in zip(display_bins, centers, strict=True)
                    ],
                    x_positions=centers,
                    y=self._normalize_values(values, config, widths),
                    bar_width=[width if width is not None else fallback_width for width in widths],
                    opacity=0.7 if group_by else 1.0,
                    border_width=1.0,
                    border_color="white",
                    custom_data={
                        "drilldown": [drilldown[0] if drilldown else {} for _ in display_bins]
                    },
                )
            )
        ticks: dict[str, list[float] | list[str] | list[bool]] | None = None
        if any(bucket.width is None for bucket in display_bins):
            ticks = {
                "vals": centers,
                "text": [
                    bucket.label or str(center)
                    for bucket, center in zip(display_bins, centers, strict=True)
                ],
            }
        return TraceBuildResult(
            traces=traces, barmode="overlay" if group_by else "relative", custom_x_ticks=ticks
        )

    # ========== Helper Methods ==========

    def _detect_histogram_variables(self, data: pd.DataFrame) -> list[str]:
        """
        Detect histogram variables from DataFrame columns.

        Args:
            data: DataFrame to analyze

        Returns:
            List of histogram variable names (base names without bucket suffixes)
        """
        histogram_vars: set[str] = set()

        for col in data.columns:
            if ".." in col and not col.endswith(".sd"):
                # Extract base variable name (before "..")
                base_name = col.split("..")[0]
                histogram_vars.add(base_name)

        return sorted(list(histogram_vars))

    def _normalize_values(
        self,
        values: list[float],
        config: PlotConfig,
        widths: list[float | None] | None = None,
    ) -> list[float]:
        """Normalize counts using actual widths; cumulative density is a CDF.

        Raises:
            ValueError: If density is requested for an unbounded interval.
        """
        # [impl->req~ring5.figure.histogram-cumulative~1]
        normalization = config.get("normalization", "count")
        cumulative = bool(config.get("cumulative", False))
        total = math.fsum(values)
        if normalization == "density" and not cumulative and (widths is None or None in widths):
            raise ValueError(
                "Histogram density requires finite bucket bounds; "
                "overflow and underflow have unknown widths."
            )
        if not total:
            return values
        if normalization in {"probability", "percent", "density"}:
            values = [value / total for value in values]
        if normalization == "percent":
            values = [value * 100 for value in values]
        if cumulative:
            running = 0.0
            result = []
            for value in values:
                running += value
                result.append(running)
            return result
        if normalization == "density":
            assert widths is not None
            return [value / cast(float, width) for value, width in zip(values, widths, strict=True)]
        return values
