"""Line plot implementation."""

from typing import Any, Dict, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.plotting.base_plot import BasePlot


class LinePlot(BasePlot):
    """Line plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "line")

    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
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
        self, saved_config: Dict[str, Any], data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
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

    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create line plot figure."""
        # Sort data by x-axis to ensure correct line drawing order (prevents zig-zags)
        if config.get("x") in data.columns:
            data = data.sort_values(by=config["x"])

        y_error = None
        if config.get("show_error_bars"):
            sd_col = f"{config['y']}.sd"
            if sd_col in data.columns:
                y_error = sd_col

        fig = px.line(
            data,
            x=config["x"],
            y=config["y"],
            color=config.get("color"),
            error_y=y_error,
            title=config["title"],
            labels={config["x"]: config["xlabel"], config["y"]: config["ylabel"]},
            markers=True,  # Enable markers to show explicit points
        )

        # Force categorical x-axis to show all unique values as labels
        fig.update_xaxes(type="category")

        return fig

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for line plot."""
        result = config.get("color")
        return str(result) if result is not None else None
