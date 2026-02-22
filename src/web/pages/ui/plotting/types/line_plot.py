"""Line plot implementation."""

from typing import Any

import pandas as pd
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import LineTraceConfig
from src.web.pages.ui.plotting.base_plot import BasePlot


class LinePlot(BasePlot):
    """Line plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "line")

    def render_config_ui(self, data: pd.DataFrame, saved_config: dict[str, Any]) -> dict[str, Any]:
        """Render configuration UI for line plot."""
        # Common config
        config = self.render_common_config(data, saved_config)

        # Color option
        color_options = [None] + config["categorical_cols"]
        color_default_idx = 0
        if saved_config.get("color") and saved_config["color"] in config["categorical_cols"]:
            color_default_idx = color_options.index(saved_config["color"])

        color_column = st.selectbox(
            "Color by (optional)",
            options=color_options,
            index=color_default_idx,
            key=f"color_{self.plot_id}",
        )

        return {**config, "color": color_column}

    def render_specific_advanced_options(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None = None
    ) -> dict[str, Any]:
        """Specific options for Line Plot."""
        config = {}
        st.markdown("#### Line Settings")
        config["line_shape"] = st.selectbox(
            "Line Shape",
            ["linear", "spline", "hv", "vh", "hvh", "vhv"],
            index=["linear", "spline", "hv", "vh", "hvh", "vhv"].index(
                saved_config.get("line_shape", "linear")
            ),
            key=f"lshape_{self.plot_id}",
        )
        return config

    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        """Produce line traces from data and config."""
        x_col: str = config["x"]
        y_col: str = config["y"]
        color_col: str | None = config.get("color")

        # Sort by x-axis to ensure correct line drawing order
        if x_col in data.columns:
            data = data.sort_values(by=x_col)

        # Error bar column
        sd_col: str | None = None
        if config.get("show_error_bars"):
            candidate = f"{y_col}.sd"
            if candidate in data.columns:
                sd_col = candidate

        traces: list[LineTraceConfig] = []

        if color_col:
            groups: list[str] = sorted(data[color_col].unique().astype(str))
            data = data.copy()
            data[color_col] = data[color_col].astype(str)
            for grp in groups:
                grp_data = data[data[color_col] == grp]
                error_y = grp_data[sd_col].tolist() if sd_col else None
                traces.append(
                    LineTraceConfig(
                        name=str(grp),
                        x=grp_data[x_col].tolist(),
                        y=grp_data[y_col].tolist(),
                        show_markers=True,
                        error_y=error_y,
                    )
                )
        else:
            error_y = data[sd_col].tolist() if sd_col else None
            traces.append(
                LineTraceConfig(
                    name=y_col,
                    x=data[x_col].tolist(),
                    y=data[y_col].tolist(),
                    show_markers=True,
                    error_y=error_y,
                )
            )

        return TraceBuildResult(traces=traces)

    def get_legend_column(self, config: dict[str, Any]) -> str | None:
        """Get legend column for line plot."""
        result = config.get("color")
        return str(result) if result is not None else None
