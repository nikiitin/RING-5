"""
Layout mapper for preserving Plotly layout in Matplotlib exports.

Extracts layout properties (axis limits, legend position, titles, etc.)
from Plotly figures and applies them to Matplotlib axes.
"""

from typing import Any, Dict, List, Optional, Tuple

import plotly.graph_objects as go
from matplotlib.axes import Axes

from src.web.pages.ui.plotting.export.presets.preset_schema import LaTeXPreset

from .layout_applier import LayoutApplier


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

        # Extract tick visibility settings (e.g. numbered X-axis hides ticks)
        if layout.xaxis.showticklabels is not None:
            props["x_showticklabels"] = layout.xaxis.showticklabels
        if layout.xaxis.ticks is not None:
            props["x_ticks"] = layout.xaxis.ticks

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

                # Extract box/border properties (for legend-style annotations)
                if hasattr(ann, "borderwidth") and ann.borderwidth is not None:
                    ann_dict["borderwidth"] = ann.borderwidth
                if hasattr(ann, "bordercolor") and ann.bordercolor is not None:
                    ann_dict["bordercolor"] = ann.bordercolor
                if hasattr(ann, "borderpad") and ann.borderpad is not None:
                    ann_dict["borderpad"] = ann.borderpad
                if hasattr(ann, "bgcolor") and ann.bgcolor is not None:
                    ann_dict["bgcolor"] = ann.bgcolor
                if hasattr(ann, "align") and ann.align is not None:
                    ann_dict["align"] = ann.align

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

        Delegates to LayoutApplier for the actual application logic.
        Maintained as static method for backward compatibility.

        Args:
            ax: Matplotlib axes to modify
            layout: Layout dictionary from extract_layout()
            preset: Optional preset dict with font sizes (for proper sizing)
        """
        applier = LayoutApplier(preset)
        applier.apply_to_matplotlib(ax, layout)
