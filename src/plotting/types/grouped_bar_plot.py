"""Grouped bar plot implementation."""

from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.plotting.base_plot import BasePlot
from src.plotting.utils import GroupedBarUtils
from src.web.ui.components.plot_config_components import PlotConfigComponents


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

        # Use reusable filter components
        x_values, group_values = PlotConfigComponents.render_filter_multiselects(
            data=data,
            x_col=config.get("x"),
            group_col=group_column,
            saved_config=saved_config,
            plot_id=self.plot_id,
        )

        return {
            **config,
            "group": group_column,
            "color": None,
            "x_filter": x_values,
            "group_filter": group_values,
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

    def render_theme_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Add specific styling options for Grouped Bar."""
        config = super().render_theme_options(saved_config)

        # Visual Distinction Section
        st.markdown("**Visual Distinction**")
        d1, d2 = st.columns(2)
        with d1:
            config["show_separators"] = st.checkbox(
                "Show Vertical Separators",
                value=saved_config.get("show_separators", False),
                key=f"show_sep_{self.plot_id}",
            )
            config["separator_color"] = st.color_picker(
                "Separator Color",
                value=saved_config.get("separator_color", "#E0E0E0"),
                key=f"sep_col_{self.plot_id}",
            )
        with d2:
            # Shading alternate groups might be less relevant for simple grouped bar
            # if the groups are just categories, but providing it for consistency.
            config["shade_alternate"] = st.checkbox(
                "Shade Alternate Categories",
                value=saved_config.get("shade_alternate", False),
                key=f"shade_alt_{self.plot_id}",
            )
            config["shade_color"] = st.color_picker(
                "Shade Color",
                value=saved_config.get("shade_color", "#F5F5F5"),
                key=f"shade_col_{self.plot_id}",
            )

        # Isolation Section
        st.markdown("**Summary Group Isolation (Last Group)**")
        d3, d4 = st.columns(2)
        with d3:
            config["isolate_last_group"] = st.checkbox(
                "Isolate Last Group",
                value=saved_config.get("isolate_last_group", False),
                key=f"iso_last_{self.plot_id}",
                help="Adds extra space and a distinct separator before the last X-axis category.",
            )
        with d4:
            if config["isolate_last_group"]:
                config["isolation_gap"] = st.number_input(
                    "Isolation Gap Size",
                    value=float(saved_config.get("isolation_gap", 0.5)),
                    min_value=0.0,
                    step=0.1,
                    key=f"iso_gap_{self.plot_id}",
                )

        return config

    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create grouped bar plot figure using manual coordinates for spacing control."""

        # 1. Data Preparation
        data = data.copy()
        x_col = config["x"]
        group_col = config["group"] if config.get("group") else None

        data[x_col] = data[x_col].astype(str)
        if group_col:
            data[group_col] = data[group_col].astype(str)

        # Apply Filters
        if config.get("x_filter") is not None:
            data = data[data[x_col].isin(config["x_filter"])]
        if config.get("group_filter") is not None and group_col:
            data = data[data[group_col].isin(config["group_filter"])]

        # Determine Orders
        if config.get("xaxis_order"):
            ordered_x = [str(x) for x in config["xaxis_order"] if str(x) in data[x_col].unique()]
            # Add missing
            missing = [x for x in sorted(data[x_col].unique()) if x not in ordered_x]
            ordered_x.extend(missing)
        else:
            ordered_x = sorted(data[x_col].unique())

        # Determine Group Order (for Legend/Color)
        if group_col:
            if config.get("group_order"):
                ordered_groups = [
                    str(g) for g in config["group_order"] if str(g) in data[group_col].unique()
                ]
                missing_g = [g for g in sorted(data[group_col].unique()) if g not in ordered_groups]
                ordered_groups.extend(missing_g)
            else:
                ordered_groups = sorted(data[group_col].unique())
        else:
            ordered_groups = [None]  # Dummy for iteration

        # 2. Calculate Manual X Coordinates
        # GroupedBarPlot uses Plotly's native 'group' barmode, so we only need one X coordinate
        # per Category (Major Group). The sub-groups are handled by Plotly automatically offsetting traces.
        # So we pass groups=[None] to the utility to get simple category-based coordinates.
        coord_result = GroupedBarUtils.calculate_grouped_coordinates(
            categories=ordered_x, groups=[None], config=config
        )

        # Adapt keys: Utility returns cat (string) when groups=[None]
        # or (cat, grp) when groups are provided.
        x_map = {
            (k[0] if isinstance(k, tuple) else k): v for k, v in coord_result["coord_map"].items()
        }
        tick_vals = coord_result["tick_vals"]
        tick_text = coord_result["tick_text"]
        distinction_shapes = coord_result["shapes"]

        # 3. Create Traces
        fig = go.Figure()

        # If grouped by color
        if group_col:
            # For each group in legend order
            for grp in ordered_groups:
                # Filter data for this group
                grp_data = data[data[group_col] == grp]

                x_coords = grp_data[x_col].map(x_map)

                y_error_dict = None
                if config.get("show_error_bars"):
                    sd_col = f"{config['y']}.sd"
                    if sd_col in data.columns:
                        y_error_dict = dict(type="data", array=grp_data[sd_col], visible=True)

                fig.add_trace(
                    go.Bar(x=x_coords, y=grp_data[config["y"]], name=grp, error_y=y_error_dict)
                )
        else:
            # No grouping (Single series)
            x_coords = data[x_col].map(x_map)

            y_error_dict = None
            if config.get("show_error_bars"):
                sd_col = f"{config['y']}.sd"
                if sd_col in data.columns:
                    y_error_dict = dict(type="data", array=data[sd_col], visible=True)

            fig.add_trace(go.Bar(x=x_coords, y=data[config["y"]], error_y=y_error_dict))

        # 4. Layout
        existing_shapes = config.get("shapes", []) or []
        if not isinstance(existing_shapes, list):
            existing_shapes = []
        fig.update_layout(
            barmode="group",
            title=config.get("title", ""),
            xaxis=dict(
                title=config.get("xlabel", x_col),
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text,
            ),
            yaxis=dict(title=config.get("ylabel", config.get("y", "Value"))),
            shapes=existing_shapes + distinction_shapes,
            legend_title=config.get("group", ""),
        )

        return fig

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for grouped bar plot."""
        return config.get("group")
