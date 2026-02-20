"""Scatter plot implementation."""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import ScatterTraceConfig
from src.web.pages.ui.plotting.base_plot import BasePlot


class ScatterPlot(BasePlot):
    """Scatter plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "scatter")

    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for scatter plot."""
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

    def create_traces(self, data: pd.DataFrame, config: Dict[str, Any]) -> TraceBuildResult:
        """Produce scatter traces from data and config."""
        x_col: str = config["x"]
        y_col: str = config["y"]
        color_col: Optional[str] = config.get("color")

        # Error bar column
        sd_col: Optional[str] = None
        if config.get("show_error_bars"):
            candidate = f"{y_col}.sd"
            if candidate in data.columns:
                sd_col = candidate

        traces: List[ScatterTraceConfig] = []

        if color_col:
            groups: List[str] = sorted(data[color_col].unique().astype(str))
            data = data.copy()
            data[color_col] = data[color_col].astype(str)
            for grp in groups:
                grp_data = data[data[color_col] == grp]
                error_y = grp_data[sd_col].tolist() if sd_col else None
                traces.append(
                    ScatterTraceConfig(
                        name=str(grp),
                        x=grp_data[x_col].tolist(),
                        y=grp_data[y_col].tolist(),
                        error_y=error_y,
                    )
                )
        else:
            error_y = data[sd_col].tolist() if sd_col else None
            traces.append(
                ScatterTraceConfig(
                    name=y_col,
                    x=data[x_col].tolist(),
                    y=data[y_col].tolist(),
                    error_y=error_y,
                )
            )

        return TraceBuildResult(traces=traces)

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for scatter plot."""
        result = config.get("color")
        return str(result) if result is not None else None
