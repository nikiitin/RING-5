"""
Layout mapper for preserving Plotly layout in Matplotlib exports.

Extracts layout properties (axis limits, legend position, titles, etc.)
from Plotly figures and applies them to Matplotlib axes.
"""

from typing import Any, Dict, List

import plotly.graph_objects as go
from matplotlib.axes import Axes


class LayoutMapper:
    """
    Maps layout properties between Plotly and Matplotlib.

    Preserves user's interactive layout decisions when exporting to static formats.
    This ensures the exported figure matches what the user sees in the UI.

    Example:
        >>> layout = LayoutMapper.extract_layout(plotly_fig)
        >>> LayoutMapper.apply_to_matplotlib(mpl_ax, layout)
    """

    @staticmethod
    def extract_layout(figure: go.Figure) -> Dict[str, Any]:
        """
        Extract layout properties from Plotly figure.

        Args:
            figure: Plotly figure to extract from

        Returns:
            Dictionary with layout properties:
            - x_range, y_range: Axis limits
            - x_label, y_label: Axis labels
            - title: Figure title
            - legend: Legend position and anchor
            - x_grid, y_grid: Grid visibility
            - x_type, y_type: Axis type (linear, log)
            - annotations: List of annotations
        """
        layout = figure.layout
        layout_dict: Dict[str, Any] = {}

        # Extract axis ranges
        if layout.xaxis.range is not None:
            layout_dict["x_range"] = list(layout.xaxis.range)

        if layout.yaxis.range is not None:
            layout_dict["y_range"] = list(layout.yaxis.range)

        # Extract axis labels
        if layout.xaxis.title is not None:
            layout_dict["x_label"] = layout.xaxis.title.text

        if layout.yaxis.title is not None:
            layout_dict["y_label"] = layout.yaxis.title.text

        # Extract title
        if layout.title is not None and layout.title.text:
            layout_dict["title"] = layout.title.text

        # Extract legend settings
        if layout.legend is not None:
            legend_dict: Dict[str, Any] = {}
            if layout.legend.x is not None:
                legend_dict["x"] = layout.legend.x
            if layout.legend.y is not None:
                legend_dict["y"] = layout.legend.y
            if layout.legend.xanchor is not None:
                legend_dict["xanchor"] = layout.legend.xanchor
            if layout.legend.yanchor is not None:
                legend_dict["yanchor"] = layout.legend.yanchor
            if legend_dict:
                layout_dict["legend"] = legend_dict

        # Extract grid settings
        if layout.xaxis.showgrid is not None:
            layout_dict["x_grid"] = layout.xaxis.showgrid

        if layout.yaxis.showgrid is not None:
            layout_dict["y_grid"] = layout.yaxis.showgrid

        # Extract axis types (linear, log, etc.)
        if layout.xaxis.type is not None:
            layout_dict["x_type"] = layout.xaxis.type

        if layout.yaxis.type is not None:
            layout_dict["y_type"] = layout.yaxis.type

        # Extract annotations
        if layout.annotations:
            annotations: List[Dict[str, Any]] = []
            for ann in layout.annotations:
                ann_dict = {
                    "x": ann.x,
                    "y": ann.y,
                    "text": ann.text,
                    "showarrow": ann.showarrow,
                }
                annotations.append(ann_dict)
            layout_dict["annotations"] = annotations

        return layout_dict

    @staticmethod
    def apply_to_matplotlib(ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply extracted layout to Matplotlib axes.

        Args:
            ax: Matplotlib axes to modify
            layout: Layout dictionary from extract_layout()
        """
        # Apply axis ranges
        if "x_range" in layout:
            ax.set_xlim(layout["x_range"])

        if "y_range" in layout:
            ax.set_ylim(layout["y_range"])

        # Apply axis labels
        if "x_label" in layout:
            ax.set_xlabel(layout["x_label"])

        if "y_label" in layout:
            ax.set_ylabel(layout["y_label"])

        # Apply title
        if "title" in layout:
            ax.set_title(layout["title"])

        # Apply axis scales
        if "x_type" in layout and layout["x_type"] == "log":
            ax.set_xscale("log")

        if "y_type" in layout and layout["y_type"] == "log":
            ax.set_yscale("log")

        # Apply grid settings
        if "x_grid" in layout:
            ax.xaxis.grid(layout["x_grid"])

        if "y_grid" in layout:
            ax.yaxis.grid(layout["y_grid"])

        # Apply legend position if present
        if "legend" in layout:
            legend_config = layout["legend"]
            if "x" in legend_config and "y" in legend_config:
                # Matplotlib uses bbox_to_anchor for legend positioning
                ax.legend(
                    bbox_to_anchor=(legend_config["x"], legend_config["y"]),
                    loc="upper left",  # Use xanchor/yanchor to determine this
                )

        # Apply annotations
        if "annotations" in layout:
            for ann in layout["annotations"]:
                ax.annotate(
                    ann["text"],
                    xy=(ann["x"], ann["y"]),
                    xytext=(ann["x"], ann["y"]),
                    arrowprops=dict(arrowstyle="->") if ann.get("showarrow") else None,
                )
