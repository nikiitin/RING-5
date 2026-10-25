"""Grouped stacked bar plot implementation."""

from typing import Any, override

import pandas as pd
import plotly.graph_objects as go

from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import TraceConfig
from src.web.components.plotting.config import grouped_stacked_bar_config
from src.core.models.plot_config import PlotConfig
from src.web.pages.ui.plotting.types._trace_helpers import (
    build_drill_down_payload,
    prepare_categorical_data,
)
from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot
from src.web.pages.ui.plotting.utils import GroupedBarUtils


class GroupedStackedBarPlot(StackedBarPlot):
    """Grouped stacked bar plot with support for multiple stacked statistics and grouping."""

    def __init__(self, plot_id: int, name: str) -> None:
        """Initialize a grouped stacked plot with its concrete type identifier."""
        # Call through MRO (StackedBarPlot → BarPlot → BasePlot)
        super().__init__(plot_id, name)
        # Override plot_type set by parent chain ("stacked_bar" → "grouped_stacked_bar")
        self.plot_type: str = "grouped_stacked_bar"

    @override
    def _supports_secondary_legend(self) -> bool:
        """Grouped stacked bar always supports a secondary legend.

        The secondary legend is used for the numbered X-axis feature
        as well as dual-axis legend separation.
        """
        return True

    @override
    def _supports_tertiary_legend(self) -> bool:
        """Tertiary legend is available when dual-axis splits legends.

        When dual-axis has right-axis series and legends are not unified,
        the secondary pill controls the right-axis legend (legend2_*) and
        the tertiary pill controls the numbered-xaxis annotation
        (legend3_*). Otherwise, the secondary pill controls the annotation.
        """
        return True

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for grouped stacked bar plot."""
        return grouped_stacked_bar_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Create grouped stacked bar trace configurations."""
        # [impl->req~ring5.figure.plot-filtering~1]
        # [impl->req~ring5.plot.grouped-stacked-bar~1]
        x_col = config.get("x")
        group_col = config.get("group")
        y_cols = config.get("y_columns", [])
        dual_axis: bool = bool(config.get("dual_axis"))

        # If no group column, delegate to parent's simple stacked bar implementation
        if not group_col:
            return super().create_traces(data, config)

        if not x_col or not y_cols:
            return TraceBuildResult(traces=[], barmode="stack")

        # Prepare data — include right-axis columns in total calculation
        y_cols_right: list[str] = config.get("y_columns_right", []) if dual_axis else []
        all_y_cols: list[str] = y_cols + [c for c in y_cols_right if c not in y_cols]
        data = self._prepare_data(data, x_col, all_y_cols, config)

        # Define hover template
        hover_template = self._get_hover_template()

        # Create grouped traces
        return self._create_grouped_traces(
            data, x_col, group_col, y_cols, config, hover_template, dual_axis
        )

    def _create_grouped_traces(
        self,
        data: pd.DataFrame,
        x_col: str,
        group_col: str,
        y_cols: list[str],
        config: PlotConfig,
        hover_template: str,
        dual_axis: bool = False,
    ) -> TraceBuildResult:
        """Build TraceBuildResult for grouped stacked bars."""
        # Copy + cast the group column to string (categorical axis)
        data = prepare_categorical_data(data, [group_col])

        # Apply Group Filter
        if config.get("group_filter") is not None:
            data = data[data[group_col].isin(config["group_filter"])]

        # Get ordered categories and groups
        categories, groups = self._get_ordered_categories_and_groups(data, x_col, group_col, config)

        data["__ring5_drilldown_x"] = data[x_col]
        data["__ring5_drilldown_group"] = data[group_col]

        # Apply renames
        data, categories, groups = self._apply_renames(
            data, x_col, group_col, categories, groups, config
        )

        # Build coordinate map and shapes
        coord_result = self._build_coordinate_map(
            categories, groups, data, x_col, group_col, config
        )
        coord_map = coord_result["coord_map"]
        tick_vals = coord_result["tick_vals"]
        tick_text = coord_result["tick_text"]
        cat_centers = coord_result["cat_centers"]
        separator_lines = coord_result["separator_lines"]
        shaded_regions = coord_result["shaded_regions"]
        bar_width = coord_result["bar_width"]

        # Map coordinates to data
        data["__x_coord"] = data.apply(
            lambda row: coord_map.get((row[x_col], row[group_col]), None), axis=1
        )

        # Build bar traces (LEFT axis)
        traces: list[TraceConfig] = []
        for y_col in y_cols:
            trace = self._build_bar_trace(
                data, y_col, "__x_coord", bar_width, hover_template, config
            )
            traces.append(trace)

        # Build RIGHT-axis traces (dual-axis mode)
        if dual_axis:
            y_cols_right: list[str] = config.get("y_columns_right", [])
            right_type: str = config.get("right_axis_type", "bars")
            right_traces = self._build_right_axis_traces(
                data, "__x_coord", y_cols_right, right_type, bar_width, config
            )
            traces.extend(right_traces)

        if dual_axis and config.get("unified_legend", True):
            traces = self._order_unified_legend_traces(traces, config)

        payloads = build_drill_down_payload(
            data,
            {
                x_col: "__ring5_drilldown_x",
                group_col: "__ring5_drilldown_group",
            },
        )
        payload_by_coordinate = dict(zip(data["__x_coord"], payloads, strict=False))
        for built_trace in traces:
            coordinates = getattr(built_trace, "x_positions", []) or built_trace.x
            built_trace.custom_data["drilldown"] = [
                payload_by_coordinate.get(coordinate, {}) for coordinate in coordinates
            ]

        # Apply numbered X-axis labels (replace verbose ticks with indices)
        tick_text, numbered_legend = self._apply_numbered_xaxis(tick_text, config)

        # Build custom_x_ticks
        custom_x_ticks: dict[str, list[Any]] = {"vals": tick_vals, "text": tick_text}

        # Hide x-tick labels per the shared rule (same logic the mpl path uses).
        from src.web.rendering.config_builder import should_show_x_tick_labels

        if not should_show_x_tick_labels(config):
            custom_x_ticks["hide_ticks"] = [True]

        # Build annotations
        annotations = self._build_category_annotations(cat_centers, config)

        # Super-group labels under the category labels
        group_centers = coord_result.get("category_group_centers") or []
        if group_centers:
            annotations.extend(self._build_category_group_annotations(group_centers, config))

        # Add totals if requested
        if config.get("show_totals"):
            totals_annotations = self._build_totals_annotations(data, "__x_coord", config)
            annotations.extend(totals_annotations)

        # Add numbered legend annotation if enabled
        if numbered_legend is not None:
            annotations.append(numbered_legend)

        return TraceBuildResult(
            traces=traces,
            barmode="stack",
            separator_lines=separator_lines,
            rule_lines=coord_result.get("category_group_rules") or [],
            shaded_regions=shaded_regions,
            custom_x_ticks=custom_x_ticks,
            annotations=annotations,
            secondary_y=dual_axis,
        )

    @staticmethod
    def _order_unified_legend_traces(
        traces: list[TraceConfig], config: PlotConfig
    ) -> list[TraceConfig]:
        """Apply a combined left/right order to a unified legend."""
        # [impl->req~ring5.figure.ordering-renaming~2]
        configured_order = config.get("legend_order")
        if not configured_order:
            return traces

        series_styles: dict[str, Any] = config.get("series_styles", {})
        ordered_names = [
            str(series_styles.get(key, {}).get("name", key)) for key in configured_order
        ]
        rank = {name: index for index, name in enumerate(ordered_names)}
        fallback = len(rank)
        return [
            trace
            for _, trace in sorted(
                enumerate(traces),
                key=lambda indexed: (rank.get(indexed[1].name, fallback), indexed[0]),
            )
        ]

    def _get_ordered_categories_and_groups(
        self, data: pd.DataFrame, x_col: str, group_col: str, config: PlotConfig
    ) -> tuple[list[str], list[str]]:
        """Get ordered lists of categories and groups."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            get_ordered_categories_and_groups,
        )

        return get_ordered_categories_and_groups(data, x_col, group_col, config)

    def _apply_renames(
        self,
        data: pd.DataFrame,
        x_col: str,
        group_col: str,
        categories: list[str],
        groups: list[str],
        config: PlotConfig,
    ) -> tuple[pd.DataFrame, list[str], list[str]]:
        """Apply renames to data and ordered lists."""
        # [impl->req~ring5.figure.ordering-renaming~2]
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            apply_renames,
        )

        return apply_renames(data, x_col, group_col, categories, groups, config)

    def _build_coordinate_map(
        self,
        categories: list[str],
        groups: list[str],
        data: pd.DataFrame,
        x_col: str,
        group_col: str,
        config: PlotConfig,
    ) -> dict[str, Any]:
        """Build coordinate mapping for grouped bars using centralized utility."""
        return GroupedBarUtils.calculate_grouped_coordinates(
            categories=categories, groups=groups, config=config
        )

    def _apply_numbered_xaxis(
        self,
        tick_text: list[str],
        config: PlotConfig,
    ) -> tuple[list[str], AnnotationConfig | None]:
        """Replace tick labels with numbered indices and build legend annotation."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            apply_numbered_xaxis,
        )

        return apply_numbered_xaxis(tick_text, config)

    def _build_category_annotations(
        self, cat_centers: list[tuple[float, str]], config: PlotConfig
    ) -> list[AnnotationConfig]:
        """Build annotations for category labels (grouped bars only)."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            build_category_annotations,
        )

        return build_category_annotations(cat_centers, config)

    def _build_category_group_annotations(
        self, group_centers: list[tuple[float, str]], config: PlotConfig
    ) -> list[AnnotationConfig]:
        """Build annotations for category super-group labels."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            build_category_group_annotations,
        )

        return build_category_group_annotations(group_centers, config)

    @override
    def apply_common_layout(self, fig: go.Figure, config: PlotConfig) -> go.Figure:
        """Apply common layout and enforce hover template."""
        fig = super().apply_common_layout(fig, config)

        # Enforce hover template for this specific plot type (reuse the inherited single
        # source so the two never drift); this overwrites what base_plot sets.
        fig.update_traces(hovertemplate=self._get_hover_template())

        # Dual-axis enhancements
        if config.get("dual_axis"):
            # 1. Y-axis title rotation
            #    Primary (left):  reads bottom-to-top (textangle=-90, standard)
            #    Secondary (right): reads top-to-bottom (textangle=90, opposite)
            self._apply_dual_axis_titles(fig, config)

            # 2. Grid lines per axis — primary ON by default, secondary OFF
            fig.update_yaxes(
                showgrid=config.get("show_y_grid", True),
                secondary_y=False,
            )
            fig.update_yaxes(
                showgrid=config.get("y2show_y_grid", False),
                secondary_y=True,
            )

            # 3. Legend unification
            if not config.get("unified_legend", True):
                self._apply_separate_legends(fig, config)

        return fig

    # Dual-axis helpers

    def _apply_dual_axis_titles(self, fig: go.Figure, config: PlotConfig) -> None:
        """Apply Y-axis titles as symmetrical annotations for dual-axis mode."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            apply_dual_axis_titles,
        )

        apply_dual_axis_titles(fig, config)

    def _apply_separate_legends(self, fig: go.Figure, config: PlotConfig) -> None:
        """Split traces into separate legends for left and right axis groups."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            apply_separate_legends,
        )

        apply_separate_legends(fig, config)

    def _build_right_axis_traces(
        self,
        data: pd.DataFrame,
        x_coord_col: str,
        y_cols: list[str],
        trace_type: str,
        bar_width: float | None,
        config: PlotConfig,
    ) -> list[TraceConfig]:
        """Build traces for the secondary (right) Y-axis."""
        # [impl->req~ring5.figure.dual-axis-controls~1]
        # [impl->req~ring5.plot.grouped-stacked-bar~1]
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            build_right_axis_traces,
        )

        return build_right_axis_traces(data, x_coord_col, y_cols, trace_type, bar_width, config)
