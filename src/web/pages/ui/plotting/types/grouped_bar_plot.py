"""Grouped bar plot implementation."""

from typing import cast, override

import pandas as pd

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
        ordered_groups: list[str] = []
        if group_col:
            ordered_groups = order_with_overrides(
                data[group_col].unique(), config.get("group_order")
            )

        # 2. Calculate Manual X Coordinates
        coord_result = GroupedBarUtils.calculate_grouped_coordinates(
            categories=ordered_x, groups=ordered_groups, config=config
        )

        # Adapt keys
        x_map = {
            (k[0] if isinstance(k, tuple) else k): v for k, v in coord_result["coord_map"].items()
        }
        tick_vals = [center for center, _ in coord_result["cat_centers"]]
        tick_text = [label for _, label in coord_result["cat_centers"]]

        # 3. Create Traces
        traces: list[BarTraceConfig] = []

        # If grouped by color
        if group_col:
            for grp in ordered_groups:
                grp_data = data[data[group_col] == grp]
                x_coords = [
                    coord_result["coord_map"][(category, grp)] for category in grp_data[x_col]
                ]

                sd_col = extract_error_bars(data, y_col, config)
                error_y_vals: list[float] | None = grp_data[sd_col].tolist() if sd_col else None

                traces.append(
                    BarTraceConfig(
                        name=grp,
                        x_positions=x_coords,
                        bar_width=coord_result["bar_width"],
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
                    bar_width=coord_result["bar_width"],
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
