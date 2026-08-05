"""Grouped bar plot implementation."""

from typing import cast, override

import pandas as pd
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config import grouped_bar_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import (
    build_drill_down_payload,
    extract_error_bars,
    prepare_categorical_data,
)
from src.web.pages.ui.plotting.utils import GroupedBarUtils, order_with_overrides


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
                assert isinstance(data, pd.DataFrame)  # nosec B101  # pandas stubs lose narrowing

            # Apply Group filter
            if saved_config.get("group_filter") is not None and saved_config.get("group"):
                data = data[data[saved_config["group"]].isin(saved_config["group_filter"])]
                assert isinstance(data, pd.DataFrame)  # nosec B101  # pandas stubs lose narrowing

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
        # [impl->req~ring5.figure.alternate-category-shading~1]
        # [impl->req~ring5.figure.plot-filtering~1]
        # [impl->req~ring5.plot.grouped-bar~1]

        # 1. Data Preparation
        x_col = cast(str, config["x"])
        y_col = cast(str, config["y"])
        group_col = cast(str | None, config.get("group"))
        data = prepare_categorical_data(data, [x_col, group_col])

        # Apply Filters
        if config.get("x_filter") is not None:
            data = data[data[x_col].isin(config["x_filter"])]
        if config.get("group_filter") is not None and group_col:
            data = data[data[group_col].isin(config["group_filter"])]

        # Determine Orders (explicit order first, then remaining sorted)
        ordered_x = order_with_overrides(data[x_col].unique(), config.get("xaxis_order"))
        if group_col:
            ordered_groups = order_with_overrides(
                data[group_col].unique(), config.get("group_order")
            )

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

        # 3. Create Traces
        traces: list[BarTraceConfig] = []

        # If grouped by color
        if group_col:
            for grp in ordered_groups:
                grp_data = data[data[group_col] == grp]
                x_coords = pd.Series(grp_data[x_col]).map(x_map).tolist()

                sd_col = extract_error_bars(data, y_col, config)
                error_y_vals: list[float] | None = grp_data[sd_col].tolist() if sd_col else None

                traces.append(
                    BarTraceConfig(
                        name=grp,
                        x_positions=x_coords,
                        y=grp_data[y_col].tolist(),
                        error_y=error_y_vals,
                        custom_data={
                            "drilldown": build_drill_down_payload(grp_data, [x_col, group_col])
                        },
                    )
                )
        else:
            # No grouping (Single series)
            x_coords = pd.Series(data[x_col]).map(x_map).tolist()

            sd_col = extract_error_bars(data, y_col, config)
            error_y_vals = data[sd_col].tolist() if sd_col else None

            traces.append(
                BarTraceConfig(
                    x_positions=x_coords,
                    y=data[y_col].tolist(),
                    error_y=error_y_vals,
                    custom_data={"drilldown": build_drill_down_payload(data, [x_col])},
                )
            )

        # 4. Build result with separators/shading and tick overrides.
        # User-drawn shapes (config["shapes"]) are applied separately by the
        # Plotly StyleApplicator; the auto separators/shades flow through the
        # engine-agnostic fields so both engines render them.
        return TraceBuildResult(
            traces=traces,
            barmode="group",
            separator_lines=coord_result["separator_lines"],
            rule_lines=coord_result.get("category_group_rules") or [],
            shaded_regions=coord_result["shaded_regions"],
            custom_x_ticks={"vals": tick_vals, "text": tick_text},
        )

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Get legend column for grouped bar plot."""
        result = config.get("group")
        return str(result) if result is not None else None
