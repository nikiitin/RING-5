"""Stacked bar plot implementation."""

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.plotting.base_plot import BasePlot
from src.web.ui.components.plot_config_components import PlotConfigComponents


class StackedBarPlot(BasePlot):
    """Stacked bar plot with support for multiple stacked statistics."""

    def __init__(self, plot_id: int, name: str):
        """Initialize stacked bar plot."""
        super().__init__(plot_id, name, "stacked_bar")

    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for stacked bar plot."""
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        all_cols = data.columns.tolist()

        x_col = st.selectbox(
            "X-Axis (Categories)",
            options=all_cols,
            index=all_cols.index(saved_config["x"]) if saved_config.get("x") in all_cols else 0,
            key=f"stacked_x_{self.plot_id}",
        )

        # Use reusable statistics multiselect component
        y_cols = PlotConfigComponents.render_statistics_multiselect(
            numeric_cols=numeric_cols,
            saved_config=saved_config,
            plot_id=self.plot_id,
        )

        # Filter Options
        x_values, _ = PlotConfigComponents.render_filter_multiselects(
            data=data,
            x_col=x_col,
            group_col=None,
            saved_config=saved_config,
            plot_id=self.plot_id,
        )

        # Title & Labels
        default_title = saved_config.get("title", f"Stacked Statistics by {x_col}")
        default_xlabel = saved_config.get("xlabel", x_col)
        default_ylabel = saved_config.get("ylabel", "Value")

        label_config = PlotConfigComponents.render_title_labels_section(
            saved_config=saved_config,
            plot_id=self.plot_id,
            default_title=default_title,
            default_xlabel=default_xlabel,
            default_ylabel=default_ylabel,
            include_legend_title=True,
            default_legend_title=saved_config.get("legend_title", "Statistics"),
        )

        return {
            "x": x_col,
            "y_columns": y_cols,
            "x_filter": x_values,
            **label_config,
        }

    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create stacked bar plot figure."""
        fig = go.Figure()

        x_col = config.get("x")
        y_cols = config.get("y_columns", [])

        if not x_col or not y_cols:
            fig.update_layout(title="Please select X axis and at least one Statistic")
            return fig

        # Prepare data
        data = self._prepare_data(data, x_col, y_cols, config)

        # Define hover template
        hover_template = self._get_hover_template()

        # Create simple stacked bar figure
        fig = self._create_stacked_figure(fig, data, x_col, y_cols, config, hover_template)

        fig.update_layout(
            title=config.get("title", ""),
            xaxis_title=config.get("xlabel", x_col),
            yaxis_title=config.get("ylabel", "Value"),
            legend_title=config.get("legend_title", "Statistics"),
        )

        return fig

    def _prepare_data(
        self, data: pd.DataFrame, x_col: str, y_cols: List[str], config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Prepare data: apply filters, calculate totals, convert types."""
        data = data.copy()
        data[x_col] = data[x_col].astype(str)

        # Apply X Filter
        if config.get("x_filter") is not None:
            data = data[data[x_col].isin(config["x_filter"])]

        # Calculate Total for each row
        data["__total"] = data[y_cols].sum(axis=1)

        return data

    def _get_hover_template(self) -> str:
        """Get standard hover template."""
        return (
            "<b>%{x}</b><br>"
            "Value: %{y:.4f}<br>"
            "<b>Total: %{customdata:.4f}</b>"
            "<extra></extra>"
        )

    def _create_stacked_figure(
        self,
        fig: go.Figure,
        data: pd.DataFrame,
        x_col: str,
        y_cols: List[str],
        config: Dict[str, Any],
        hover_template: str,
    ) -> go.Figure:
        """Create figure for stacked bars."""
        for y_col in y_cols:
            fig = self._add_bar_trace(fig, data, y_col, x_col, None, hover_template, config)

        if config.get("show_totals"):
            annotations = self._build_totals_annotations(data, x_col, config)
            fig.update_layout(annotations=annotations)

        fig.update_layout(barmode="stack")

        return fig

    def _add_bar_trace(
        self,
        fig: go.Figure,
        data: pd.DataFrame,
        y_col: str,
        x_col: str,
        bar_width: Optional[float],
        hover_template: str,
        config: Dict[str, Any],
    ) -> go.Figure:
        """Add a single bar trace to the figure."""
        error_y = None
        if config.get("show_error_bars"):
            sd_col = f"{y_col}.sd"
            if sd_col in data.columns:
                error_y = dict(type="data", array=data[sd_col], visible=True)

        trace_kwargs = dict(
            x=data[x_col],
            y=data[y_col],
            name=y_col,
            error_y=error_y,
            customdata=data["__total"].tolist(),
            hovertemplate=hover_template,
        )

        if bar_width is not None:
            trace_kwargs["width"] = bar_width

        fig.add_trace(go.Bar(**trace_kwargs))
        return fig

    def _build_totals_annotations(
        self, data: pd.DataFrame, x_col: str, config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build annotations for stack totals."""
        total_fmt = config.get("net_total_format", ".2f")
        font_size = config.get("total_font_size", 12)
        font_color = config.get("total_font_color", "#000000")
        position_option = config.get("total_position", "Outside")
        anchor_option = config.get("total_anchor", "End")
        offset = config.get("total_offset", 0)
        rotation = config.get("total_rotation", 0)
        threshold = config.get("total_threshold", 0.0)

        def fmt_val(val: float) -> str:
            try:
                return f"{val:{total_fmt}}"
            except ValueError:
                return str(val)

        annotations = []
        for _, row in data.iterrows():
            val = row["__total"]

            if val <= threshold:
                continue

            x_pos = row[x_col]
            y_pos, yanchor = self._get_total_position(val, position_option, anchor_option)

            annotations.append(
                dict(
                    x=x_pos,
                    y=y_pos,
                    xref="x",
                    yref="y",
                    text=fmt_val(val),
                    showarrow=False,
                    font=dict(size=font_size, color=font_color),
                    yanchor=yanchor,
                    yshift=offset,
                    textangle=rotation,
                )
            )

        return annotations

    def _get_total_position(
        self, val: float, position_option: str, anchor_option: str
    ) -> tuple[float, str]:
        """Calculate Y position and anchor for total annotation."""
        if position_option == "Outside":
            return val, "bottom"
        elif position_option == "Inside":
            if anchor_option == "End":
                return val, "top"
            elif anchor_option == "Middle":
                return val / 2, "middle"
            elif anchor_option == "Start":
                return 0, "bottom"
        return val, "bottom"

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for stacked bar plot."""
        return None
