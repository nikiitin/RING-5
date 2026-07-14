"""Reusable UI components for plot configuration."""

import pandas as pd
import streamlit as st

from src.web.components.common.bounded_options import bounded_unique_strings
from src.web.models.plot_models import PlotConfig


class PlotConfigComponents:
    """Reusable UI components for plot configuration."""

    @staticmethod
    def render_filter_multiselects(
        data: pd.DataFrame,
        x_col: str | None,
        group_col: str | None,
        saved_config: PlotConfig,
        plot_id: int,
        x_label: str = "Filter X values",
        group_label: str = "Filter Groups",
    ) -> tuple[list[str], list[str]]:
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

        x_values: list[str] = []
        group_values: list[str] = []

        # Filter X values
        if x_col and x_col in data.columns:
            unique_x, x_truncated = bounded_unique_strings(data[x_col])
            if x_truncated:
                st.warning(
                    "X-axis filter options were capped for safety; refine the dataset first."
                )
            raw_default_x = saved_config.get("x_filter", unique_x)
            default_x, _ = bounded_unique_strings(
                raw_default_x if isinstance(raw_default_x, list) else unique_x
            )
            # Ensure defaults are valid
            default_x = [x for x in default_x if x in unique_x]

            # Sanitize session state — Streamlit >= 1.53 raises when keys hold
            # values that are no longer valid options (e.g. after a data update).
            _xf_key = f"x_filter_{plot_id}"
            if _xf_key in st.session_state:
                _xf_state = st.session_state[_xf_key]
                if isinstance(_xf_state, list):
                    _xf_valid = [v for v in _xf_state[: len(unique_x)] if v in unique_x]
                    if len(_xf_valid) != len(_xf_state):
                        st.session_state[_xf_key] = _xf_valid

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
            unique_g, group_truncated = bounded_unique_strings(data[group_col])
            if group_truncated:
                st.warning("Group filter options were capped for safety; refine the dataset first.")
            raw_default_g = saved_config.get("group_filter", unique_g)
            default_g, _ = bounded_unique_strings(
                raw_default_g if isinstance(raw_default_g, list) else unique_g
            )
            # Ensure defaults are valid
            default_g = [g for g in default_g if g in unique_g]

            # Sanitize session state for group filter (same reason as above).
            _gf_key = f"group_filter_{plot_id}"
            if _gf_key in st.session_state:
                _gf_state = st.session_state[_gf_key]
                if isinstance(_gf_state, list):
                    _gf_valid = [v for v in _gf_state[: len(unique_g)] if v in unique_g]
                    if len(_gf_valid) != len(_gf_state):
                        st.session_state[_gf_key] = _gf_valid

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
        numeric_cols: list[str],
        saved_config: PlotConfig,
        plot_id: int,
        label: str = "Statistics to Stack",
        help_text: str = "Select multiple statistics to stack on top of each other",
    ) -> list[str]:
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

        # Sanitize session state to prevent StreamlitInvalidOptionError when
        # previously selected columns are no longer available after a data change.
        _ys_key = f"y_multiselect_{plot_id}"
        if _ys_key in st.session_state:
            _ys_state = st.session_state[_ys_key]
            if isinstance(_ys_state, list):
                _ys_valid = [v for v in _ys_state if v in numeric_cols]
                if len(_ys_valid) != len(_ys_state):
                    st.session_state[_ys_key] = _ys_valid

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
        saved_config: PlotConfig,
        plot_id: int,
        default_title: str = "",
        default_xlabel: str = "",
        default_ylabel: str = "Value",
        include_legend_title: bool = False,
        default_legend_title: str = "",
    ) -> dict[str, str]:
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
        title = (
            st.text_input(
                "Title",
                value=saved_config.get("title", default_title),
                key=f"title_{plot_id}",
            )
            or ""
        )

        xlabel = (
            st.text_input(
                "X-label",
                value=saved_config.get("xlabel", default_xlabel),
                key=f"xlabel_{plot_id}",
            )
            or ""
        )

        ylabel = (
            st.text_input(
                "Y-label",
                value=saved_config.get("ylabel", default_ylabel),
                key=f"ylabel_{plot_id}",
            )
            or ""
        )

        result = {
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
        }

        if include_legend_title:
            legend_title = (
                st.text_input(
                    "Legend Title",
                    value=saved_config.get("legend_title", default_legend_title),
                    key=f"legend_title_{plot_id}",
                    help="Custom title for the legend.",
                )
                or ""
            )
            result["legend_title"] = legend_title

        return result
