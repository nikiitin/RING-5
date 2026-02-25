"""Grouped stacked bar plot implementation."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import TraceConfig
from src.web.components.plotting.config import grouped_stacked_bar_config
from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot
from src.web.pages.ui.plotting.utils import GroupedBarUtils


class GroupedStackedBarPlot(StackedBarPlot):
    """Grouped stacked bar plot with support for multiple stacked statistics and grouping."""

    def __init__(self, plot_id: int, name: str):
        # Call through MRO (StackedBarPlot → BarPlot → BasePlot)
        super().__init__(plot_id, name)
        # Override plot_type set by parent chain ("stacked_bar" → "grouped_stacked_bar")
        self.plot_type: str = "grouped_stacked_bar"

    def _supports_secondary_legend(self) -> bool:
        """Grouped stacked bar always supports a secondary legend.

        The secondary legend is used for the numbered X-axis feature
        as well as dual-axis legend separation.
        """
        return True

    def _supports_tertiary_legend(self) -> bool:
        """Tertiary legend is available when dual-axis splits legends.

        When dual-axis is active AND legends are not unified, the
        secondary pill controls the right-axis legend (legend2_*) and
        the tertiary pill controls the numbered-xaxis annotation
        (legend3_*).  Without dual-axis, the secondary pill itself
        controls the annotation, so no third level is needed.
        """
        return True

    def render_config_ui(self, data: pd.DataFrame, saved_config: dict[str, Any]) -> dict[str, Any]:
        """Render configuration UI for grouped stacked bar plot."""
        return grouped_stacked_bar_config.render(data, saved_config, self.plot_id)

    def _render_stack_total_options(
        self, saved_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Render options for Stack Totals."""
        from src.web.components.plotting.config.grouped_stacked_bar_theme import (
            render_stack_total_options,
        )

        render_stack_total_options(saved_config, config, self.plot_id)

    def render_theme_options(
        self, saved_config: dict[str, Any], items: list[str] | None = None
    ) -> dict[str, Any]:
        """Override to add specific styling options."""
        # Get base theme options
        stacks = saved_config.get("y_columns", [])
        config = super().render_theme_options(saved_config, items=stacks)

        # Add grouped-stacked-bar-specific theme extras
        from src.web.components.plotting.config.grouped_stacked_bar_theme import (
            render_grouped_theme_extras,
        )

        render_grouped_theme_extras(saved_config, config, self.plot_id)

        return config

    def render_advanced_options(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None = None
    ) -> dict[str, Any]:
        """Custom Advanced Options for Grouped Stacked Bar."""
        config: dict[str, Any] = {}

        # 1. General Settings
        self._render_general_settings(saved_config, config)

        # 2. Specific Bar Settings
        specific = self.render_specific_advanced_options(saved_config, data)
        config.update(specific)

        # 2b. Right-axis dot/line settings (only when dual_axis + dots)
        if saved_config.get("dual_axis") and saved_config.get("right_axis_type") == "dots":
            self._render_right_axis_dot_settings(saved_config, config)

        # 2c. Dual-axis display settings (grid lines, legend unification)
        if saved_config.get("dual_axis"):
            self._render_dual_axis_display_settings(saved_config, config)

        # 2d. Right-axis series configuration (reorder & rename)
        if saved_config.get("dual_axis"):
            y_cols_right: list[str] = saved_config.get("y_columns_right", [])
            if y_cols_right:
                st.markdown("#### Right-Axis Series Configuration")
                existing_styles: dict[str, Any] = saved_config.get("series_styles", {})
                right_rename_map: dict[str, str] = {
                    k: str(existing_styles[k].get("name", k))
                    for k in y_cols_right
                    if k in existing_styles and existing_styles[k].get("name")
                }
                with st.expander("Reorder & Rename Right-Axis Series"):
                    current_right_order = list(y_cols_right)
                    r_result = self.render_reorderable_list(
                        "Right-Axis Order",
                        current_right_order,
                        "right_ord",
                        enable_rename=True,
                        rename_map=right_rename_map or None,
                    )
                    new_right_order, right_renames = r_result  # type: ignore[misc]
                    if new_right_order != current_right_order:
                        config["y_columns_right"] = new_right_order
                    if right_renames and isinstance(right_renames, dict):
                        if "series_styles" not in config:
                            config["series_styles"] = {}
                        for k, v in right_renames.items():
                            if k not in config["series_styles"]:
                                config["series_styles"][k] = {"name": v}
                            else:
                                config["series_styles"][k]["name"] = v

        # 3. Stack Configuration
        y_cols = saved_config.get("y_columns", [])
        if y_cols:
            st.markdown("#### Stack / Legend Configuration")
            stack_styles: dict[str, Any] = saved_config.get("series_styles", {})
            stack_rename_map: dict[str, str] = {
                k: str(stack_styles[k].get("name", k))
                for k in y_cols
                if k in stack_styles and stack_styles[k].get("name")
            }
            with st.expander("Reorder & Rename"):
                current_order = list(y_cols)
                s_result = self.render_reorderable_list(
                    "Stack Order",
                    current_order,
                    "stack_ord",
                    enable_rename=True,
                    rename_map=stack_rename_map or None,
                )
                new_order, stack_renames = s_result  # type: ignore[misc]
                if new_order != current_order:
                    config["y_columns"] = new_order
                if stack_renames and isinstance(stack_renames, dict):
                    if "series_styles" not in config:
                        config["series_styles"] = {}
                    for k, v in stack_renames.items():
                        if k not in config["series_styles"]:
                            config["series_styles"][k] = {"name": v}
                        else:
                            config["series_styles"][k]["name"] = v

        # 4. Major Group Configuration (Original X)
        x_col = saved_config.get("x")
        if data is not None and x_col and x_col in data.columns:
            st.markdown("#### Major Grouping (Outer) Configuration")
            with st.expander("Reorder & Rename Major Groups"):
                unique_x = sorted(data[x_col].unique().tolist())
                maj_result = self.render_reorderable_list(
                    "Major Group Order",
                    unique_x,
                    "xaxis",
                    default_order=saved_config.get("xaxis_order"),
                    enable_rename=True,
                    rename_map=saved_config.get("xaxis_labels"),
                )
                order_maj, renames_maj = maj_result  # type: ignore[misc]
                config["xaxis_order"] = order_maj
                if renames_maj:
                    config["xaxis_labels"] = renames_maj

        # 5. Minor Group Configuration (Original Group)
        group_col = saved_config.get("group")
        if data is not None and group_col and group_col in data.columns:
            st.markdown("#### X-Axis / Minor Grouping (Inner) Configuration")
            with st.expander("Reorder & Rename Minor Groups"):
                unique_g = sorted(data[group_col].unique().tolist())
                min_result = self.render_reorderable_list(
                    "Minor Group Order",
                    unique_g,
                    "group",
                    default_order=saved_config.get("group_order"),
                    enable_rename=True,
                    rename_map=saved_config.get("group_renames"),
                )
                order_min, renames_min = min_result  # type: ignore[misc]
                config["group_order"] = order_min
                if renames_min:
                    config["group_renames"] = renames_min

        # 6. Reference Line (Normalizer)
        self._render_reference_line_ui(saved_config, data, config)

        # 7. Annotations
        st.markdown("#### Annotations (Shapes)")
        config["shapes"] = self._render_shapes_ui(saved_config)

        # Legend & Interactivity (Standard)
        st.markdown("#### Legend & Interactivity")
        config["enable_editable"] = st.checkbox(
            "Enable Interactive Editing",
            value=saved_config.get("enable_editable", False),
            key=f"editable_{self.plot_id}",
        )

        return config

    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        """Create grouped stacked bar trace configurations."""
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
        config: dict[str, Any],
        hover_template: str,
        dual_axis: bool = False,
    ) -> TraceBuildResult:
        """Build TraceBuildResult for grouped stacked bars."""
        # Make a copy to avoid SettingWithCopyWarning
        data = data.copy()

        # Ensure group column is string
        data[group_col] = data[group_col].astype(str)

        # Apply Group Filter
        if config.get("group_filter") is not None:
            data = pd.DataFrame(data[data[group_col].isin(config["group_filter"])])

        # Get ordered categories and groups
        categories, groups = self._get_ordered_categories_and_groups(data, x_col, group_col, config)

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
        distinction_shapes = coord_result["shapes"]
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

        # Apply numbered X-axis labels (replace verbose ticks with indices)
        tick_text, numbered_legend = self._apply_numbered_xaxis(tick_text, config)

        # Build custom_x_ticks
        custom_x_ticks: dict[str, list[Any]] = {"vals": tick_vals, "text": tick_text}

        # Handle numbered xaxis: hide ticks only when numbered ticks are off
        if numbered_legend is not None and not config.get("show_numbered_ticks", False):
            custom_x_ticks["hide_ticks"] = [True]

        # Combine shapes
        existing_shapes = config.get("shapes", []) or []
        if not isinstance(existing_shapes, list):
            existing_shapes = []
        all_shapes = existing_shapes + distinction_shapes

        # Build annotations
        layout_annotations = self._build_category_annotations(cat_centers, config)

        # Add totals if requested
        if config.get("show_totals"):
            totals_annotations = self._build_totals_annotations(data, "__x_coord", config)
            layout_annotations.extend(totals_annotations)

        # Add numbered legend annotation if enabled
        if numbered_legend is not None:
            layout_annotations.append(numbered_legend)

        return TraceBuildResult(
            traces=traces,
            barmode="stack",
            shapes=all_shapes,
            custom_x_ticks=custom_x_ticks,
            layout_annotations=layout_annotations,
            secondary_y=dual_axis,
        )

    def _get_ordered_categories_and_groups(
        self, data: pd.DataFrame, x_col: str, group_col: str, config: dict[str, Any]
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
        config: dict[str, Any],
    ) -> tuple[pd.DataFrame, list[str], list[str]]:
        """Apply renames to data and ordered lists."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import apply_renames

        return apply_renames(data, x_col, group_col, categories, groups, config)

    def _build_coordinate_map(
        self,
        categories: list[str],
        groups: list[str],
        data: pd.DataFrame,
        x_col: str,
        group_col: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Build coordinate mapping for grouped bars using centralized utility."""
        return GroupedBarUtils.calculate_grouped_coordinates(
            categories=categories, groups=groups, config=config
        )

    def _apply_numbered_xaxis(
        self,
        tick_text: list[str],
        config: dict[str, Any],
    ) -> tuple[list[str], dict[str, Any] | None]:
        """Replace tick labels with numbered indices and build legend annotation."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            apply_numbered_xaxis,
        )

        return apply_numbered_xaxis(tick_text, config)

    def _build_category_annotations(
        self, cat_centers: list[tuple[float, str]], config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Build annotations for category labels (grouped bars only)."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            build_category_annotations,
        )

        return build_category_annotations(cat_centers, config)

    def apply_common_layout(self, fig: go.Figure, config: dict[str, Any]) -> go.Figure:
        """Apply common layout and enforce hover template."""
        fig = super().apply_common_layout(fig, config)

        # Enforce hover template for this specific plot type
        # We need to make sure this overwrites what base_plot does
        hover_template = (
            "<b>%{x}</b><br>"
            "Value: %{y:.4f}<br>"
            "<b>Total: %{customdata:.4f}</b>"
            "<extra></extra>"
        )
        fig.update_traces(hovertemplate=hover_template)

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

    # ------------------------------------------------------------------
    # Dual-axis helpers
    # ------------------------------------------------------------------

    def _apply_dual_axis_titles(self, fig: go.Figure, config: dict[str, Any]) -> None:
        """Apply Y-axis titles as symmetrical annotations for dual-axis mode."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            apply_dual_axis_titles,
        )

        apply_dual_axis_titles(fig, config)

    def _apply_separate_legends(self, fig: go.Figure, config: dict[str, Any]) -> None:
        """Split traces into separate legends for left and right axis groups."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            apply_separate_legends,
        )

        apply_separate_legends(fig, config)

    def _render_dual_axis_display_settings(
        self, saved_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Render dual-axis display settings: grid, typography, legend."""
        from src.web.components.plotting.config.dual_axis_settings import (
            render_dual_axis_display_settings,
        )

        render_dual_axis_display_settings(saved_config, config, self.plot_id)

    def _render_secondary_legend_controls(
        self, saved_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Render full legend controls for the secondary (right-axis) legend."""
        from src.web.components.plotting.config.dual_axis_settings import (
            render_secondary_legend_controls,
        )

        render_secondary_legend_controls(saved_config, config, self.plot_id)

    def _render_right_axis_dot_settings(
        self, saved_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Render dot & line settings for the right (secondary) Y-axis."""
        from src.web.components.plotting.config.dual_axis_settings import (
            render_right_axis_dot_settings,
        )

        render_right_axis_dot_settings(saved_config, config, self.plot_id)

    def _build_right_axis_traces(
        self,
        data: pd.DataFrame,
        x_coord_col: str,
        y_cols: list[str],
        trace_type: str,
        bar_width: float | None,
        config: dict[str, Any],
    ) -> list[TraceConfig]:
        """Build traces for the secondary (right) Y-axis."""
        from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
            build_right_axis_traces,
        )

        return build_right_axis_traces(data, x_coord_col, y_cols, trace_type, bar_width, config)

    def get_legend_column(self, config: dict[str, Any]) -> str | None:
        """Get legend column for grouped stacked bar plot."""
        return None
