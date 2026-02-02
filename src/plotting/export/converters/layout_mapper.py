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

        # Extract custom tick positions and labels (for grouped-stacked bars)
        if layout.xaxis.tickmode == "array":
            if layout.xaxis.tickvals is not None:
                layout_dict["x_tickvals"] = list(layout.xaxis.tickvals)
            if layout.xaxis.ticktext is not None:
                layout_dict["x_ticktext"] = [str(t) for t in layout.xaxis.ticktext]

        if layout.yaxis.tickmode == "array":
            if layout.yaxis.tickvals is not None:
                layout_dict["y_tickvals"] = list(layout.yaxis.tickvals)
            if layout.yaxis.ticktext is not None:
                layout_dict["y_ticktext"] = [str(t) for t in layout.yaxis.ticktext]

        # Extract annotations
        if layout.annotations:
            annotations: List[Dict[str, Any]] = []
            for ann in layout.annotations:
                ann_dict: Dict[str, Any] = {
                    "x": ann.x,
                    "y": ann.y,
                    "text": ann.text,
                    "showarrow": ann.showarrow,
                }

                # Extract text angle (rotation)
                if hasattr(ann, "textangle") and ann.textangle is not None:
                    ann_dict["textangle"] = ann.textangle

                # Extract font properties
                if hasattr(ann, "font") and ann.font is not None:
                    font_dict: Dict[str, Any] = {}
                    if hasattr(ann.font, "size") and ann.font.size is not None:
                        font_dict["size"] = ann.font.size
                    if hasattr(ann.font, "color") and ann.font.color is not None:
                        font_dict["color"] = ann.font.color
                    if font_dict:
                        ann_dict["font"] = font_dict

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

        # Apply custom tick positions and labels (for grouped-stacked bars)
        if "x_tickvals" in layout and "x_ticktext" in layout:
            ax.set_xticks(layout["x_tickvals"])
            ax.set_xticklabels(layout["x_ticktext"], rotation=45, ha="right")

        if "y_tickvals" in layout and "y_ticktext" in layout:
            ax.set_yticks(layout["y_tickvals"])
            ax.set_yticklabels(layout["y_ticktext"])

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
                # Clean HTML tags from text (e.g., <b>genome</b> → genome)
                import re

                text = ann["text"]
                text = re.sub(r"<b>(.*?)</b>", r"\1", text)  # Remove <b> tags
                text = re.sub(r"<i>(.*?)</i>", r"\1", text)  # Remove <i> tags

                # Build font properties
                font_props = {}
                if "font" in ann:
                    if "size" in ann["font"]:
                        font_props["fontsize"] = ann["font"]["size"]
                    if "color" in ann["font"]:
                        font_props["color"] = ann["font"]["color"]

                # Build annotation kwargs
                ann_kwargs: Dict[str, Any] = {
                    "xy": (ann["x"], ann["y"]),
                    "xytext": (ann["x"], ann["y"]),
                    "ha": "center",
                    "va": "center",
                }

                # Add rotation if present
                if "textangle" in ann:
                    ann_kwargs["rotation"] = ann["textangle"]

                # Add font properties
                ann_kwargs.update(font_props)

                # Add arrow if needed
                if ann.get("showarrow"):
                    ann_kwargs["arrowprops"] = dict(arrowstyle="->")

                ax.annotate(text, **ann_kwargs)
