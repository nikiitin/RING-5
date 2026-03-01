"""Grouped bar plot implementation."""

from typing import override

import pandas as pd
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config import grouped_bar_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.utils import GroupedBarUtils


class GroupedBarPlot(BasePlot):
    """Grouped bar plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "grouped_bar")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for grouped bar plot."""
        return grouped_bar_config.render(data, saved_config, self.plot_id)

    @override
    def render_advanced_options(
        self, saved_config: PlotConfig, data: pd.DataFrame | None = None
    ) -> PlotConfig:
        """Override to apply filters before rendering advanced options."""
        if data is not None:
            # Apply X filter
            if saved_config.get("x_filter") is not None:
                data = data[data[saved_config["x"]].isin(saved_config["x_filter"])]

            # Apply Group filter
            if saved_config.get("group_filter") is not None and saved_config.get("group"):
                data = data[data[saved_config["group"]].isin(saved_config["group_filter"])]

        return super().render_advanced_options(saved_config, data)

    @override
    def render_theme_options(
        self, saved_config: PlotConfig, items: list[str] | None = None
    ) -> PlotConfig:
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

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
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
        traces: list[BarTraceConfig] = []

        # If grouped by color
        if group_col:
            for grp in ordered_groups:
                grp_data = data[data[group_col] == grp]
                x_coords = pd.Series(grp_data[x_col]).map(x_map).tolist()

                error_y_vals: list[float] | None = None
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
            x_coords = pd.Series(data[x_col]).map(x_map).tolist()

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

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Get legend column for grouped bar plot."""
        result = config.get("group")
        return str(result) if result is not None else None
