"""
Plotly connector — translate resolved FigureSpec into go.Figure updates.

This replaces ``StyleApplicator.apply_styles()`` internals.  The applicator
becomes a thin wrapper that builds a FigureSpec and calls this connector.

Usage:
    from src.core.visualization.connectors import FigureSpecToPlotly

    resolved = resolve_spec(spec)
    fig = FigureSpecToPlotly.apply(resolved, fig)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import plotly.graph_objects as go

from src.core.visualization.figure_spec import FigureSpec
from src.core.visualization.legend_spec import LegendSpec
from src.core.visualization.annotation_spec import AnnotationSpec, ReferenceLineSpec


class FigureSpecToPlotly:
    """Stateless translator: FigureSpec → Plotly figure updates.

    All methods are static / class-level — no instance state needed.
    The FigureSpec must be **resolved** (no -1 sentinels) before calling.
    """

    @staticmethod
    def apply(spec: FigureSpec, fig: go.Figure) -> go.Figure:
        """Apply the full FigureSpec to a Plotly figure.

        Args:
            spec: A resolved FigureSpec (no sentinel values).
            fig: The Plotly figure to update in place.

        Returns:
            The same figure, updated.
        """
        FigureSpecToPlotly._apply_dimensions(spec, fig)
        FigureSpecToPlotly._apply_backgrounds(spec, fig)
        FigureSpecToPlotly._apply_title(spec, fig)
        FigureSpecToPlotly._apply_xaxis(spec, fig)
        FigureSpecToPlotly._apply_yaxis(spec, fig)
        FigureSpecToPlotly._apply_y2axis(spec, fig)
        FigureSpecToPlotly._apply_legends(spec, fig)
        return fig

    @staticmethod
    def _apply_dimensions(spec: FigureSpec, fig: go.Figure) -> None:
        """Set figure width, height, margins, and bar gaps."""
        dims = spec.dimensions
        # Plotly uses pixels; convert inches → px
        dpi = dims.dpi if dims.dpi > 0 else 96
        width_px = int(dims.width * dpi)
        height_px = int(dims.height * dpi)

        margins = dims.margins
        fig.update_layout(
            width=width_px,
            height=height_px,
            margin=dict(
                t=int(margins.top),
                b=int(margins.bottom),
                l=int(margins.left),
                r=int(margins.right),
                pad=int(margins.pad),
            ),
            bargap=dims.bargap,
            bargroupgap=dims.bargroupgap,
        )

    @staticmethod
    def _apply_backgrounds(spec: FigureSpec, fig: go.Figure) -> None:
        """Set paper and plot background colors."""
        fig.update_layout(
            paper_bgcolor=spec.paper_bgcolor,
            plot_bgcolor=spec.plot_bgcolor,
        )

    @staticmethod
    def _apply_title(spec: FigureSpec, fig: go.Figure) -> None:
        """Set figure title with typography from spec."""
        if spec.title:
            typo = spec.typography
            fig.update_layout(
                title=dict(
                    text=spec.title,
                    font=dict(
                        size=typo.font_size_title,
                    ),
                ),
            )

    @staticmethod
    def _apply_xaxis(spec: FigureSpec, fig: go.Figure) -> None:
        """Configure the primary X-axis."""
        x_axis = spec.axes.x
        typo = spec.typography

        update: Dict[str, Any] = {}

        if x_axis.label:
            update["title"] = dict(
                text=x_axis.label,
                font=dict(size=typo.font_size_xlabel),
            )

        update["tickfont"] = dict(size=typo.font_size_ticks)
        update["tickangle"] = x_axis.tick_angle

        if x_axis.range is not None:
            update["range"] = x_axis.range
        if x_axis.scale != "linear":
            update["type"] = x_axis.scale
        if x_axis.dtick is not None:
            update["dtick"] = x_axis.dtick

        update["showgrid"] = x_axis.show_grid
        if x_axis.show_grid:
            update["gridcolor"] = x_axis.grid_color
            update["gridwidth"] = x_axis.grid_width

        update["showticklabels"] = x_axis.show_tick_labels
        update["automargin"] = x_axis.automargin

        if x_axis.category_order is not None:
            update["categoryorder"] = "array"
            update["categoryarray"] = x_axis.category_order

        fig.update_xaxes(**update)

    @staticmethod
    def _apply_yaxis(spec: FigureSpec, fig: go.Figure) -> None:
        """Configure the primary Y-axis."""
        y_axis = spec.axes.y
        typo = spec.typography

        update: Dict[str, Any] = {}

        if y_axis.label:
            update["title"] = dict(
                text=y_axis.label,
                font=dict(size=typo.font_size_ylabel),
            )

        update["tickfont"] = dict(size=typo.font_size_yticks)

        if y_axis.range is not None:
            update["range"] = y_axis.range
        if y_axis.scale != "linear":
            update["type"] = y_axis.scale
        if y_axis.dtick is not None:
            update["dtick"] = y_axis.dtick

        update["showgrid"] = y_axis.show_grid
        if y_axis.show_grid:
            update["gridcolor"] = y_axis.grid_color
            update["gridwidth"] = y_axis.grid_width

        update["automargin"] = y_axis.automargin

        fig.update_yaxes(**update, selector=dict(overlaying=None))

    @staticmethod
    def _apply_y2axis(spec: FigureSpec, fig: go.Figure) -> None:
        """Configure the secondary Y-axis (if present)."""
        if spec.axes.y2 is None:
            return

        y2 = spec.axes.y2
        typo = spec.typography

        update: Dict[str, Any] = {
            "overlaying": "y",
            "side": "right",
        }

        if y2.label:
            update["title"] = dict(
                text=y2.label,
                font=dict(size=typo.font_size_y2label),
            )

        update["tickfont"] = dict(size=typo.font_size_y2ticks)

        if y2.range is not None:
            update["range"] = y2.range
        if y2.dtick is not None:
            update["dtick"] = y2.dtick

        update["showgrid"] = y2.show_grid

        fig.update_layout(yaxis2=update)

    @staticmethod
    def _apply_legends(spec: FigureSpec, fig: go.Figure) -> None:
        """Apply legend configuration for all legends."""
        if not spec.legends:
            return

        # Primary legend (legend1)
        primary = spec.legends[0]
        legend_update = FigureSpecToPlotly._build_legend_dict(primary)
        fig.update_layout(legend=legend_update)

        # Secondary legends (legend2, legend3) if multi-legend layout
        for i, legend in enumerate(spec.legends[1:], start=2):
            if not legend.visible:
                continue
            legend_key = f"legend{i}"
            legend_dict = FigureSpecToPlotly._build_legend_dict(legend)
            fig.update_layout(**{legend_key: legend_dict})

    @staticmethod
    def _build_legend_dict(legend: LegendSpec) -> Dict[str, Any]:
        """Build a Plotly legend configuration dictionary."""
        result: Dict[str, Any] = {
            "font": dict(
                size=legend.font_size,
                color=legend.font_color,
            ),
            "orientation": "h" if legend.orientation == "horizontal" else "v",
            "itemsizing": legend.itemsizing,
        }

        if legend.title:
            result["title"] = dict(
                text=legend.title,
                font=dict(
                    size=legend.title_font_size,
                    color=legend.title_font_color,
                ),
            )

        if legend.custom_position and legend.position_x >= 0:
            result["x"] = legend.position_x
        if legend.custom_position and legend.position_y >= 0:
            result["y"] = legend.position_y

        if legend.anchor_x != "auto":
            result["xanchor"] = legend.anchor_x
        if legend.anchor_y != "auto":
            result["yanchor"] = legend.anchor_y

        if legend.bgcolor:
            result["bgcolor"] = legend.bgcolor
        if legend.border_width > 0:
            result["borderwidth"] = legend.border_width
            result["bordercolor"] = legend.border_color

        return result
