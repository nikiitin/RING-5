"""Bar plot implementation."""

from typing import Any, Dict, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.plotting.base_plot import BasePlot


class BarPlot(BasePlot):
    """Simple bar plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "bar")

    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for bar plot."""
        # Common config (x, y, title, labels)
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

        # Display options
        display_config = self.render_display_options(saved_config)

        return {**config, "color": color_column, **display_config}

    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create bar plot figure."""
        y_error = None
        if config.get("show_error_bars"):
            sd_col = f"{config['y']}.sd"
            if sd_col in data.columns:
                y_error = sd_col

        # Ensure data is string for categorical plotting
        data = data.copy()
        data[config["x"]] = data[config["x"]].astype(str)
        if config.get("color"):
            data[config["color"]] = data[config["color"]].astype(str)

        # Handle ordering
        category_orders = {}
        if config.get("xaxis_order"):
            category_orders[config["x"]] = [str(x) for x in config["xaxis_order"]]
        if config.get("legend_order") and config.get("color"):
            category_orders[config["color"]] = [str(x) for x in config["legend_order"]]

        fig = px.bar(
            data,
            x=config["x"],
            y=config["y"],
            color=config.get("color"),
            error_y=y_error,
            title=config["title"],
            labels={config["x"]: config["xlabel"], config["y"]: config["ylabel"]},
            category_orders=category_orders,
        )

        return fig

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for bar plot."""
        return config.get("color")
