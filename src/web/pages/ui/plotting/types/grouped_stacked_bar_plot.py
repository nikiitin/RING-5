"""Grouped stacked bar plot implementation."""

import math
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.web.pages.ui.components.plot_config_components import PlotConfigComponents
from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot
from src.web.pages.ui.plotting.utils import GroupedBarUtils


class GroupedStackedBarPlot(StackedBarPlot):
    """Grouped stacked bar plot with support for multiple stacked statistics and grouping."""

    def __init__(self, plot_id: int, name: str):
        # Call through MRO (StackedBarPlot → BarPlot → BasePlot)
        super().__init__(plot_id, name)
        # Override plot_type set by parent chain ("stacked_bar" → "grouped_stacked_bar")
        self.plot_type: str = "grouped_stacked_bar"

    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for grouped stacked bar plot."""
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = data.select_dtypes(include=["object", "string"]).columns.tolist()

        col1, col2 = st.columns(2)

        with col1:
            # X-axis (Major Group)
            x_default_idx = 0
            if saved_config.get("x") and saved_config["x"] in (categorical_cols + numeric_cols):
                x_default_idx = (categorical_cols + numeric_cols).index(saved_config["x"])

            x_column = st.selectbox(
                "Major Grouping (Outer)",
                options=categorical_cols + numeric_cols,
                index=x_default_idx,
                key=f"x_{self.plot_id}",
                help="The main outer category (e.g., Benchmark)",
            )

            # Sub-group (Minor Group)
            group_default_idx = 0
            if saved_config.get("group") and saved_config["group"] in categorical_cols:
                group_default_idx = categorical_cols.index(saved_config["group"])

            # Filter out None from categorical_cols for selectbox
            filtered_cols: List[str] = [col for col in categorical_cols if col is not None]
            options_list: List[Optional[str]] = [None] + filtered_cols
            group_column = st.selectbox(
                "X-Axis / Minor Grouping (Inner)",
                options=options_list,
                index=group_default_idx + 1 if saved_config.get("group") else 0,
                key=f"group_{self.plot_id}",
                help=(
                    "The variable displayed on the X-axis"
                    " within the major group"
                    " (e.g., Configuration)"
                ),
            )

        with col2:
            # Y-axis (Statistics to stack)
            default_ys = saved_config.get("y_columns", [])
            # Filter to ensure they exist
            default_ys = [y for y in default_ys if y in numeric_cols]

            y_columns = st.multiselect(
                "Statistics to Stack (Y-axis)",
                options=numeric_cols,
                default=default_ys,
                key=f"y_multiselect_{self.plot_id}",
                help="Select multiple statistics to stack on top of each other",
            )

            # Title & Labels
            default_title = saved_config.get("title", f"Stacked Statistics by {x_column}")
            default_xlabel = saved_config.get("xlabel", x_column)
            default_ylabel = saved_config.get("ylabel", "Value")

            label_config = PlotConfigComponents.render_title_labels_section(
                saved_config=saved_config,
                plot_id=self.plot_id,
                default_title=default_title,
                default_xlabel=default_xlabel,
                default_ylabel=default_ylabel,
                include_legend_title=True,
                default_legend_title=saved_config.get("legend_title", ""),
            )
            title = label_config["title"]
            xlabel = label_config["xlabel"]
            ylabel = label_config["ylabel"]
            legend_title = label_config["legend_title"]

        # ── Dual Axis ──────────────────────────────────────────
        st.markdown("#### Dual Axis (Secondary Y)")
        dual_axis: bool = st.checkbox(
            "Enable Secondary Y-axis",
            value=saved_config.get("dual_axis", False),
            key=f"dual_axis_{self.plot_id}",
            help=(
                "Adds a right Y-axis with its own columns. "
                "Use with Split-Apply shaper for independent transforms."
            ),
        )

        y_columns_right: List[str] = []
        right_axis_type: str = "bars"
        ylabel_right: str = ""

        if dual_axis:
            da1, da2 = st.columns(2)
            with da1:
                right_axis_type = (
                    st.segmented_control(
                        "Right-axis trace type",
                        options=["bars", "dots"],
                        default=saved_config.get("right_axis_type", "bars"),
                        key=f"right_type_{self.plot_id}",
                    )
                    or "bars"
                )
            with da2:
                ylabel_right = st.text_input(
                    "Right Y-axis Label",
                    value=saved_config.get("ylabel_right", ""),
                    key=f"ylabel_right_{self.plot_id}",
                )

            available_right: List[str] = [c for c in numeric_cols if c not in y_columns]
            default_right: List[str] = [
                c for c in saved_config.get("y_columns_right", []) if c in available_right
            ]
            y_columns_right = st.multiselect(
                "Right Y-axis columns",
                options=available_right,
                default=default_right,
                key=f"y_right_{self.plot_id}",
                help="Numeric columns plotted on the secondary (right) Y-axis.",
            )

        # Filter Options
        st.markdown("#### Filter Data")
        x_values, group_values = PlotConfigComponents.render_filter_multiselects(
            data=data,
            x_col=x_column,
            group_col=group_column,
            saved_config=saved_config,
            plot_id=self.plot_id,
            x_label=f"Filter {x_column} (X-axis)" if x_column else "Filter X values",
            group_label=f"Filter {group_column} (Sub-group)" if group_column else "Filter Groups",
        )

        return {
            "x": x_column,
            "group": group_column,
            "y_columns": y_columns,
            "y": y_columns[0] if y_columns else None,  # For compatibility
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "legend_title": legend_title,
            "x_filter": x_values,
            "group_filter": group_values,
            "dual_axis": dual_axis,
            "right_axis_type": right_axis_type,
            "y_columns_right": y_columns_right,
            "ylabel_right": ylabel_right,
            "_needs_advanced": True,
        }

    def _render_stack_total_options(
        self, saved_config: Dict[str, Any], config: Dict[str, Any]
    ) -> None:
        """Render options for Stack Totals."""
        st.markdown("**Stack Totals**")
        c1, c2 = st.columns(2)
        with c1:
            config["show_totals"] = st.checkbox(
                "Show Stack Totals",
                value=saved_config.get("show_totals", False),
                key=f"show_tot_{self.plot_id}",
            )
        with c2:
            if config["show_totals"]:
                config["net_total_format"] = st.text_input(
                    "Format",
                    value=saved_config.get("net_total_format", ".2f"),
                    help="Python format string (e.g. .2f)",
                    key=f"tot_fmt_{self.plot_id}",
                )

        if config["show_totals"]:
            c3, c4 = st.columns(2)
            with c3:
                config["total_font_size"] = st.number_input(
                    "Font Size",
                    value=saved_config.get("total_font_size", 12),
                    min_value=8,
                    max_value=30,
                    key=f"tot_sz_{self.plot_id}",
                )
                config["total_font_color"] = st.color_picker(
                    "Font Color",
                    value=saved_config.get("total_font_color", "#000000"),
                    key=f"tot_col_{self.plot_id}",
                )
            with c4:
                config["total_position"] = st.selectbox(
                    "Position",
                    options=["Outside", "Inside"],
                    index=["Outside", "Inside"].index(
                        saved_config.get("total_position", "Outside")
                    ),
                    key=f"tot_pos_{self.plot_id}",
                    help="Outside: Always on top. Inside: Configurable anchor.",
                )

                if config["total_position"] == "Inside":
                    config["total_anchor"] = st.selectbox(
                        "Anchor (Inside)",
                        options=["Start", "Middle", "End"],
                        index=["Start", "Middle", "End"].index(
                            saved_config.get("total_anchor", "End")
                        ),
                        key=f"tot_anc_{self.plot_id}",
                        help="Start=Bottom, End=Top",
                    )

        if config["show_totals"]:
            c5, c6 = st.columns(2)
            with c5:
                config["total_offset"] = st.number_input(
                    "Vertical Offset (px)",
                    value=saved_config.get("total_offset", 0),
                    step=1,
                    key=f"tot_off_{self.plot_id}",
                    help="Adjustment in pixels (positive = up, negative = down)",
                )
            with c6:
                config["total_rotation"] = st.number_input(
                    "Rotation",
                    value=int(saved_config.get("total_rotation", 0)),
                    step=45,
                    min_value=-360,
                    max_value=360,
                    key=f"tot_rot_{self.plot_id}",
                )

        if config["show_totals"]:
            config["total_threshold"] = st.number_input(
                "Minimum Threshold",
                value=float(saved_config.get("total_threshold", 0.0)),
                step=0.1,
                key=f"tot_thresh_{self.plot_id}",
                help="Only show totals greater than this value.",
            )

    def render_theme_options(
        self, saved_config: Dict[str, Any], items: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Override to add specific styling options."""
        # Get base theme options
        # Fix: Pass stacks as items to ensure correct Series Styling
        stacks = saved_config.get("y_columns", [])
        config = super().render_theme_options(saved_config, items=stacks)

        # Add Groups Styling
        st.markdown("#### Major Group Styling")
        c1, c2, c3 = st.columns(3)
        with c1:
            config["major_label_size"] = st.number_input(
                "Major Label Font Size",
                value=saved_config.get("major_label_size", 14),
                key=f"maj_sz_th_{self.plot_id}",
            )
        with c2:
            config["major_label_color"] = st.color_picker(
                "Major Label Font Color",
                value=saved_config.get("major_label_color", "#000000"),
                key=f"maj_col_th_{self.plot_id}",
            )
        with c3:
            config["major_label_offset"] = st.number_input(
                "Vertical Offset",
                value=float(saved_config.get("major_label_offset", -0.15)),
                step=0.05,
                max_value=0.0,
                min_value=-1.0,
                format="%.2f",
                key=f"maj_off_th_{self.plot_id}",
                help="Adjust vertical position of Major Group labels (negative values move down)",
            )

        # Add Stack Totals
        self._render_stack_total_options(saved_config, config)

        st.markdown("**Visual Distinction**")
        d1, d2 = st.columns(2)
        with d1:
            config["show_separators"] = st.checkbox(
                "Show Vertical Separators",
                value=saved_config.get("show_separators", True),
                key=f"show_sep_{self.plot_id}",
            )
            config["separator_color"] = st.color_picker(
                "Separator Color",
                value=saved_config.get("separator_color", "#E0E0E0"),
                key=f"sep_col_{self.plot_id}",
            )
        with d2:
            config["shade_alternate"] = st.checkbox(
                "Shade Alternate Groups",
                value=saved_config.get("shade_alternate", False),
                key=f"shade_alt_{self.plot_id}",
            )
            config["shade_color"] = st.color_picker(
                "Shade Color",
                value=saved_config.get("shade_color", "#F5F5F5"),
                key=f"shade_col_{self.plot_id}",
            )

        st.markdown("**Summary Group Isolation (Last Group)**")
        d3, d4 = st.columns(2)
        with d3:
            config["isolate_last_group"] = st.checkbox(
                "Isolate Last Group",
                value=saved_config.get("isolate_last_group", False),
                key=f"iso_last_{self.plot_id}",
                help="Adds extra space and a distinct separator before the last major group.",
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

        st.markdown("**Numbered X-axis Labels**")
        e1, e2 = st.columns(2)
        with e1:
            config["numbered_xaxis"] = st.checkbox(
                "Use Numbered Labels",
                value=saved_config.get("numbered_xaxis", False),
                key=f"num_xaxis_{self.plot_id}",
                help=(
                    "Replace X-axis tick labels with numbered indices and "
                    "show a secondary legend box mapping numbers to original labels."
                ),
            )
        if config["numbered_xaxis"]:
            with e2:
                config["numbered_legend_size"] = st.number_input(
                    "Legend Font Size",
                    value=int(saved_config.get("numbered_legend_size", 10)),
                    min_value=6,
                    max_value=24,
                    key=f"num_leg_sz_{self.plot_id}",
                )
            e3, e4 = st.columns(2)
            with e3:
                config["numbered_legend_x"] = st.number_input(
                    "Legend X Position",
                    value=float(saved_config.get("numbered_legend_x", 1.02)),
                    step=0.05,
                    min_value=-0.5,
                    max_value=2.0,
                    format="%.2f",
                    key=f"num_leg_x_{self.plot_id}",
                    help="Horizontal position (0=left, 1=right edge, >1=outside right)",
                )
            with e4:
                config["numbered_legend_y"] = st.number_input(
                    "Legend Y Position",
                    value=float(saved_config.get("numbered_legend_y", 0.5)),
                    step=0.05,
                    min_value=-1.0,
                    max_value=2.0,
                    format="%.2f",
                    key=f"num_leg_y_{self.plot_id}",
                    help="Vertical position (0=bottom, 1=top, <0=below plot)",
                )
            e5, e6 = st.columns(2)
            with e5:
                config["numbered_legend_columns"] = st.number_input(
                    "Columns",
                    value=int(saved_config.get("numbered_legend_columns", 1)),
                    min_value=1,
                    max_value=10,
                    key=f"num_leg_cols_{self.plot_id}",
                    help="Number of columns inside the legend box",
                )
            with e6:
                config["numbered_legend_bgcolor"] = st.color_picker(
                    "Background",
                    value=saved_config.get("numbered_legend_bgcolor", "#FFFFFF"),
                    key=f"num_leg_bg_{self.plot_id}",
                )

        return config

    def render_advanced_options(
        self, saved_config: Dict[str, Any], data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """Custom Advanced Options for Grouped Stacked Bar."""
        config: Dict[str, Any] = {}

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
            y_cols_right: List[str] = saved_config.get("y_columns_right", [])
            if y_cols_right:
                st.markdown("#### Right-Axis Series Configuration")
                with st.expander("Reorder & Rename Right-Axis Series"):
                    st.markdown("**Order**")
                    current_right_order = list(y_cols_right)
                    new_right_order = self.render_reorderable_list(
                        "Right-Axis Order", current_right_order, "right_ord"
                    )
                    if new_right_order != current_right_order:
                        config["y_columns_right"] = new_right_order

                    st.markdown("**Rename**")
                    right_renaming = self.style_manager.render_series_renaming_ui(
                        saved_config, data, items=y_cols_right
                    )

                    if "series_styles" not in config:
                        config["series_styles"] = {}

                    for k, v in right_renaming.items():
                        if k not in config["series_styles"]:
                            config["series_styles"][k] = v
                        else:
                            config["series_styles"][k].update(v)

        # 3. Stack Configuration
        # Restore functionality handled by BasePlot's generic "Series Configuration"
        # We explicitly pass y_columns as items to ensure we rename the stacks/statistics,
        # not the internal 'group' column.
        y_cols = saved_config.get("y_columns", [])
        if y_cols:
            st.markdown("#### Stack / Legend Configuration")

            with st.expander("Reorder & Rename"):
                # A. Reorder Stacks
                st.markdown("**Order**")
                # We allow reordering the y_columns list
                current_order = list(y_cols)
                new_order = self.render_reorderable_list("Stack Order", current_order, "stack_ord")
                if new_order != current_order:
                    config["y_columns"] = new_order

                # B. Rename Series
                st.markdown("**Rename**")
                renaming_styles = self.style_manager.render_series_renaming_ui(
                    saved_config, data, items=y_cols  # Explicitly pass stack names
                )

                if "series_styles" not in config:
                    config["series_styles"] = {}

                for k, v in renaming_styles.items():
                    if k not in config["series_styles"]:
                        config["series_styles"][k] = v
                    else:
                        config["series_styles"][k].update(v)

        # 4. Major Group Configuration (Original X)
        x_col = saved_config.get("x")
        if data is not None and x_col and x_col in data.columns:
            st.markdown("#### Major Grouping (Outer) Configuration")
            with st.expander("Reorder & Rename Major Groups"):
                # Reorder
                st.markdown("**Order**")
                unique_x = sorted(data[x_col].unique().tolist())
                config["xaxis_order"] = self.render_reorderable_list(
                    "Major Group Order",
                    unique_x,
                    "xaxis",
                    default_order=saved_config.get("xaxis_order"),
                )

                # Rename
                st.markdown("**Rename**")
                config["xaxis_labels"] = self.style_manager.render_xaxis_labels_ui(
                    saved_config, data, key_prefix="maj_rename"
                )

        # 5. Minor Group Configuration (Original Group)
        group_col = saved_config.get("group")
        if data is not None and group_col and group_col in data.columns:
            st.markdown("#### X-Axis / Minor Grouping (Inner) Configuration")
            with st.expander("Reorder & Rename Minor Groups"):
                unique_g = sorted(data[group_col].unique().tolist())
                config["group_order"] = self.render_reorderable_list(
                    "Minor Group Order",
                    unique_g,
                    "group",
                    default_order=saved_config.get("group_order"),
                )

                st.markdown("**Rename Minor Groups**")
                # Use style_manager but mock the config to point 'x' to 'group'
                temp_config = saved_config.copy()
                temp_config["x"] = group_col
                temp_config["xaxis_labels"] = saved_config.get("group_renames", {})

                config["group_renames"] = self.style_manager.render_xaxis_labels_ui(
                    temp_config, data, key_prefix="min_rename"
                )

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

    def create_traces(self, data: pd.DataFrame, config: Dict[str, Any]) -> TraceBuildResult:
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
        y_cols_right: List[str] = config.get("y_columns_right", []) if dual_axis else []
        all_y_cols: List[str] = y_cols + [c for c in y_cols_right if c not in y_cols]
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
        y_cols: List[str],
        config: Dict[str, Any],
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
            data = data[data[group_col].isin(config["group_filter"])]

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
        traces: List[TraceConfig] = []
        for y_col in y_cols:
            trace = self._build_bar_trace(
                data, y_col, "__x_coord", bar_width, hover_template, config
            )
            traces.append(trace)

        # Build RIGHT-axis traces (dual-axis mode)
        if dual_axis:
            y_cols_right: List[str] = config.get("y_columns_right", [])
            right_type: str = config.get("right_axis_type", "bars")
            right_traces = self._build_right_axis_traces(
                data, "__x_coord", y_cols_right, right_type, bar_width, config
            )
            traces.extend(right_traces)

        # Apply numbered X-axis labels (replace verbose ticks with indices)
        tick_text, numbered_legend = self._apply_numbered_xaxis(tick_text, config)

        # Build custom_x_ticks
        custom_x_ticks: Dict[str, List[Any]] = {"vals": tick_vals, "text": tick_text}

        # Handle numbered xaxis: hide ticks via custom_x_ticks with empty text
        if numbered_legend is not None:
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
        self, data: pd.DataFrame, x_col: str, group_col: str, config: Dict[str, Any]
    ) -> tuple[List[str], List[str]]:
        """Get ordered lists of categories and groups."""
        # Categories
        if config.get("xaxis_order"):
            xaxis_order_str = [str(x) for x in config["xaxis_order"]]
            ordered_cats = [c for c in xaxis_order_str if c in data[x_col].unique()]
            missing = [c for c in sorted(data[x_col].unique()) if c not in ordered_cats]
            ordered_cats.extend(missing)
        else:
            ordered_cats = sorted(data[x_col].unique())

        # Groups
        if config.get("group_order"):
            group_order_str = [str(g) for g in config["group_order"]]
            ordered_groups = [g for g in group_order_str if g in data[group_col].unique()]
            missing = [g for g in sorted(data[group_col].unique()) if g not in ordered_groups]
            ordered_groups.extend(missing)
        else:
            ordered_groups = sorted(data[group_col].unique())

        return ordered_cats, ordered_groups

    def _apply_renames(
        self,
        data: pd.DataFrame,
        x_col: str,
        group_col: str,
        categories: List[str],
        groups: List[str],
        config: Dict[str, Any],
    ) -> tuple[pd.DataFrame, List[str], List[str]]:
        """Apply renames to data and ordered lists."""
        # X-axis renames
        x_renames = config.get("xaxis_labels", {})
        if x_renames:
            data[x_col] = data[x_col].replace(x_renames)

        renamed_categories = [x_renames.get(cat, cat) for cat in categories]

        # Group renames
        group_renames = config.get("group_renames", {})
        if group_renames:
            data[group_col] = data[group_col].replace(group_renames)

        renamed_groups = [group_renames.get(grp, grp) for grp in groups]

        return data, renamed_categories, renamed_groups

    def _build_coordinate_map(
        self,
        categories: List[str],
        groups: List[str],
        data: pd.DataFrame,
        x_col: str,
        group_col: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build coordinate mapping for grouped bars using centralized utility."""
        return GroupedBarUtils.calculate_grouped_coordinates(
            categories=categories, groups=groups, config=config
        )

    def _apply_numbered_xaxis(
        self,
        tick_text: List[str],
        config: Dict[str, Any],
    ) -> tuple[List[str], Optional[Dict[str, Any]]]:
        """Replace tick labels with numbered indices and build legend annotation.

        When enabled via config["numbered_xaxis"], replaces verbose X-axis labels
        with numbered indices (1, 2, 3, ...) and produces a secondary legend
        annotation mapping numbers back to the original labels.

        Args:
            tick_text: Original tick label strings (may repeat across categories).
            config: Plot configuration dict.

        Returns:
            Tuple of (possibly-replaced tick_text, legend annotation dict or None).
        """
        if not config.get("numbered_xaxis"):
            return tick_text, None

        # Unique groups preserving insertion order
        unique_groups: List[str] = list(dict.fromkeys(tick_text))

        # Return empty tick text — X-ticks are fully hidden when numbered
        # xaxis is on; the boxed legend annotation is the only reference.
        numbered_text: List[str] = [""] * len(tick_text)

        # Build legend text — vertical list inside a bordered box
        legend_parts: List[str] = [f"{i + 1}. {g}" for i, g in enumerate(unique_groups)]
        max_cols: int = int(config.get("numbered_legend_columns", 1))
        if max_cols > 1:
            # Lay out items **column-wise** (top-to-bottom, then next column)
            # to match the reading order of the actual legend, which also
            # fills columns top-to-bottom when ncols > 1.
            #
            # Example with 4 items [A, B, C, D] and 2 columns:
            #   Row 0: 1. A  3. C
            #   Row 1: 2. B  4. D
            #
            # Compute per-column max widths and pad ALL columns so that
            # every row is the same total width — this prevents the
            # bounding box from showing extra whitespace on shorter rows.
            n_items: int = len(legend_parts)
            n_rows: int = math.ceil(n_items / max_cols)

            col_widths: List[int] = []
            for col in range(max_cols):
                col_items = [
                    legend_parts[col * n_rows + r]
                    for r in range(n_rows)
                    if col * n_rows + r < n_items
                ]
                col_widths.append(max(len(p) for p in col_items) if col_items else 0)

            sep = "  "
            rows: List[str] = []
            for row_idx in range(n_rows):
                parts: List[str] = []
                for col_idx in range(max_cols):
                    item_idx = col_idx * n_rows + row_idx
                    if item_idx < n_items:
                        parts.append(legend_parts[item_idx].ljust(col_widths[col_idx]))
                rows.append(sep.join(parts))
            legend_text: str = "<br>".join(rows)
        else:
            # One entry per line (vertical, like a standard legend)
            legend_text = "<br>".join(legend_parts)

        legend_x: float = float(config.get("numbered_legend_x", 1.02))
        legend_y: float = float(config.get("numbered_legend_y", 0.5))
        bgcolor: str = str(config.get("numbered_legend_bgcolor", "#FFFFFF"))

        legend_annotation: Dict[str, Any] = dict(
            x=legend_x,
            y=legend_y,
            xref="paper",
            yref="paper",
            text=legend_text,
            showarrow=False,
            font=dict(size=int(config.get("numbered_legend_size", 10))),
            align="left",
            xanchor="left",
            yanchor="middle",
            bordercolor="#333333",
            borderwidth=1,
            borderpad=6,
            bgcolor=bgcolor,
        )

        return numbered_text, legend_annotation

    def _build_category_annotations(
        self, cat_centers: List[tuple[float, str]], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build annotations for category labels (grouped bars only)."""
        return GroupedBarUtils.build_category_annotations(
            cat_centers=cat_centers,
            font_size=config.get("major_label_size", 14),
            font_color=config.get("major_label_color", "#000000"),
            y_offset=config.get("major_label_offset", -0.15),
        )

    def apply_common_layout(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
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
                showgrid=config.get("show_left_grid", True),
                secondary_y=False,
            )
            fig.update_yaxes(
                showgrid=config.get("show_right_grid", False),
                secondary_y=True,
            )

            # 3. Legend unification
            if not config.get("unified_legend", True):
                self._apply_separate_legends(fig, config)

        return fig

    # ------------------------------------------------------------------
    # Dual-axis helpers
    # ------------------------------------------------------------------

    def _render_dual_axis_display_settings(
        self, saved_config: Dict[str, Any], config: Dict[str, Any]
    ) -> None:
        """Render dual-axis display settings: grid, typography, legend.

        Shown only when ``dual_axis`` is True.

        Args:
            saved_config: Previously saved configuration.
            config: Current configuration dict to update in-place.
        """
        st.markdown("#### Dual Axis Display")

        # Grid Lines
        st.markdown("**Grid Lines**")
        g1, g2 = st.columns(2)
        with g1:
            config["show_left_grid"] = st.checkbox(
                "Show Left Y-axis Grid",
                value=saved_config.get("show_left_grid", True),
                key=f"show_left_grid_{self.plot_id}",
            )
        with g2:
            config["show_right_grid"] = st.checkbox(
                "Show Right Y-axis Grid",
                value=saved_config.get("show_right_grid", False),
                key=f"show_right_grid_{self.plot_id}",
            )

        # Secondary Y-axis Typography
        # Fall back to primary axis values when not explicitly set
        _pri_title_fs: int = int(saved_config.get("yaxis_title_font_size", 14))
        _pri_tick_fs: int = int(saved_config.get("yaxis_tickfont_size", 12))
        _pri_tick_col: str = saved_config.get("yaxis_tickfont_color", "#444444")
        _pri_standoff: int = int(saved_config.get("yaxis_title_standoff", 0))

        st.markdown("**Right Y-Axis Typography**")
        t1, t2 = st.columns(2)
        with t1:
            config["yaxis2_title_font_size"] = st.number_input(
                "Right Y-Axis Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("yaxis2_title_font_size", _pri_title_fs),
                key=f"y2_title_sz_{self.plot_id}",
            )
            config["yaxis2_title_standoff"] = st.slider(
                "Right Y-Axis Title Standoff",
                min_value=0,
                max_value=100,
                value=saved_config.get("yaxis2_title_standoff", _pri_standoff),
                key=f"y2_title_standoff_{self.plot_id}",
                help="Distance between the right Y-axis ticks and the title.",
            )
        with t2:
            config["yaxis2_tickfont_size"] = st.number_input(
                "Right Y-Axis Tick Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("yaxis2_tickfont_size", _pri_tick_fs),
                key=f"y2_tick_sz_{self.plot_id}",
            )
            config["yaxis2_tickfont_color"] = st.color_picker(
                "Right Y-Axis Tick Color",
                saved_config.get("yaxis2_tickfont_color", _pri_tick_col),
                key=f"y2_tick_col_{self.plot_id}",
            )

        # Legend Unification
        st.markdown("**Legend**")
        config["unified_legend"] = st.checkbox(
            "Unified Legend (all items in one legend)",
            value=saved_config.get("unified_legend", True),
            key=f"unified_legend_{self.plot_id}",
            help=(
                "When enabled, left and right axis items share a single legend "
                "with full position and styling controls.  When disabled, each "
                "axis group gets its own legend."
            ),
        )

        # When using separate legends, show full controls for legend2
        if not config.get("unified_legend", True):
            self._render_secondary_legend_controls(saved_config, config)

    def _apply_dual_axis_titles(self, fig: go.Figure, config: Dict[str, Any]) -> None:
        """Apply Y-axis titles as symmetrical annotations for dual-axis mode.

        When dual-axis is active **both** Y labels are rendered as
        annotations so they look identical (same font family, size and
        colour).  The only differences are:

        * Primary  (left):  ``textangle = -90``  at ``x = 0``
        * Secondary (right): ``textangle =  90`` at ``x = 1``

        The secondary config keys (``yaxis2_title_font_size``,
        ``yaxis2_title_standoff``) fall back to their primary
        counterparts when not explicitly set, guaranteeing visual
        symmetry by default.

        Also applies secondary Y-axis tick styling.

        Args:
            fig: Plotly figure (``make_subplots`` with ``secondary_y``).
            config: Full plot configuration.
        """
        # ── Resolve primary settings ─────────────────────────────
        # Read from config (the style chain may not have set the native
        # title yet, so we cannot rely on fig.layout.yaxis.title.text).
        ylabel_left: str = config.get("ylabel", "")
        ylabel_right: str = config.get("ylabel_right", "")

        primary_font_size: int = int(config.get("yaxis_title_font_size", 14))
        primary_standoff: int = int(config.get("yaxis_title_standoff", 0))
        font_color: str = config.get("axis_color", "#444444")

        # ── Resolve secondary settings (fall back to primary) ────
        yaxis2_fs_raw: Any = config.get("yaxis2_title_font_size")
        secondary_font_size: int = (
            int(yaxis2_fs_raw) if yaxis2_fs_raw is not None else primary_font_size
        )
        yaxis2_so_raw: Any = config.get("yaxis2_title_standoff")
        secondary_standoff: int = (
            int(yaxis2_so_raw) if yaxis2_so_raw is not None else primary_standoff
        )

        # ── Secondary Y tick styling (fall back to primary) ────
        primary_tick_size: int = int(config.get("yaxis_tickfont_size", 12))
        primary_tick_color: str = config.get("yaxis_tickfont_color", "#444444")

        y2_tick_size_raw: Any = config.get("yaxis2_tickfont_size")
        secondary_tick_size: int = (
            int(y2_tick_size_raw) if y2_tick_size_raw is not None else primary_tick_size
        )
        y2_tick_color_raw: Any = config.get("yaxis2_tickfont_color")
        secondary_tick_color: str = (
            str(y2_tick_color_raw) if y2_tick_color_raw is not None else primary_tick_color
        )

        fig.update_yaxes(
            tickfont=dict(
                size=secondary_tick_size,
                color=secondary_tick_color,
            ),
            secondary_y=True,
        )

        # ── Primary Y title → annotation (if not already done) ──
        if ylabel_left:
            # Clear native title so it doesn't render alongside
            fig.update_yaxes(title_text="", secondary_y=False)

            fig.add_annotation(
                text=ylabel_left,
                x=0,
                y=0.5,
                xref="paper",
                yref="paper",
                xanchor="right",
                yanchor="middle",
                textangle=-90,
                showarrow=False,
                captureevents=False,
                font=dict(size=primary_font_size, color=font_color),
                xshift=-(primary_standoff + 40),
            )

        # ── Secondary Y title → annotation ──────────────────────
        if ylabel_right:
            # Clear native secondary title
            fig.update_yaxes(title_text="", secondary_y=True)

            fig.add_annotation(
                text=ylabel_right,
                x=1.0,
                y=0.5,
                xref="paper",
                yref="paper",
                xanchor="left",
                yanchor="middle",
                textangle=90,
                showarrow=False,
                captureevents=False,
                font=dict(size=secondary_font_size, color=font_color),
                xshift=secondary_standoff + 40,
            )
        else:
            # Ensure the secondary Y title stays cleared
            fig.update_yaxes(title_text="", secondary_y=True)

    def _apply_separate_legends(self, fig: go.Figure, config: Dict[str, Any]) -> None:
        """Split traces into separate legends for left and right axis groups.

        Left-axis traces are assigned to ``legend``, right-axis traces to
        ``legend2``.  ``legend2`` uses position/appearance controls from
        the ``legend2_*`` config keys set by the secondary legend UI.

        Args:
            fig: Plotly figure with dual-axis traces.
            config: Plot configuration dict.
        """
        n_left: int = len(config.get("y_columns", []))

        for i, trace in enumerate(fig.data):
            if i < n_left:
                trace.update(legend="legend")
            else:
                trace.update(legend="legend2")

        # Secondary legend config from user controls (fallback to defaults)
        legend2_cfg: Dict[str, Any] = {
            "x": config.get("legend2_x", 1.0),
            "y": config.get("legend2_y", 1.0),
            "xanchor": config.get("legend2_xanchor", "right"),
            "yanchor": config.get("legend2_yanchor", "top"),
            "orientation": config.get("legend2_orientation", "v"),
        }

        # Font
        legend2_font: Dict[str, Any] = {}
        if config.get("legend2_font_color"):
            legend2_font["color"] = config["legend2_font_color"]
        if config.get("legend2_font_size"):
            legend2_font["size"] = config["legend2_font_size"]

        # Fallback: inherit from primary legend if no secondary font set
        if not legend2_font and fig.layout.legend and fig.layout.legend.font:
            font_obj = fig.layout.legend.font
            if font_obj.size is not None:
                legend2_font["size"] = font_obj.size
            if font_obj.color is not None:
                legend2_font["color"] = font_obj.color

        if legend2_font:
            legend2_cfg["font"] = legend2_font

        # Background & border
        if config.get("legend2_bgcolor"):
            legend2_cfg["bgcolor"] = config["legend2_bgcolor"]
        if config.get("legend2_border_width", 0) > 0:
            legend2_cfg["bordercolor"] = config.get("legend2_border_color", "#000000")
            legend2_cfg["borderwidth"] = config["legend2_border_width"]

        # Title
        legend2_title = config.get("legend2_title")
        if legend2_title:
            legend2_cfg["title"] = dict(text=legend2_title)

        fig.update_layout(
            legend=dict(
                x=0.0,
                y=1.0,
                xanchor="left",
                yanchor="top",
            ),
            legend2=legend2_cfg,
        )

    def _render_secondary_legend_controls(
        self, saved_config: Dict[str, Any], config: Dict[str, Any]
    ) -> None:
        """Render full legend controls for the secondary (right-axis) legend.

        Mirrors the primary legend controls from ``BaseStyleUI`` to give the
        user equivalent control over position, appearance, and sizing.

        Args:
            saved_config: Previously saved configuration.
            config: Current configuration dict to update in-place.
        """
        st.markdown("##### Right-Axis Legend")

        # Position & Orientation
        st.markdown("**Position & Orientation**")
        p1, p2 = st.columns(2)
        with p1:
            config["legend2_orientation"] = st.selectbox(
                "Orientation (Right Legend)",
                options=["v", "h"],
                format_func=lambda x: "Vertical" if x == "v" else "Horizontal",
                index=0 if saved_config.get("legend2_orientation", "v") == "v" else 1,
                key=f"leg2_orient_{self.plot_id}",
            )
            config["legend2_x"] = st.number_input(
                "X Position",
                value=float(saved_config.get("legend2_x", 1.0)),
                step=0.05,
                min_value=-0.5,
                max_value=2.0,
                format="%.2f",
                key=f"leg2_x_{self.plot_id}",
            )
        with p2:
            config["legend2_xanchor"] = st.selectbox(
                "X Anchor",
                options=["auto", "left", "center", "right"],
                index=["auto", "left", "center", "right"].index(
                    saved_config.get("legend2_xanchor", "right")
                ),
                key=f"leg2_xanc_{self.plot_id}",
            )
            config["legend2_y"] = st.number_input(
                "Y Position",
                value=float(saved_config.get("legend2_y", 1.0)),
                step=0.05,
                min_value=-0.5,
                max_value=2.0,
                format="%.2f",
                key=f"leg2_y_{self.plot_id}",
            )

        q1, q2 = st.columns(2)
        with q1:
            config["legend2_yanchor"] = st.selectbox(
                "Y Anchor",
                options=["auto", "top", "middle", "bottom"],
                index=["auto", "top", "middle", "bottom"].index(
                    saved_config.get("legend2_yanchor", "top")
                ),
                key=f"leg2_yanc_{self.plot_id}",
            )

        # Appearance
        st.markdown("**Appearance (Right Legend)**")
        a1, a2 = st.columns(2)
        with a1:
            config["legend2_bgcolor"] = st.color_picker(
                "Background",
                saved_config.get("legend2_bgcolor", "#ffffff"),
                key=f"leg2_bg_{self.plot_id}",
            )
            config["legend2_border_color"] = st.color_picker(
                "Border Color",
                saved_config.get("legend2_border_color", "#000000"),
                key=f"leg2_bord_col_{self.plot_id}",
            )
            config["legend2_border_width"] = st.number_input(
                "Border Width",
                min_value=0,
                max_value=5,
                value=saved_config.get("legend2_border_width", 0),
                key=f"leg2_bord_w_{self.plot_id}",
            )
        with a2:
            config["legend2_font_color"] = st.color_picker(
                "Font Color",
                saved_config.get("legend2_font_color", "#000000"),
                key=f"leg2_font_col_{self.plot_id}",
            )
            config["legend2_font_size"] = st.number_input(
                "Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("legend2_font_size", 12),
                key=f"leg2_font_sz_{self.plot_id}",
            )
            config["legend2_title"] = st.text_input(
                "Legend Title",
                value=saved_config.get("legend2_title", ""),
                key=f"leg2_title_{self.plot_id}",
            )

    def _render_right_axis_dot_settings(
        self, saved_config: Dict[str, Any], config: Dict[str, Any]
    ) -> None:
        """Render dot & line settings for the right (secondary) Y-axis.

        Only displayed when ``dual_axis`` is True and ``right_axis_type``
        is ``"dots"``.

        Args:
            saved_config: Previously saved configuration.
            config: Current configuration dict to update in-place.
        """
        st.markdown("#### Right-Axis Dot & Line Settings")
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            config["right_show_lines"] = st.checkbox(
                "Show lines (right axis)",
                value=saved_config.get("right_show_lines", True),
                key=f"right_show_lines_{self.plot_id}",
            )
        with dc2:
            symbols: List[str] = [
                "circle",
                "square",
                "diamond",
                "cross",
                "x",
                "triangle-up",
                "triangle-down",
            ]
            config["right_dot_symbol"] = st.selectbox(
                "Dot Symbol (right)",
                options=symbols,
                index=(
                    symbols.index(saved_config.get("right_dot_symbol", "circle"))
                    if saved_config.get("right_dot_symbol") in symbols
                    else 0
                ),
                key=f"right_dot_sym_{self.plot_id}",
            )
        with dc3:
            config["right_dot_size"] = st.number_input(
                "Dot Size (right)",
                min_value=2,
                max_value=30,
                value=saved_config.get("right_dot_size", 10),
                key=f"right_dot_size_{self.plot_id}",
            )

        dc4, _ = st.columns(2)
        with dc4:
            config["right_line_width"] = st.number_input(
                "Line Width (right)",
                min_value=1,
                max_value=10,
                value=saved_config.get("right_line_width", 2),
                key=f"right_line_w_{self.plot_id}",
                disabled=not config.get("right_show_lines", True),
            )

    def _build_right_axis_traces(
        self,
        data: pd.DataFrame,
        x_coord_col: str,
        y_cols: List[str],
        trace_type: str,
        bar_width: Optional[float],
        config: Dict[str, Any],
    ) -> List[TraceConfig]:
        """Build traces for the secondary (right) Y-axis.

        Args:
            data: DataFrame with ``x_coord_col`` already mapped.
            x_coord_col: Column name holding numeric X coordinates.
            y_cols: Numeric columns to plot on the right axis.
            trace_type: ``"bars"`` or ``"dots"``.
            bar_width: Width for bar traces (may be None).
            config: Full plot configuration.

        Returns:
            List of TraceConfig for the right axis.
        """
        series_styles: Dict[str, Any] = config.get("series_styles", {})
        traces: List[TraceConfig] = []

        for y_col in y_cols:
            error_y_vals: Optional[List[float]] = None
            if config.get("show_error_bars"):
                sd_col: str = f"{y_col}.sd"
                if sd_col in data.columns:
                    error_y_vals = data[sd_col].tolist()

            style: Dict[str, Any] = series_styles.get(y_col, {})
            trace_name: str = style.get("name", y_col)

            if trace_type == "bars":
                traces.append(
                    BarTraceConfig(
                        name=trace_name,
                        x_positions=data[x_coord_col].tolist(),
                        y=data[y_col].tolist(),
                        bar_width=bar_width if bar_width is not None else 0.8,
                        color=style.get("color", ""),
                        pattern=style.get("pattern", ""),
                        error_y=error_y_vals,
                        yaxis="y2",
                    )
                )
            else:  # dots
                show_lines: bool = config.get("right_show_lines", True)
                if show_lines:
                    traces.append(
                        LineTraceConfig(
                            name=trace_name,
                            x=data[x_coord_col].tolist(),
                            y=data[y_col].tolist(),
                            show_markers=True,
                            marker_symbol=config.get("right_dot_symbol", "circle"),
                            marker_size=config.get("right_dot_size", 10),
                            line_width=float(config.get("right_line_width", 2)),
                            error_y=error_y_vals,
                            yaxis="y2",
                        )
                    )
                else:
                    traces.append(
                        ScatterTraceConfig(
                            name=trace_name,
                            x=data[x_coord_col].tolist(),
                            y=data[y_col].tolist(),
                            marker_symbol=config.get("right_dot_symbol", "circle"),
                            marker_size=config.get("right_dot_size", 10),
                            error_y=error_y_vals,
                            yaxis="y2",
                        )
                    )

        return traces

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for grouped stacked bar plot."""
        return None
