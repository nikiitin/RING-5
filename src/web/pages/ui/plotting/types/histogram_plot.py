"""Histogram plot implementation."""

from typing import cast, override

import math

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.common.distribution_metadata import inspect_distribution_layouts
from src.core.models.native_distribution_layout import (
    NativeDistributionLayout,
    OpaqueDistributionLayout,
)
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config import histogram_config
from src.core.models.plot_config import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import build_drill_down_payload
from src.web.pages.ui.plotting.utils.ordering import order_with_overrides
from src.web.pages.ui.plotting.utils.histogram_bins import (
    HistogramBin,
    aggregate_histogram_observations,
    rebin_histogram,
    sum_histogram_counts,
    histogram_mass_ratio,
    cumulative_histogram_counts,
)


class HistogramPlot(BasePlot):
    """Render native storage-cell mass or explicit generic intervals through neutral bars."""

    def __init__(self, plot_id: int, name: str) -> None:
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
            ValueError: Selection, frequency data, arithmetic or the requested view is invalid.
        """
        # [impl->req~ring5.figure.histogram-controls~2]
        # [impl->req~ring5.plot.histogram~2]
        histogram_var = config.get("histogram_variable")
        if not histogram_var:
            raise ValueError("No histogram variable specified")

        layouts = inspect_distribution_layouts(data)
        layout = layouts.get(str(histogram_var))
        if type(layout) is OpaqueDistributionLayout:
            raise ValueError(
                "Native Distribution labels alone do not declare storage-cell geometry; "
                "select Distribution output with an explicit full grid and zero_policy."
            )
        native = type(layout) is NativeDistributionLayout
        if native:
            assert isinstance(layout, NativeDistributionLayout)
            if config.get("bucket_size") is not None:
                raise ValueError(
                    "Native Distribution storage cells do not support continuous rebinning."
                )
            frequencies = [column for column in layout.columns if column.role != "summary"]
            columns = [column.column for column in frequencies]
            labels = [column.source_label for column in frequencies]
        else:
            columns = [
                col
                for col in data.columns
                if col.startswith(f"{histogram_var}..") and not col.endswith(".sd")
            ]
            if not columns:
                raise ValueError(f"No histogram bucket columns found for variable: {histogram_var}")
            if any(
                column.column in columns
                for declared in layouts.values()
                for column in declared.columns
            ):
                raise ValueError(
                    "Histogram prefix overlaps declared Native Distribution bindings; "
                    "select the layout's logical variable instead."
                )
            labels = [column.split("..", 1)[1] for column in columns]
        group_by = config.get("group_by")
        if group_by and group_by not in data.columns:
            raise ValueError(f"Histogram grouping column is missing: {group_by!r}.")
        groups = (
            order_with_overrides(data[str(group_by)].dropna().unique(), config.get("legend_order"))
            if group_by
            else [""]
        )
        if native and not groups:
            raise ValueError("Native Distribution requires at least one observed selected group.")
        traces: list[BarTraceConfig] = []
        display_bins: list[HistogramBin] = []
        centers: list[float] = []
        for group in groups:
            source = data[data[str(group_by)].astype(str) == str(group)] if group_by else data
            numeric = source[columns].apply(pd.to_numeric, errors="raise")
            rows = numeric.to_numpy(dtype=float, na_value=float("nan")).tolist()
            if native:
                if not rows or any(
                    not math.isfinite(value) or value < 0 for row in rows for value in row
                ):
                    raise ValueError(
                        "Every selected Native Distribution cell must be measured, finite "
                        "and nonnegative."
                    )
                values = [
                    sum_histogram_counts(row[index] for row in rows)
                    for index in range(len(columns))
                ]
                widths: list[float | None] = [1.0] * len(columns)
                centers = [float(index) for index in range(len(columns))]
                display_labels = labels
                fallback_width = 1.0
            else:
                observed_bins, values = aggregate_histogram_observations(labels, rows)
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
                        bucket.lower + (bucket.upper - bucket.lower) / 2
                        if bucket.lower is not None and bucket.upper is not None
                        else (
                            bucket.lower + fallback_width / 2
                            if bucket.lower is not None
                            else cast(float, bucket.upper) - fallback_width / 2
                        )
                    )
                    for bucket in display_bins
                ]
                if any(not math.isfinite(center) for center in centers):
                    raise ValueError("Histogram display positions must remain finite.")
                display_labels = [
                    bucket.label or str(center)
                    for bucket, center in zip(display_bins, centers, strict=True)
                ]
            drilldown = (
                build_drill_down_payload(source.head(1), [str(group_by)]) if group_by else [{}]
            )
            traces.append(
                BarTraceConfig(
                    name=str(group) if group_by else str(histogram_var),
                    x=[label for label in display_labels],
                    x_positions=centers,
                    y=self._normalize_values(values, config, widths, native=native),
                    bar_width=[width if width is not None else fallback_width for width in widths],
                    opacity=0.7 if group_by else 1.0,
                    border_width=1.0,
                    border_color="white",
                    custom_data={
                        "drilldown": [drilldown[0] if drilldown else {} for _ in display_labels]
                    },
                )
            )
        ticks: dict[str, list[float] | list[str] | list[bool]] | None = None
        if native:
            ticks = {"vals": centers, "text": labels}
        elif any(bucket.width is None for bucket in display_bins):
            ticks = {"vals": centers, "text": display_labels}
        return TraceBuildResult(
            traces=traces,
            barmode="overlay" if group_by else "relative",
            custom_x_ticks=ticks,
            default_x_axis_label="Native bucket" if native else None,
        )

    def _normalize_values(
        self,
        values: list[float],
        config: PlotConfig,
        widths: list[float | None] | None = None,
        *,
        native: bool = False,
    ) -> list[float]:
        """Normalize finite cell mass; cumulative density is a CDF.

        Raw count does not require a representable total. Normalized views need
        positive finite mass, and native storage cells do not define density.

        Raises:
            ValueError: Density has no width or an output/required total is invalid.
        """
        # [impl->req~ring5.figure.histogram-cumulative~2]
        normalization = config.get("normalization", "count")
        cumulative = bool(config.get("cumulative", False))
        if normalization == "density" and not cumulative:
            if native:
                raise ValueError(
                    "Native Distribution storage cells do not define continuous density."
                )
            if (
                widths is None
                or len(widths) != len(values)
                or any(width is None or not math.isfinite(width) or width <= 0 for width in widths)
            ):
                raise ValueError(
                    "Histogram density requires finite positive bucket widths; "
                    "tails have unknown widths."
                )
        if normalization in {"probability", "percent", "density"}:
            total = sum_histogram_counts(values)
            if total <= 0:
                raise ValueError("Histogram normalization requires finite positive selected mass.")
            if normalization == "density" and not cumulative:
                assert widths is not None
                return [
                    histogram_mass_ratio(value, 1.0, total, cast(float, width))
                    for value, width in zip(values, widths, strict=True)
                ]
            scale = 100.0 if normalization == "percent" else 1.0
            values = [histogram_mass_ratio(value, scale, total) for value in values]
        if cumulative:
            return cumulative_histogram_counts(values)
        return values
