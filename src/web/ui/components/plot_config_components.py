"""Reusable UI components for plot configuration."""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


class PlotConfigComponents:
    """Reusable UI components for plot configuration."""

    @staticmethod
    def render_filter_multiselects(
        data: pd.DataFrame,
        x_col: Optional[str],
        group_col: Optional[str],
        saved_config: Dict[str, Any],
        plot_id: int,
        x_label: str = "Filter X values",
        group_label: str = "Filter Groups",
    ) -> Tuple[List[str], List[str]]:
        """
        Render X and Group filter multiselects in a two-column layout.

        Args:
            data: The DataFrame to filter
            x_col: X-axis column name
            group_col: Group column name (optional)
            saved_config: Previously saved configuration
            plot_id: Plot ID for unique widget keys
            x_label: Label for X filter (default: "Filter X values")
            group_label: Label for group filter (default: "Filter Groups")

        Returns:
            Tuple of (x_filter_values, group_filter_values)
        """
        col_filter1, col_filter2 = st.columns(2)

        x_values: List[str] = []
        group_values: List[str] = []

        # Filter X values
        if x_col and x_col in data.columns:
            unique_x = sorted(data[x_col].astype(str).unique())
            default_x = saved_config.get("x_filter", unique_x)
            # Ensure defaults are valid
            default_x = [x for x in default_x if x in unique_x]

            with col_filter1:
                x_values = st.multiselect(
                    x_label,
                    options=unique_x,
                    default=default_x,
                    key=f"x_filter_{plot_id}",
                    help="Select specific values to display on the X-axis.",
                )

        # Filter Group values
        if group_col and group_col in data.columns:
            unique_g = sorted(data[group_col].astype(str).unique())
            default_g = saved_config.get("group_filter", unique_g)
            # Ensure defaults are valid
            default_g = [g for g in default_g if g in unique_g]

            with col_filter2:
                group_values = st.multiselect(
                    group_label,
                    options=unique_g,
                    default=default_g,
                    key=f"group_filter_{plot_id}",
                    help="Select specific groups to display.",
                )

        return x_values, group_values

    @staticmethod
    def render_statistics_multiselect(
        numeric_cols: List[str],
        saved_config: Dict[str, Any],
        plot_id: int,
        label: str = "Statistics to Stack",
        help_text: str = "Select multiple statistics to stack on top of each other",
    ) -> List[str]:
        """
        Render a multiselect for choosing statistics to stack.

        Args:
            numeric_cols: List of numeric column names
            saved_config: Previously saved configuration
            plot_id: Plot ID for unique widget keys
            label: Label for the multiselect
            help_text: Help text for the multiselect

        Returns:
            List of selected column names
        """
        default_ys = saved_config.get("y_columns", [])
        # Filter to ensure they exist
        valid_ys = [y for y in default_ys if y in numeric_cols]

        # Default to first two numeric columns if none selected
        if not valid_ys and len(numeric_cols) >= 2:
            valid_ys = numeric_cols[:2]
        elif not valid_ys and numeric_cols:
            valid_ys = numeric_cols[:1]

        result = st.multiselect(
            label,
            options=numeric_cols,
            default=valid_ys,
            key=f"y_multiselect_{plot_id}",
            help=help_text,
        )
        return list(result) if isinstance(result, list) else []

    @staticmethod
    def render_title_labels_section(
        saved_config: Dict[str, Any],
        plot_id: int,
        default_title: str = "",
        default_xlabel: str = "",
        default_ylabel: str = "Value",
        include_legend_title: bool = False,
        default_legend_title: str = "",
    ) -> Dict[str, str]:
        """
        Render title and label inputs.

        Args:
            saved_config: Previously saved configuration
            plot_id: Plot ID for unique widget keys
            default_title: Default title value
            default_xlabel: Default x-label value
            default_ylabel: Default y-label value
            include_legend_title: Whether to show legend title input
            default_legend_title: Default legend title value

        Returns:
            Dictionary with title, xlabel, ylabel, (and legend_title if requested)
        """
        title = st.text_input(
            "Title",
            value=saved_config.get("title", default_title),
            key=f"title_{plot_id}",
        )

        xlabel = st.text_input(
            "X-label",
            value=saved_config.get("xlabel", default_xlabel),
            key=f"xlabel_{plot_id}",
        )

        ylabel = st.text_input(
            "Y-label",
            value=saved_config.get("ylabel", default_ylabel),
            key=f"ylabel_{plot_id}",
        )

        result = {
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
        }

        if include_legend_title:
            legend_title = st.text_input(
                "Legend Title",
                value=saved_config.get("legend_title", default_legend_title),
                key=f"legend_title_{plot_id}",
                help="Custom title for the legend.",
            )
            result["legend_title"] = legend_title

        return result
