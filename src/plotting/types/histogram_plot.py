"""Histogram plot implementation."""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.plotting.base_plot import BasePlot


class HistogramPlot(BasePlot):
    """
    Histogram plot for visualizing distribution data.

    Supports:
    - Single or multiple histograms (grouped by categorical variable)
    - Configurable bucket sizes (rebinning)
    - Multiple normalization modes (count, probability, percent)
    - Histogram variables from gem5 with bucket ranges
    """

    def __init__(self, plot_id: int, name: str):
        """
        Initialize histogram plot.

        Args:
            plot_id: Unique identifier for the plot
            name: Display name for the plot
        """
        super().__init__(plot_id, name, "histogram")

    def render_config_ui(
        self, data: pd.DataFrame, saved_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Render configuration UI for histogram plot.

        Args:
            data: The processed data to plot
            saved_config: Previously saved configuration

        Returns:
            Current configuration dictionary
        """
        # Common config (title, labels)
        config = self.render_common_config(data, saved_config)

        # Find histogram variables (columns with ".." pattern indicating buckets)
        histogram_vars = self._detect_histogram_variables(data)

        if not histogram_vars:
            st.warning(
                "No histogram variables detected. "
                "Histogram variables should have columns like 'var..0-10', 'var..10-20', etc."
            )
            return {**config, "histogram_variable": None}

        # Histogram variable selection
        default_var = (
            saved_config.get("histogram_variable")
            if saved_config.get("histogram_variable") in histogram_vars
            else histogram_vars[0]
        )
        default_idx = histogram_vars.index(default_var) if default_var in histogram_vars else 0

        histogram_variable = st.selectbox(
            "Histogram Variable",
            options=histogram_vars,
            index=default_idx,
            key=f"histogram_var_{self.plot_id}",
            help="Select the variable with histogram bucket data",
        )

        # Grouping variable (for multiple histograms)
        categorical_cols = config["categorical_cols"]
        group_options: List[Optional[str]] = [None] + categorical_cols

        group_default_idx = 0
        if saved_config.get("group_by") and saved_config["group_by"] in categorical_cols:
            group_default_idx = group_options.index(saved_config["group_by"])

        group_by = st.selectbox(
            "Group By (optional)",
            options=group_options,
            index=group_default_idx,
            key=f"histogram_group_{self.plot_id}",
            format_func=lambda x: "None" if x is None else x,
            help="Create multiple histograms grouped by this categorical variable",
        )

        # Bucket size configuration
        bucket_size = st.number_input(
            "Bucket Size",
            min_value=1,
            value=int(saved_config.get("bucket_size", 10)),
            key=f"histogram_bucket_{self.plot_id}",
            help="Size of histogram buckets (for rebinning)",
        )

        # Normalization mode
        norm_options = ["count", "probability", "percent", "density"]
        norm_default = saved_config.get("normalization", "count")
        norm_default_idx = (
            norm_options.index(norm_default) if norm_default in norm_options else 0
        )

        normalization = st.selectbox(
            "Normalization",
            options=norm_options,
            index=norm_default_idx,
            key=f"histogram_norm_{self.plot_id}",
            help="How to normalize histogram heights",
        )

        # Cumulative option
        cumulative = st.checkbox(
            "Cumulative",
            value=saved_config.get("cumulative", False),
            key=f"histogram_cumulative_{self.plot_id}",
            help="Show cumulative distribution",
        )

        return {
            **config,
            "histogram_variable": histogram_variable,
            "group_by": group_by,
            "bucket_size": bucket_size,
            "normalization": normalization,
            "cumulative": cumulative,
        }

    def create_figure(
        self, data: pd.DataFrame, config: Dict[str, Any]
    ) -> go.Figure:
        """
        Create histogram plot figure.

        Args:
            data: The data to plot
            config: Configuration dictionary

        Returns:
            Plotly figure object

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
            if col.startswith(f"{histogram_var}..")
            and not col.endswith(".sd")
        ]

        if not bucket_cols:
            raise ValueError(
                f"No histogram bucket columns found for variable: {histogram_var}"
            )

        # Parse bucket ranges and prepare data
        bucket_data = self._extract_bucket_data(data, bucket_cols, config)

        # Create figure
        fig = go.Figure()

        # Add traces
        if config.get("group_by"):
            # Multiple histograms grouped by categorical variable
            self._add_grouped_histograms(fig, bucket_data, config)
        else:
            # Single histogram
            self._add_single_histogram(fig, bucket_data, config)

        # Apply common layout
        fig.update_layout(
            title=config["title"],
            xaxis_title=config["xlabel"],
            yaxis_title=config["ylabel"],
            barmode="overlay" if config.get("group_by") else "relative",
            bargap=0.1,
        )

        return fig

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Get legend column for histogram plot.

        Args:
            config: Plot configuration

        Returns:
            Column name for legend grouping, or None
        """
        return config.get("group_by")

    # ========== Helper Methods ==========

    def _detect_histogram_variables(self, data: pd.DataFrame) -> List[str]:
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
        bucket_cols: List[str],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract and process bucket data from DataFrame.

        Args:
            data: Source DataFrame
            bucket_cols: List of bucket column names
            config: Plot configuration

        Returns:
            Dictionary with processed bucket data
        """
        # Parse bucket ranges
        buckets: List[Tuple[float, float]] = []
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
            result = {
                "buckets": buckets,
                "groups": groups,
                "data": {},
            }

            for group in groups:
                group_data = data[data[group_by] == group]
                values = [
                    group_data[col].sum() if col in group_data.columns else 0
                    for col in bucket_cols
                ]
                result["data"][str(group)] = values

            return result
        else:
            # Single histogram
            values = [data[col].sum() if col in data.columns else 0 for col in bucket_cols]
            return {"buckets": buckets, "groups": None, "data": {"": values}}

    def _add_single_histogram(
        self,
        fig: go.Figure,
        bucket_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> None:
        """
        Add single histogram trace to figure.

        Args:
            fig: Plotly figure object
            bucket_data: Processed bucket data
            config: Plot configuration
        """
        buckets = bucket_data["buckets"]
        values = bucket_data["data"][""]

        # Create bin edges and centers
        x_centers = [(b[0] + b[1]) / 2 for b in buckets]

        # Apply normalization
        values_normalized = self._normalize_values(values, config)

        fig.add_trace(
            go.Bar(
                x=x_centers,
                y=values_normalized,
                name=config.get("histogram_variable", "Histogram"),
                marker=dict(line=dict(width=1, color="white")),
            )
        )

    def _add_grouped_histograms(
        self,
        fig: go.Figure,
        bucket_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> None:
        """
        Add multiple grouped histogram traces to figure.

        Args:
            fig: Plotly figure object
            bucket_data: Processed bucket data
            config: Plot configuration
        """
        buckets = bucket_data["buckets"]
        groups = bucket_data["groups"]

        x_centers = [(b[0] + b[1]) / 2 for b in buckets]

        for group in groups:
            values = bucket_data["data"].get(str(group), [])
            values_normalized = self._normalize_values(values, config)

            fig.add_trace(
                go.Bar(
                    x=x_centers,
                    y=values_normalized,
                    name=str(group),
                    marker=dict(line=dict(width=1, color="white")),
                    opacity=0.7,
                )
            )

    def _normalize_values(
        self, values: List[float], config: Dict[str, Any]
    ) -> List[float]:
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
