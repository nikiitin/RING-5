"""Grouped bar plot implementation."""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.pages.ui.components.plot_config_components import PlotConfigComponents
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.utils import GroupedBarUtils


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

    def render_theme_options(
        self, saved_config: Dict[str, Any], items: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Add specific styling options for Grouped Bar."""
        config = super().render_theme_options(saved_config, items)

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

    def create_traces(self, data: pd.DataFrame, config: Dict[str, Any]) -> TraceBuildResult:
        """Create grouped bar trace configurations using manual coordinates."""

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
            ordered_groups = []  # Empty list instead of [None]

        # 2. Calculate Manual X Coordinates
        coord_result = GroupedBarUtils.calculate_grouped_coordinates(
            categories=ordered_x, groups=[], config=config
        )

        # Adapt keys
        x_map = {
            (k[0] if isinstance(k, tuple) else k): v for k, v in coord_result["coord_map"].items()
        }
        tick_vals = coord_result["tick_vals"]
        tick_text = coord_result["tick_text"]
        distinction_shapes = coord_result["shapes"]

        # 3. Create Traces
        traces: List[BarTraceConfig] = []

        # If grouped by color
        if group_col:
            for grp in ordered_groups:
                grp_data = data[data[group_col] == grp]
                x_coords = grp_data[x_col].map(x_map).tolist()

                error_y_vals: Optional[List[float]] = None
                if config.get("show_error_bars"):
                    sd_col = f"{config['y']}.sd"
                    if sd_col in data.columns:
                        error_y_vals = grp_data[sd_col].tolist()

                traces.append(
                    BarTraceConfig(
                        name=grp,
                        x_positions=x_coords,
                        y=grp_data[config["y"]].tolist(),
                        error_y=error_y_vals,
                    )
                )
        else:
            # No grouping (Single series)
            x_coords = data[x_col].map(x_map).tolist()

            error_y_vals = None
            if config.get("show_error_bars"):
                sd_col = f"{config['y']}.sd"
                if sd_col in data.columns:
                    error_y_vals = data[sd_col].tolist()

            traces.append(
                BarTraceConfig(
                    x_positions=x_coords,
                    y=data[config["y"]].tolist(),
                    error_y=error_y_vals,
                )
            )

        # 4. Build result with shapes and tick overrides
        existing_shapes = config.get("shapes", []) or []
        if not isinstance(existing_shapes, list):
            existing_shapes = []

        return TraceBuildResult(
            traces=traces,
            barmode="group",
            shapes=existing_shapes + distinction_shapes,
            custom_x_ticks={"vals": tick_vals, "text": tick_text},
        )

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for grouped bar plot."""
        result = config.get("group")
        return str(result) if result is not None else None
