"""Grouped bar plot implementation."""

from typing import Any, Dict, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.plotting.base_plot import BasePlot


class GroupedBarPlot(BasePlot):
    """Grouped bar plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "grouped_bar")

    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for grouped bar plot."""
        # Common config
        config = self.render_common_config(data, saved_config)

        # Group by option
        group_default_idx = 0
        if saved_config.get("group") and saved_config["group"] in config["categorical_cols"]:
            group_default_idx = config["categorical_cols"].index(saved_config["group"])

        group_column = st.selectbox(
            "Group by",
            options=config["categorical_cols"],
            index=group_default_idx,
            key=f"group_{self.plot_id}",
        )

        col_filter1, col_filter2 = st.columns(2)

        # Filter X values
        x_values = []
        if config.get("x") and config["x"] in data.columns:
            unique_x = sorted(data[config["x"]].astype(str).unique())
            default_x = saved_config.get("x_filter", unique_x)
            # Ensure defaults are valid
            default_x = [x for x in default_x if x in unique_x]

            with col_filter1:
                x_values = st.multiselect(
                    "Filter X values",
                    options=unique_x,
                    default=default_x,
                    key=f"x_filter_{self.plot_id}",
                    help="Select specific values to display on the X-axis.",
                )

        # Filter Group values
        group_values = []
        if group_column and group_column in data.columns:
            unique_g = sorted(data[group_column].astype(str).unique())
            default_g = saved_config.get("group_filter", unique_g)
            # Ensure defaults are valid
            default_g = [g for g in default_g if g in unique_g]

            with col_filter2:
                group_values = st.multiselect(
                    "Filter Groups",
                    options=unique_g,
                    default=default_g,
                    key=f"group_filter_{self.plot_id}",
                    help="Select specific groups to display.",
                )

        # Display options
        display_config = self.render_display_options(saved_config)

        return {
            **config,
            "group": group_column,
            "color": None,
            "x_filter": x_values,
            "group_filter": group_values,
            **display_config,
            "_needs_advanced": True,
        }

    def render_advanced_options(
        self, saved_config: Dict[str, Any], data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """Override to apply filters before rendering advanced options."""
        if data is not None:
            # Apply X filter
            if saved_config.get("x_filter") is not None:
                data = data[data[saved_config["x"]].isin(saved_config["x_filter"])]
            
            # Apply Group filter
            if saved_config.get("group_filter") is not None and saved_config.get("group"):
                data = data[data[saved_config["group"]].isin(saved_config["group_filter"])]

        return super().render_advanced_options(saved_config, data)

    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create grouped bar plot figure."""
        y_error = None
        if config.get("show_error_bars"):
            sd_col = f"{config['y']}.sd"
            if sd_col in data.columns:
                y_error = sd_col

        # Ensure data is string for categorical plotting
        data = data.copy()
        data[config["x"]] = data[config["x"]].astype(str)
        if config.get("group"):
            data[config["group"]] = data[config["group"]].astype(str)

        # Apply Filters
        if config.get("x_filter") is not None:
            data = data[data[config["x"]].isin(config["x_filter"])]

        if config.get("group_filter") is not None and config.get("group"):
            data = data[data[config["group"]].isin(config["group_filter"])]

        # Handle ordering
        category_orders = {}
        if config.get("xaxis_order"):
            category_orders[config["x"]] = [str(x) for x in config["xaxis_order"]]
        if config.get("group_order"):
            category_orders[config["group"]] = [str(x) for x in config["group_order"]]

        fig = px.bar(
            data,
            x=config["x"],
            y=config["y"],
            color=config["group"],
            error_y=y_error,
            barmode="group",
            title=config["title"],
            labels={config["x"]: config["xlabel"], config["y"]: config["ylabel"]},
            category_orders=category_orders,
        )

        return fig

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for grouped bar plot."""
        return config.get("group")
