"""Grouped stacked bar plot implementation."""

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.plotting.types.stacked_bar_plot import StackedBarPlot
from src.plotting.utils import GroupedBarUtils
from src.web.ui.components.plot_config_components import PlotConfigComponents


class GroupedStackedBarPlot(StackedBarPlot):
    """Grouped stacked bar plot with support for multiple stacked statistics and grouping."""

    def __init__(self, plot_id: int, name: str):
        # Initialize with BasePlot's __init__ to set correct plot_type
        super(StackedBarPlot, self).__init__(plot_id, name, "grouped_stacked_bar")

    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for grouped stacked bar plot."""
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = data.select_dtypes(include=["object"]).columns.tolist()

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
                help="The variable displayed on the X-axis within the major group (e.g., Configuration)",  # noqa: E501
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

        # Renaming Options (Delegated to Advanced Options now)
        # Renaming handled by standardized 'Series Configuration' in Advanced Options.

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

        # 6. Annotations
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

    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create grouped stacked bar plot figure."""
        x_col = config.get("x")
        group_col = config.get("group")
        y_cols = config.get("y_columns", [])

        # If no group column, delegate to parent's simple stacked bar implementation
        if not group_col:
            return super().create_figure(data, config)

        fig = go.Figure()

        if not x_col or not y_cols:
            fig.update_layout(title="Please select X axis and at least one Statistic")
            return fig

        # Prepare data using parent's method
        data = self._prepare_data(data, x_col, y_cols, config)

        # Define hover template
        hover_template = self._get_hover_template()

        # Create grouped figure
        fig = self._create_grouped_figure(
            fig, data, x_col, group_col, y_cols, config, hover_template
        )

        fig.update_layout(
            title=config.get("title", ""),
            yaxis_title=config.get("ylabel", "Value"),
            legend_title=config.get("legend_title", "Statistics"),
        )

        return fig

    def _create_grouped_figure(
        self,
        fig: go.Figure,
        data: pd.DataFrame,
        x_col: str,
        group_col: str,
        y_cols: List[str],
        config: Dict[str, Any],
        hover_template: str,
    ) -> go.Figure:
        """Create figure for grouped stacked bars."""
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

        # Add bar traces
        for y_col in y_cols:
            fig = self._add_bar_trace(
                fig, data, y_col, "__x_coord", bar_width, hover_template, config
            )

        # Update layout for grouped bars
        fig.update_layout(
            barmode="stack",
            xaxis=dict(
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text,
                title=config.get("xlabel", x_col),
            ),
        )

        # Combine shapes
        existing_shapes = config.get("shapes", []) or []
        if not isinstance(existing_shapes, list):
            existing_shapes = []
        fig.update_layout(shapes=existing_shapes + distinction_shapes)

        # Build annotations
        annotations = self._build_category_annotations(cat_centers, config)

        # Add totals if requested
        if config.get("show_totals"):
            totals_annotations = self._build_totals_annotations(data, "__x_coord", config)
            annotations.extend(totals_annotations)

        fig.update_layout(annotations=annotations)

        return fig

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

        return fig

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for grouped stacked bar plot."""
        return None
