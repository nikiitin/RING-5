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
                "X-axis (Major Group)",
                options=categorical_cols + numeric_cols,
                index=x_default_idx,
                key=f"x_{self.plot_id}",
                help="The main category for the X-axis (e.g., Benchmark)",
            )

            # Sub-group (Minor Group)
            group_default_idx = 0
            if saved_config.get("group") and saved_config["group"] in categorical_cols:
                group_default_idx = categorical_cols.index(saved_config["group"])

            group_column = st.selectbox(
                "Sub-group (Optional)",
                options=[None] + categorical_cols,
                index=group_default_idx + 1 if saved_config.get("group") else 0,
                key=f"group_{self.plot_id}",
                help="Secondary category to group by (e.g., Configuration)",
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

        # Renaming Options
        legend_renames = {}
        x_renames = {}
        group_renames = {}

        with st.expander("Label Renaming"):
            # Legend Labels
            st.markdown("#### Legend Labels")
            for y_col in y_columns:
                default_label = saved_config.get("legend_renames", {}).get(y_col, y_col)
                new_label = st.text_input(
                    f"Rename '{y_col}'",
                    value=default_label,
                    key=f"legend_rename_{self.plot_id}_{y_col}",
                )
                if new_label != y_col:
                    legend_renames[y_col] = new_label

            # X-axis Labels
            if x_column:
                st.markdown("#### X-axis Labels")
                unique_x = sorted(data[x_column].astype(str).unique())
                if len(unique_x) > 50:
                    st.warning(f"Too many X values ({len(unique_x)}). Renaming disabled.")
                else:
                    cols = st.columns(2)
                    for i, val in enumerate(unique_x):
                        with cols[i % 2]:
                            default_val = saved_config.get("x_renames", {}).get(val, val)
                            new_val = st.text_input(
                                f"'{val}' →",
                                value=default_val,
                                key=f"x_rename_{self.plot_id}_{val}",
                            )
                            if new_val != val:
                                x_renames[val] = new_val

            # Group Labels
            if group_column:
                st.markdown("#### Sub-group Labels")
                unique_g = sorted(data[group_column].astype(str).unique())
                if len(unique_g) > 50:
                    st.warning(f"Too many Group values ({len(unique_g)}). Renaming disabled.")
                else:
                    cols = st.columns(2)
                    for i, val in enumerate(unique_g):
                        with cols[i % 2]:
                            default_val = saved_config.get("group_renames", {}).get(val, val)
                            new_val = st.text_input(
                                f"'{val}' →",
                                value=default_val,
                                key=f"group_rename_{self.plot_id}_{val}",
                            )
                            if new_val != val:
                                group_renames[val] = new_val

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

        # Display options
        display_config = self.render_display_options(saved_config)

        return {
            "x": x_column,
            "group": group_column,
            "y_columns": y_columns,
            "y": y_columns[0] if y_columns else None,  # For compatibility
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "legend_renames": legend_renames,
            "x_renames": x_renames,
            "group_renames": group_renames,
            "x_filter": x_values,
            "group_filter": group_values,
            **display_config,
            "_needs_advanced": True,
        }

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
        # Note: We handle renames later to ensure ordering works on original values
        # Ensure x_data is string for categorical plotting
        data = data.copy()
        data[x_col] = data[x_col].astype(str)

        # Apply X Filter
        if config.get("x_filter") is not None:
            data = data[data[x_col].isin(config["x_filter"])]

        # Calculate Total for each row (stacked bars)
        # Assuming one row per X/Group combination
        data["__total"] = data[y_cols].sum(axis=1)
        
        # Debug: Print first few totals
        print(f"DEBUG: Calculated totals (first 5): {data['__total'].head().tolist()}")

        # Define hover template
        hover_template = (
            "<b>%{x}</b><br>"
            "Value: %{y:.4f}<br>"
            "<b>Total: %{customdata:.4f}</b>"
            "<extra></extra>"
        )

        if group_col:
            # Custom Layout for Grouped Stacked Bars to support Spacing
            # Note: We handle renames later to ensure ordering works on original values

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
            x_renames = config.get("x_renames", {})
            if x_renames:
                data[x_col] = data[x_col].replace(x_renames)

            group_renames = config.get("group_renames", {})
            if group_renames:
                data[group_col] = data[group_col].replace(group_renames)

            # Apply Renames to Ordered Lists
            categories = []
            for cat in ordered_cats:
                # x_renames keys might be strings or original types.
                # Since we converted data to string, we should check string keys.
                # But config['x_renames'] keys come from UI which uses strings.
                new_name = x_renames.get(cat, cat)
                categories.append(new_name)

            groups = []
            for grp in ordered_groups:
                new_name = group_renames.get(grp, grp)
                groups.append(new_name)

            # Calculate coordinates
            # We map (Category, Group) -> X Coordinate
            # Gap between bars (within group) is controlled by width (1 - bargap)
            # Gap between groups (Categories) is controlled by adding extra space

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

            for cat in categories:
                start_x = current_x
                for grp in groups:
                    coord_map[(cat, grp)] = current_x
                    tick_vals.append(current_x)
                    tick_text.append(grp)
                    current_x += 1.0  # Advance by 1 unit (bar + gap is handled by width)

                # Calculate center for this category
                end_x = current_x - 1.0
                center = (start_x + end_x) / 2.0
                cat_centers.append((center, cat))

                # Add group gap
                # bargroupgap is a fraction of the group width? Or just units?
                # Let's treat it as units. 1 unit = 1 bar slot.
                # Default gap is 0. We add extra.
                current_x += bargroupgap

            # Map coordinates to data
            # We can't just use map on a tuple column easily, so we iterate or use apply
            # Faster: create a temporary column
            def get_coord(row: pd.Series) -> Any:
                return coord_map.get((row[x_col], row[group_col]), None)

            data["__x_coord"] = data.apply(get_coord, axis=1)

            # Add traces
            legend_renames = config.get("legend_renames", {})

            for y_col in y_cols:
                error_y = None
                if config.get("show_error_bars"):
                    sd_col = f"{y_col}.sd"
                    if sd_col in data.columns:
                        error_y = dict(type="data", array=data[sd_col], visible=True)

                trace_name = legend_renames.get(y_col, y_col)

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

            # Add Annotations for Categories
            # We place them below the X axis
            annotations = []
            for center, label in cat_centers:
                annotations.append(
                    dict(
                        x=center,
                        y=-0.15,  # Position below axis. User might need to adjust bottom margin.
                        xref="x",
                        yref="paper",  # Relative to plot area
                        text=f"<b>{label}</b>",
                        showarrow=False,
                        font=dict(size=14),
                        yanchor="top",
                    )
                )

            fig.update_layout(annotations=annotations)

            # Adjust bottom margin automatically if not set high enough?
            # The user has a control for margin_b, so we respect that.

        else:
            # Standard Stacked Bar (No Sub-groups)
            x_values = data[x_col]

            legend_renames = config.get("legend_renames", {})

            for y_col in y_cols:
                error_y = None
                if config.get("show_error_bars"):
                    sd_col = f"{y_col}.sd"
                    if sd_col in data.columns:
                        error_y = dict(type="data", array=data[sd_col], visible=True)

                trace_name = legend_renames.get(y_col, y_col)

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
