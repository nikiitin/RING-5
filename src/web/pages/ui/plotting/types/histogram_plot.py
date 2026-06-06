"""Histogram plot implementation."""

from typing import Any, override

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config import histogram_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot


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

        # Parse bucket ranges and prepare data
        bucket_data = self._extract_bucket_data(data, bucket_cols, config)

        # Build traces
        if config.get("group_by"):
            # Multiple histograms grouped by categorical variable
            traces = self._add_grouped_histograms(bucket_data, config)
            barmode = "overlay"
        else:
            # Single histogram
            traces = self._add_single_histogram(bucket_data, config)
            barmode = "relative"

        return TraceBuildResult(
            traces=traces,
            barmode=barmode,
        )

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """
        Get legend column for histogram plot.

        Args:
            config: Plot configuration

        Returns:
            Column name for legend grouping, or None
        """
        result = config.get("group_by")
        return str(result) if result is not None else None

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

    def _extract_bucket_data(
        self,
        data: pd.DataFrame,
        bucket_cols: list[str],
        config: PlotConfig,
    ) -> dict[str, Any]:
        """
        Extract and process bucket data from DataFrame.

        gem5 histogram buckets are flattened into columns named
        ``"{var}..{start}-{end}"`` (e.g. ``latency..0-99``, ``latency..100-199``).
        This parses ``start``/``end`` out of each column's ``..start-end`` suffix
        and pairs them with the row values. This per-bin reshape is intentionally
        kept here (not in the shaper pipeline): it is histogram-specific view
        prep that depends on the gem5 column-naming convention, not a reusable
        data transform (deferred B5 — documented rather than extracted).

        Args:
            data: Source DataFrame
            bucket_cols: List of bucket column names (``{var}..{start}-{end}``)
            config: Plot configuration

        Returns:
            Dictionary with processed bucket data
        """
        # Parse bucket ranges
        buckets: list[tuple[float, float]] = []
        for col in bucket_cols:
            bucket_part = col.split("..")[1]
            if "-" in bucket_part:
                parts = bucket_part.split("-")
                try:
                    start = float(parts[0])
                    end = float(parts[1])
                    buckets.append((start, end))
                except ValueError:
                    # Skip malformed bucket names
                    continue

        if not buckets:
            raise ValueError("No valid bucket ranges found")

        # Sort buckets by start value
        buckets.sort(key=lambda x: x[0])

        # Extract counts/values for each bucket
        group_by = config.get("group_by")

        if group_by and group_by in data.columns:
            # Group data
            groups = data[group_by].unique()
            result: dict[str, Any] = {
                "buckets": buckets,
                "groups": groups,
                "data": {},
            }

            for group in groups:
                group_data = data[data[group_by] == group]
                values = [
                    group_data[col].sum() if col in group_data.columns else 0 for col in bucket_cols
                ]
                result["data"][str(group)] = values

            return result
        else:
            # Single histogram
            values = [data[col].sum() if col in data.columns else 0 for col in bucket_cols]
            return {"buckets": buckets, "groups": None, "data": {"": values}}

    def _add_single_histogram(
        self,
        bucket_data: dict[str, Any],
        config: PlotConfig,
    ) -> list[BarTraceConfig]:
        """
        Build a single histogram trace.

        Args:
            bucket_data: Processed bucket data
            config: Plot configuration

        Returns:
            List containing a single BarTraceConfig
        """
        buckets = bucket_data["buckets"]
        values = bucket_data["data"][""]

        # Create bin edges and centers
        x_centers = [(b[0] + b[1]) / 2 for b in buckets]

        # Apply normalization
        values_normalized = self._normalize_values(values, config)

        trace = BarTraceConfig(
            name=config.get("histogram_variable", "Histogram"),
            x=[str(c) for c in x_centers],
            y=values_normalized,
            x_positions=x_centers,
            border_width=1.0,
            border_color="white",
        )
        return [trace]

    def _add_grouped_histograms(
        self,
        bucket_data: dict[str, Any],
        config: PlotConfig,
    ) -> list[BarTraceConfig]:
        """
        Build multiple grouped histogram traces.

        Args:
            bucket_data: Processed bucket data
            config: Plot configuration

        Returns:
            List of BarTraceConfig, one per group
        """
        buckets = bucket_data["buckets"]
        groups = bucket_data["groups"]

        x_centers = [(b[0] + b[1]) / 2 for b in buckets]
        traces: list[BarTraceConfig] = []

        for group in groups:
            values = bucket_data["data"].get(str(group), [])
            values_normalized = self._normalize_values(values, config)

            trace = BarTraceConfig(
                name=str(group),
                x=[str(c) for c in x_centers],
                y=values_normalized,
                x_positions=x_centers,
                opacity=0.7,
                border_width=1.0,
                border_color="white",
            )
            traces.append(trace)

        return traces

    def _normalize_values(self, values: list[float], config: PlotConfig) -> list[float]:
        """
        Normalize histogram values according to config.

        Args:
            values: Raw histogram counts
            config: Plot configuration with normalization mode

        Returns:
            Normalized values
        """
        normalization = config.get("normalization", "count")
        cumulative = config.get("cumulative", False)

        # Convert to list of floats
        vals = [float(v) for v in values]

        # Apply normalization
        total = sum(vals)
        if total == 0:
            return vals

        if normalization == "probability":
            vals = [v / total for v in vals]
        elif normalization == "percent":
            vals = [(v / total) * 100 for v in vals]
        elif normalization == "density":
            # Density = count / (total * bin_width)
            # Assuming uniform bin width for simplicity
            bin_width = config.get("bucket_size", 1)
            vals = [v / (total * bin_width) for v in vals]

        # Apply cumulative if requested
        if cumulative:
            cumulative_vals = []
            cum_sum = 0.0
            for v in vals:
                cum_sum += v
                cumulative_vals.append(cum_sum)
            vals = cumulative_vals

        return vals
