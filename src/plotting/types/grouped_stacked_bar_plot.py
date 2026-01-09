"""Grouped stacked bar plot implementation."""

from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.plotting.base_plot import BasePlot


class GroupedStackedBarPlot(BasePlot):
    """Grouped stacked bar plot with support for multiple stacked statistics."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "grouped_stacked_bar")

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

            group_column = st.selectbox(
                "X-Axis / Minor Grouping (Inner)",
                options=[None] + categorical_cols,
                index=group_default_idx + 1 if saved_config.get("group") else 0,
                key=f"group_{self.plot_id}",
                help="The variable displayed on the X-axis within the major group (e.g., Configuration)",
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

            # Title
            default_title = saved_config.get("title", f"Stacked Statistics by {x_column}")
            title = st.text_input("Title", value=default_title, key=f"title_{self.plot_id}")

            # Labels
            default_xlabel = saved_config.get("xlabel", x_column)
            xlabel = st.text_input("X-label", value=default_xlabel, key=f"xlabel_{self.plot_id}")

            default_ylabel = saved_config.get("ylabel", "Value")
            ylabel = st.text_input("Y-label", value=default_ylabel, key=f"ylabel_{self.plot_id}")

        # Renaming Options (Delegated to Advanced Options now)
        # We removed the manual 'legend_renames' in favor of the standardized 'Series Configuration'
        # in the Advanced Options menu to avoid conflicts.

        # Filter Options
        st.markdown("#### Filter Data")
        col_filter1, col_filter2 = st.columns(2)

        # Filter X values
        x_values = []
        if x_column and x_column in data.columns:
            unique_x = sorted(data[x_column].astype(str).unique())
            default_x = saved_config.get("x_filter", unique_x)
            # Ensure defaults are valid
            default_x = [x for x in default_x if x in unique_x]

            with col_filter1:
                x_values = st.multiselect(
                    f"Filter {x_column} (X-axis)",
                    options=unique_x,
                    default=default_x,
                    key=f"x_filter_{self.plot_id}",
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
                    f"Filter {group_column} (Sub-group)",
                    options=unique_g,
                    default=default_g,
                    key=f"group_filter_{self.plot_id}",
                )

        return {
            "x": x_column,
            "group": group_column,
            "y_columns": y_columns,
            "y": y_columns[0] if y_columns else None,  # For compatibility
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "x_filter": x_values,
            "group_filter": group_values,
            "_needs_advanced": True,
        }

    def render_theme_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
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
        config = {}

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
        fig = go.Figure()

        x_col = config.get("x")
        group_col = config.get("group")
        y_cols = config.get("y_columns", [])

        if not x_col or not y_cols:
            fig.update_layout(title="Please select X axis and at least one Statistic")
            return fig

        # Prepare X axis with renames
        # Prepare X axis with renames (handled later to preserve order)
        # Ensure x_data is string for categorical plotting
        data = data.copy()
        data[x_col] = data[x_col].astype(str)

        # Apply X Filter
        if config.get("x_filter") is not None:
            data = data[data[x_col].isin(config["x_filter"])]

        # Calculate Total for each row (stacked bars)
        # Assuming one row per X/Group combination
        data["__total"] = data[y_cols].sum(axis=1)

        # Define hover template
        hover_template = (
            "<b>%{x}</b><br>"
            "Value: %{y:.4f}<br>"
            "<b>Total: %{customdata:.4f}</b>"
            "<extra></extra>"
        )

        if group_col:
            # Custom Layout for Grouped Stacked Bars to support Spacing

            # Ensure data is string for categorical plotting
            data[group_col] = data[group_col].astype(str)

            # Apply Group Filter
            if config.get("group_filter") is not None:
                data = data[data[group_col].isin(config["group_filter"])]

            # Get unique categories and groups (sorted)
            if config.get("xaxis_order"):
                # Convert order to strings to match data
                xaxis_order_str = [str(x) for x in config["xaxis_order"]]
                # Filter to present values
                ordered_cats = [c for c in xaxis_order_str if c in data[x_col].unique()]
                missing = [c for c in sorted(data[x_col].unique()) if c not in ordered_cats]
                ordered_cats.extend(missing)
            else:
                ordered_cats = sorted(data[x_col].unique())

            if config.get("group_order"):
                # Convert order to strings to match data
                group_order_str = [str(g) for g in config["group_order"]]
                ordered_groups = [g for g in group_order_str if g in data[group_col].unique()]
                missing = [g for g in sorted(data[group_col].unique()) if g not in ordered_groups]
                ordered_groups.extend(missing)
            else:
                ordered_groups = sorted(data[group_col].unique())

            # Apply Renames to Data
            x_renames = config.get("xaxis_labels", {})
            if x_renames:
                data[x_col] = data[x_col].replace(x_renames)

            # Apply Renames to Ordered Lists
            categories = []
            for cat in ordered_cats:
                new_name = x_renames.get(cat, cat)
                categories.append(new_name)

            groups = []
            # Check for explicit group renames (from specific UI)
            group_renames = config.get("group_renames", {})

            # Fix: Apply renames to data so lookups succeed
            if group_renames:
                data[group_col] = data[group_col].replace(group_renames)

            for grp in ordered_groups:
                new_name = group_renames.get(grp, grp)
                groups.append(new_name)

            # Calculate coordinates: Map (Category, Group) -> X Coordinate
            # Unit width per bar slot (including gap) is 1.0

            bargap = config.get("bargap", 0.2)
            bargroupgap = config.get("bargroupgap", 0.0)

            # Bar width
            bar_width = 1.0 - bargap

            # Coordinate mapping
            tick_vals = []
            tick_text = []

            # For annotations (Category labels)
            cat_centers = []

            current_x = 0.0

            # We need to map each row in data to an x_coord
            # Create a mapping dictionary
            coord_map = {}

            # For Shapes (Distinction)
            distinction_shapes = []
            show_separators = config.get("show_separators", False)
            sep_color = config.get("separator_color", "#E0E0E0")
            shade_alternate = config.get("shade_alternate", False)
            shade_color = config.get("shade_color", "#F5F5F5")

            # Isolation Config
            isolate_last = config.get("isolate_last_group", False)
            isolation_gap = config.get("isolation_gap", 0.5)

            # Track start of current category for shading

            for i, cat in enumerate(categories):
                start_x = current_x

                for grp in groups:
                    # Map based on current iteration values
                    coord_map[(cat, grp)] = current_x
                    tick_vals.append(current_x)
                    tick_text.append(grp)
                    current_x += 1.0  # Advance by 1 unit (bar + gap is handled by width)

                # Calculate center for this category
                # Bars occupy [start_x, current_x] roughly, but last bar ends at current_x - 1.0 + bar_width
                # We align label to the center of the group occupied duration.
                # Center = (start_x + (current_x - 1.0)) / 2.0
                center = (start_x + (current_x - 1.0)) / 2.0
                cat_centers.append((center, cat))

                # SHADING LOGIC
                if shade_alternate and (i % 2 == 1):
                    # Shade odd groups (e.g., 2nd, 4th...)
                    # Left edge: Start of group minus half gap (unless first group)
                    rect_x0 = start_x - 0.5 - (bargroupgap / 2.0)

                    # Right edge: End of group plus half gap
                    rect_x1 = current_x - 0.5 + (bargroupgap / 2.0)

                    distinction_shapes.append(
                        dict(
                            type="rect",
                            xref="x",
                            yref="paper",
                            x0=rect_x0,
                            x1=rect_x1,
                            y0=0,
                            y1=1,
                            fillcolor=shade_color,
                            opacity=0.5,
                            layer="below",
                            line_width=0,
                        )
                    )

                # SEPARATOR LOGIC
                # We want to draw separators between groups.
                # If 'isolate_last' is True, we handle the separation before the LAST group differently.

                # Check if the NEXT group is the last one (and we are isolating)
                next_is_last_isolated = isolate_last and (i == len(categories) - 2)

                if show_separators and i < len(categories) - 1:
                    # If next is isolated, we SKIP the standard dashed separator here.
                    # We will draw a special solid separator after adding the gap.
                    if not next_is_last_isolated:
                        # Standard Separator at midpoint of gap
                        sep_x = (current_x - 0.5) + (bargroupgap / 2.0)
                        distinction_shapes.append(
                            dict(
                                type="line",
                                xref="x",
                                yref="paper",
                                x0=sep_x,
                                x1=sep_x,
                                y0=0,
                                y1=1,
                                line=dict(color=sep_color, width=1, dash="dash"),
                                layer="below",
                            )
                        )

                # Standard Gap between groups
                current_x += bargroupgap

                # ISOLATION GAP & SEPARATOR
                # If we just finished the second-to-last group, and we are isolating the last one:
                if next_is_last_isolated:
                    # Add extra isolation gap
                    current_x += isolation_gap

                    # Draw Special Separator in the middle of this total gap
                    # Total gap = bargroupgap + isolation_gap
                    # The gap ends at the new 'current_x' (start of next bar slot - 0.5? No, see below)
                    # Visual Right Edge of Prev Group = (current_x - isolation_gap - bargroupgap) - 0.5
                    # Visual Left Edge of Next Group = current_x - 0.5

                    # Midpoint = current_x - 0.5 - (TotalGap / 2.0)
                    gap_total = bargroupgap + isolation_gap
                    sep_x = current_x - 0.5 - (gap_total / 2.0)

                    # Draw solid line
                    distinction_shapes.append(
                        dict(
                            type="line",
                            xref="x",
                            yref="paper",
                            x0=sep_x,
                            x1=sep_x,
                            y0=0,
                            y1=1,
                            line=dict(color="#333333", width=2, dash="solid"),  # Darker/Stronger
                            layer="below",
                        )
                    )

            # Map coordinates to data
            # We can't just use map on a tuple column easily, so we iterate or use apply
            # Faster: create a temporary column
            def get_coord(row: pd.Series) -> Any:
                return coord_map.get((row[x_col], row[group_col]), None)

            data["__x_coord"] = data.apply(get_coord, axis=1)

            # Add traces

            for y_col in y_cols:
                error_y = None
                if config.get("show_error_bars"):
                    sd_col = f"{y_col}.sd"
                    if sd_col in data.columns:
                        error_y = dict(type="data", array=data[sd_col], visible=True)

                # We use the original y_col as name. StyleManager will apply overrides.
                trace_name = y_col

                fig.add_trace(
                    go.Bar(
                        x=data["__x_coord"],
                        y=data[y_col],
                        name=trace_name,
                        error_y=error_y,
                        width=bar_width,
                        customdata=data["__total"].tolist(),
                        hovertemplate=hover_template,
                    )
                )

            # Update Layout
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
            # Make sure it's a list
            if not isinstance(existing_shapes, list):
                existing_shapes = []

            # Convert tuples likely coming from Streamlit shapes UI? No, usually list of dicts.
            # safe merge
            all_shapes = existing_shapes + distinction_shapes
            fig.update_layout(shapes=all_shapes)

            # Add Annotations for Categories
            # We place them below the X axis
            annotations = []

            font_size = config.get("major_label_size", 14)
            font_color = config.get("major_label_color", "#000000")
            font_offset = config.get("major_label_offset", -0.15)

            for center, label in cat_centers:
                annotations.append(
                    dict(
                        x=center,
                        y=font_offset,  # Position below axis. User might need to adjust bottom margin.
                        xref="x",
                        yref="paper",  # Relative to plot area
                        text=f"<b>{label}</b>",
                        showarrow=False,
                        font=dict(size=font_size, color=font_color),
                        yanchor="top",
                    )
                )

            fig.update_layout(annotations=annotations)

            # Adjust bottom margin automatically if not set high enough?
            # The user has a control for margin_b, so we respect that.

        else:
            # Standard Stacked Bar (No Sub-groups)
            x_values = data[x_col]

            for y_col in y_cols:
                error_y = None
                if config.get("show_error_bars"):
                    sd_col = f"{y_col}.sd"
                    if sd_col in data.columns:
                        error_y = dict(type="data", array=data[sd_col], visible=True)

                # We use the original y_col as name. StyleManager will apply overrides.
                trace_name = y_col

                fig.add_trace(
                    go.Bar(
                        x=x_values,
                        y=data[y_col],
                        name=trace_name,
                        error_y=error_y,
                        customdata=data["__total"].tolist(),
                        hovertemplate=hover_template,
                    )
                )

            fig.update_layout(barmode="stack")

        fig.update_layout(
            title=config.get("title", ""),
            xaxis_title=(
                config.get("xlabel", x_col) if not group_col else None
            ),  # Hide default title if grouped? No, keep it.
            yaxis_title=config.get("ylabel", "Value"),
            legend_title=config.get("legend_title", "Statistics"),
        )

        return fig

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
