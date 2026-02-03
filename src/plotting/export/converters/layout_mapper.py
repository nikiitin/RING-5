"""
Layout mapper for preserving Plotly layout in Matplotlib exports.

Extracts layout properties (axis limits, legend position, titles, etc.)
from Plotly figures and applies them to Matplotlib axes.
"""

from typing import Any, Dict, List, Optional, Tuple

import plotly.graph_objects as go
from matplotlib.axes import Axes

from ..presets.preset_schema import LaTeXPreset


class LayoutExtractor:
    """
    Extracts layout properties from Plotly figures.

    Breaks down the extraction process into focused methods for better
    maintainability and testability. Each method handles a specific
    category of layout properties.
    """

    def extract_layout(self, figure: go.Figure) -> Dict[str, Any]:
        """
        Extract layout properties from Plotly figure.

        Orchestrates extraction of all layout components and combines
        them into a single dictionary.

        Args:
            figure: Plotly figure to extract from

        Returns:
            Dictionary with layout properties
        """
        layout_dict: Dict[str, Any] = {}

        # Extract different categories of properties
        layout_dict.update(self._extract_axis_properties(figure.layout))
        layout_dict.update(self._extract_legend_settings(figure.layout))
        layout_dict.update(self._extract_annotations(figure.layout))

        return layout_dict

    def _extract_axis_properties(self, layout: go.Layout) -> Dict[str, Any]:
        """
        Extract axis-related properties.

        Args:
            layout: Plotly layout object

        Returns:
            Dictionary with axis ranges, labels, scales, grids, and ticks
        """
        props: Dict[str, Any] = {}

        # Extract axis ranges
        if layout.xaxis.range is not None:
            props["x_range"] = list(layout.xaxis.range)
        if layout.yaxis.range is not None:
            props["y_range"] = list(layout.yaxis.range)

        # Extract axis labels
        if layout.xaxis.title is not None:
            props["x_label"] = layout.xaxis.title.text
        if layout.yaxis.title is not None:
            props["y_label"] = layout.yaxis.title.text

        # Extract title
        if layout.title is not None and layout.title.text:
            props["title"] = layout.title.text

        # Extract grid settings
        if layout.xaxis.showgrid is not None:
            props["x_grid"] = layout.xaxis.showgrid
        if layout.yaxis.showgrid is not None:
            props["y_grid"] = layout.yaxis.showgrid

        # Extract axis types (linear, log, etc.)
        if layout.xaxis.type is not None:
            props["x_type"] = layout.xaxis.type
        if layout.yaxis.type is not None:
            props["y_type"] = layout.yaxis.type

        # Extract custom tick positions and labels (for grouped-stacked bars)
        if layout.xaxis.tickmode == "array":
            if layout.xaxis.tickvals is not None:
                props["x_tickvals"] = list(layout.xaxis.tickvals)
            if layout.xaxis.ticktext is not None:
                props["x_ticktext"] = [str(t) for t in layout.xaxis.ticktext]

        if layout.yaxis.tickmode == "array":
            if layout.yaxis.tickvals is not None:
                props["y_tickvals"] = list(layout.yaxis.tickvals)
            if layout.yaxis.ticktext is not None:
                props["y_ticktext"] = [str(t) for t in layout.yaxis.ticktext]

        return props

    def _extract_legend_settings(self, layout: go.Layout) -> Dict[str, Any]:
        """
        Extract legend positioning and anchor settings.

        Args:
            layout: Plotly layout object

        Returns:
            Dictionary with legend configuration (empty if no legend)
        """
        if layout.legend is None:
            return {}

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
            return {"legend": legend_dict}
        return {}

    def _detect_ylabel_from_annotation(self, annotations: Tuple[Any, ...]) -> Optional[str]:
        """
        Detect if Y-axis label is stored as annotation.

        Plotly sometimes stores axis titles as annotations with textangle=-90.
        This method identifies such annotations based on their properties.

        Args:
            annotations: Tuple of Plotly annotation objects

        Returns:
            Y-axis label text if found, None otherwise
        """
        if not annotations:
            return None

        for ann in annotations:
            # Check if this looks like a Y-axis label annotation
            if (
                hasattr(ann, "textangle")
                and ann.textangle is not None
                and abs(ann.textangle + 90) < 1  # textangle close to -90
                and hasattr(ann, "xref")
                and ann.xref == "paper"
                and ann.x is not None
                and ann.x < 0.1  # Near left edge
            ):
                return str(ann.text)

        return None

    def _extract_annotations(self, layout: go.Layout) -> Dict[str, Any]:
        """
        Extract annotations with coordinate reference info.

        Filters out annotations that are actually Y-axis labels
        (stored as annotations with specific properties).

        Args:
            layout: Plotly layout object

        Returns:
            Dictionary with annotations list and potentially y_label
        """
        result: Dict[str, Any] = {}

        # Get axis label text to filter from annotations
        y_label_text: Optional[str] = None
        if layout.yaxis.title is not None and layout.yaxis.title.text:
            y_label_text = layout.yaxis.title.text

        # Check if y-axis label is stored as annotation
        y_label_from_annotation = self._detect_ylabel_from_annotation(
            layout.annotations if layout.annotations else ()
        )

        if y_label_from_annotation:
            y_label_text = y_label_from_annotation
            # If no yaxis.title but found annotation, use it as y_label
            if "y_label" not in result and not layout.yaxis.title:
                result["y_label"] = y_label_from_annotation

        # Extract annotations with full coordinate reference info
        if layout.annotations:
            annotations: List[Dict[str, Any]] = []
            for ann in layout.annotations:
                # Skip annotations that are Y-axis labels
                if y_label_text and ann.text and ann.text.strip() == y_label_text.strip():
                    continue

                ann_dict: Dict[str, Any] = {
                    "x": ann.x,
                    "y": ann.y,
                    "text": ann.text,
                    "showarrow": ann.showarrow,
                }

                # Extract coordinate references (critical for proper positioning)
                if hasattr(ann, "xref") and ann.xref is not None:
                    ann_dict["xref"] = ann.xref
                if hasattr(ann, "yref") and ann.yref is not None:
                    ann_dict["yref"] = ann.yref

                # Extract text angle (rotation)
                if hasattr(ann, "textangle") and ann.textangle is not None:
                    ann_dict["textangle"] = ann.textangle

                # Extract vertical/horizontal anchor
                if hasattr(ann, "xanchor") and ann.xanchor is not None:
                    ann_dict["xanchor"] = ann.xanchor
                if hasattr(ann, "yanchor") and ann.yanchor is not None:
                    ann_dict["yanchor"] = ann.yanchor

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

            if annotations:
                result["annotations"] = annotations

        return result


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
    def _escape_latex(text: str) -> str:
        """
        Escape special LaTeX characters in text.

        Args:
            text: Text to escape

        Returns:
            Text with LaTeX special characters escaped
        """
        # Escape LaTeX special characters in specific order:
        # 1. Backslash first (before others that may introduce backslashes)
        # 2. Then braces (before others that may introduce braces)
        # 3. Then remaining characters

        # Step 1: Escape backslashes using a placeholder
        text = text.replace("\\", "<<<BACKSLASH>>>")

        # Step 2: Escape curly braces
        text = text.replace("{", r"\{")
        text = text.replace("}", r"\}")

        # Step 3: Replace backslash placeholder
        text = text.replace("<<<BACKSLASH>>>", r"\textbackslash{}")

        # Step 4: Escape remaining characters
        replacements = {
            "_": r"\_",
            "%": r"\%",
            "&": r"\&",
            "$": r"\$",
            "#": r"\#",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text

    @staticmethod
    def extract_layout(figure: go.Figure) -> Dict[str, Any]:
        """
        Extract layout properties from Plotly figure.

        Delegates to LayoutExtractor for the actual extraction logic.
        Maintained as static method for backward compatibility.

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
        extractor = LayoutExtractor()
        return extractor.extract_layout(figure)

    @staticmethod
    def apply_to_matplotlib(
        ax: Axes, layout: Dict[str, Any], preset: LaTeXPreset | None = None
    ) -> None:
        """
        Apply extracted layout to Matplotlib axes.

        Args:
            ax: Matplotlib axes to modify
            layout: Layout dictionary from extract_layout()
            preset: Optional preset dict with font sizes (for proper sizing)
        """
        # Get font sizes from preset or use defaults
        font_size_title = preset.get("font_size_title", 10) if preset else 10
        font_size_xlabel = preset.get("font_size_xlabel", 9) if preset else 9
        font_size_ylabel = preset.get("font_size_ylabel", 9) if preset else 9
        # Note: font_size_legend and bold_legend are used in matplotlib_converter
        font_size_ticks = preset.get("font_size_ticks", 7) if preset else 7
        font_size_annotations = preset.get("font_size_annotations", 6) if preset else 6

        # Get bold styling flags from preset or use defaults
        bold_title = preset.get("bold_title", False) if preset else False
        bold_xlabel = preset.get("bold_xlabel", False) if preset else False
        bold_ylabel = preset.get("bold_ylabel", False) if preset else False
        # Note: bold_legend is used in matplotlib_converter
        bold_ticks = preset.get("bold_ticks", False) if preset else False
        bold_annotations = preset.get("bold_annotations", True) if preset else True

        # Get positioning parameters from preset or use defaults
        ylabel_pad = preset.get("ylabel_pad", 10.0) if preset else 10.0
        ylabel_y_position = preset.get("ylabel_y_position", 0.5) if preset else 0.5
        xtick_pad = preset.get("xtick_pad", 5.0) if preset else 5.0
        ytick_pad = preset.get("ytick_pad", 5.0) if preset else 5.0
        group_label_offset = preset.get("group_label_offset", -0.12) if preset else -0.12
        group_label_alternate = preset.get("group_label_alternate", True) if preset else True

        # Get axis and bar spacing parameters
        xaxis_margin = preset.get("xaxis_margin", 0.02) if preset else 0.02
        xtick_rotation = preset.get("xtick_rotation", 45.0) if preset else 45.0
        xtick_ha = preset.get("xtick_ha", "right") if preset else "right"
        xtick_offset = preset.get("xtick_offset", 0.0) if preset else 0.0

        # Group separator parameters
        group_separator = preset.get("group_separator", False) if preset else False
        group_separator_style = (
            preset.get("group_separator_style", "dashed") if preset else "dashed"
        )
        group_separator_color = preset.get("group_separator_color", "gray") if preset else "gray"

        # Apply axis ranges with adjustable margins
        if "x_range" in layout:
            x_min, x_max = layout["x_range"]
            x_span = x_max - x_min
            # Apply margin to compress whitespace
            ax.set_xlim(x_min - x_span * xaxis_margin, x_max + x_span * xaxis_margin)
        else:
            # If no explicit range, tighten the margins
            ax.margins(x=xaxis_margin)

        if "y_range" in layout:
            ax.set_ylim(layout["y_range"])

        # Apply axis labels with proper font size and padding
        if "x_label" in layout and layout["x_label"]:
            ax.set_xlabel(
                LayoutMapper._escape_latex(layout["x_label"]),
                fontsize=font_size_xlabel,
                fontweight="bold" if bold_xlabel else "normal",
            )

        if "y_label" in layout:
            y_label_val = layout["y_label"]
            if y_label_val:
                # Y-axis label: escape LaTeX, set fontsize, rotation and padding
                y_label = LayoutMapper._escape_latex(y_label_val)
                # Use labelpad for distance from tick labels (in points)
                # Typical values: 10-50 points depending on tick label width
                # ylabel_y_position: vertical position (0=bottom, 0.5=center, 1=top)
                ax.set_ylabel(
                    y_label,
                    fontsize=font_size_ylabel,
                    fontweight="bold" if bold_ylabel else "normal",
                    rotation=90,
                    labelpad=ylabel_pad,
                    y=ylabel_y_position,
                )

        # Apply title
        if "title" in layout and layout["title"]:
            ax.set_title(
                LayoutMapper._escape_latex(layout["title"]),
                fontsize=font_size_title,
                fontweight="bold" if bold_title else "normal",
            )

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

        # Apply tick padding for proper spacing
        ax.tick_params(axis="x", pad=xtick_pad)
        ax.tick_params(axis="y", pad=ytick_pad)

        # Apply custom tick positions and labels (for grouped-stacked bars)
        if "x_tickvals" in layout and "x_ticktext" in layout:
            ax.set_xticks(layout["x_tickvals"])
            # Escape LaTeX special characters in tick labels
            # Matplotlib renders tick labels in text mode, so simple escaping is sufficient
            escaped_labels = [
                LayoutMapper._escape_latex(str(label)) for label in layout["x_ticktext"]
            ]
            # Use configurable rotation, alignment and font for tick labels
            ax.set_xticklabels(
                escaped_labels,
                rotation=xtick_rotation,
                ha=xtick_ha,
                fontsize=font_size_ticks,
                fontweight="bold" if bold_ticks else "normal",
            )

            # Apply horizontal offset to tick labels if specified
            if xtick_offset != 0.0:
                from matplotlib.transforms import ScaledTranslation

                dx = xtick_offset / 72.0  # Convert points to inches
                offset_transform = ScaledTranslation(dx, 0, ax.figure.dpi_scale_trans)
                for label in ax.get_xticklabels():
                    label.set_transform(label.get_transform() + offset_transform)

        if "y_tickvals" in layout and "y_ticktext" in layout:
            ax.set_yticks(layout["y_tickvals"])
            # Escape LaTeX special characters in tick labels
            # Matplotlib renders tick labels in text mode, so simple escaping is sufficient
            escaped_labels = [
                LayoutMapper._escape_latex(str(label)) for label in layout["y_ticktext"]
            ]
            ax.set_yticklabels(
                escaped_labels,
                fontsize=font_size_ticks,
                fontweight="bold" if bold_ticks else "normal",
            )

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
            # Track grouping label index for alternation
            grouping_label_index = 0

            for ann in layout["annotations"]:
                # Clean HTML tags from text (e.g., <b>genome</b> → genome)
                import re

                text = ann["text"]
                text = re.sub(r"<b>(.*?)</b>", r"\1", text)  # Remove <b> tags
                text = re.sub(r"<i>(.*?)</i>", r"\1", text)  # Remove <i> tags

                # Escape LaTeX special characters
                # Annotations are rendered in text mode by matplotlib
                text = LayoutMapper._escape_latex(text)

                # Determine coordinate system based on xref/yref
                # Plotly: 'x'/'y' = data coords, 'paper' = 0-1 axes fraction
                xref = ann.get("xref", "x")
                yref = ann.get("yref", "y")

                # Determine annotation type for proper font sizing:
                # - Bar totals: yref='y' (data), typically numbers above bars
                # - Grouping labels: yref='paper', y < 0 (below x-axis)
                is_bar_total = yref != "paper" and xref != "paper"
                is_grouping_label = yref == "paper" and ann["y"] < 0

                # Build font properties based on annotation type
                if is_bar_total:
                    # Bar totals use smallest font (annotations)
                    font_props: Dict[str, Any] = {
                        "fontsize": font_size_annotations,
                        "weight": "bold" if bold_annotations else "normal",
                    }
                elif is_grouping_label:
                    # Grouping labels (benchmark names) use xlabel font
                    font_props = {
                        "fontsize": font_size_xlabel,
                        "weight": "bold" if bold_xlabel else "normal",
                    }
                else:
                    # Default to annotations font
                    font_props = {
                        "fontsize": font_size_annotations,
                        "weight": "bold" if bold_annotations else "normal",
                    }

                # Apply color if present
                if "font" in ann and "color" in ann["font"]:
                    font_props["color"] = ann["font"]["color"]

                # Calculate y position for grouping labels
                y_pos = ann["y"]
                if is_grouping_label:
                    # Apply user-configurable offset
                    y_pos = group_label_offset
                    # Alternate up/down if enabled
                    if group_label_alternate:
                        # Even indices: lower, Odd indices: higher
                        if grouping_label_index % 2 == 1:
                            y_pos = group_label_offset - 0.05  # 5% lower
                        grouping_label_index += 1

                # Determine matplotlib xycoords based on Plotly refs
                # Type can be str or tuple[str, str] for mixed coordinate systems
                xycoords: str | tuple[str, str]
                if xref == "paper" and yref == "paper":
                    xycoords = "axes fraction"
                elif xref == "paper":
                    # Mixed: x is axes fraction, y is data
                    xycoords = ("axes fraction", "data")
                elif yref == "paper":
                    # Mixed: x is data, y is axes fraction
                    xycoords = ("data", "axes fraction")
                else:
                    # Both are data coordinates
                    xycoords = "data"

                # Determine vertical alignment based on yanchor or position
                yanchor = ann.get("yanchor", "auto")
                if yanchor == "top":
                    va = "top"
                elif yanchor == "bottom":
                    va = "bottom"
                elif yanchor == "middle":
                    va = "center"
                else:
                    # Auto: if y < 0 (below axis), use top; if above bars, use bottom
                    if yref == "paper" and ann["y"] < 0:
                        va = "top"
                    else:
                        va = "bottom"

                # Determine horizontal alignment based on xanchor
                xanchor = ann.get("xanchor", "center")
                if xanchor == "left":
                    ha = "left"
                elif xanchor == "right":
                    ha = "right"
                else:
                    ha = "center"

                # Build annotation kwargs
                ann_kwargs: Dict[str, Any] = {
                    "xy": (ann["x"], y_pos),
                    "xycoords": xycoords,
                    "ha": ha,
                    "va": va,
                }

                # Add rotation if present
                if "textangle" in ann:
                    ann_kwargs["rotation"] = -ann["textangle"]  # Plotly uses opposite sign

                # Add font properties
                ann_kwargs.update(font_props)

                ax.annotate(text, **ann_kwargs)

            # Draw group separator before last group if enabled
            if group_separator:
                # Collect grouping label x positions
                # These labels have xref='x' (data coords) and yref='paper' with y < 0
                grouping_positions = []
                for ann in layout["annotations"]:
                    xref = ann.get("xref", "x")
                    yref = ann.get("yref", "y")
                    # Grouping labels are positioned at yref=paper, y<0 below the axis
                    if yref == "paper" and ann["y"] < 0 and xref == "x":
                        # This is a grouping label, x is in data coordinates
                        grouping_positions.append(ann["x"])

                # Draw separator before last group if we have 2+ groups
                if len(grouping_positions) >= 2:
                    # Sort positions and find midpoint between last two
                    grouping_positions.sort()
                    last_pos = grouping_positions[-1]
                    second_last_pos = grouping_positions[-2]
                    separator_x = (second_last_pos + last_pos) / 2

                    # Map line style
                    linestyle_map = {
                        "dashed": "--",
                        "dotted": ":",
                        "solid": "-",
                        "dashdot": "-.",
                    }
                    ls = linestyle_map.get(group_separator_style, "--")

                    # Draw vertical line in data x coordinates, full height
                    # Use blended transform: x in data coords, y in axes fraction
                    from matplotlib.transforms import blended_transform_factory

                    trans = blended_transform_factory(ax.transData, ax.transAxes)
                    ax.plot(
                        [separator_x, separator_x],
                        [0, 1],
                        transform=trans,
                        linestyle=ls,
                        color=group_separator_color,
                        linewidth=0.8,
                        alpha=0.6,
                        clip_on=False,
                    )
