"""
Base converter for LaTeX exports (Strategy Pattern).

Defines abstract interface that all converter implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import List

import plotly.graph_objects as go

from src.plotting.export.presets.preset_schema import ExportResult, LaTeXPreset


class BaseConverter(ABC):
    """
    Abstract base class for figure converters.

    Converters transform Plotly figures into publication-ready formats
    (PDF, PGF, PNG, etc.) with proper sizing and styling for LaTeX documents.

    Implementations must provide:
    - convert(): Transform figure to target format
    - get_supported_formats(): Declare output formats
    - validate_figure(): Check figure compatibility

    Example:
        class MatplotlibConverter(BaseConverter):
            def convert(self, figure, preset):
                # Convert via Matplotlib
                return result
    """

    @abstractmethod
    def convert(
        self,
        figure: go.Figure,
        preset: LaTeXPreset,
        preserve_layout: bool = True,
    ) -> ExportResult:
        """
        Convert Plotly figure to target format.

        Args:
            figure: Plotly figure to convert
            preset: LaTeX preset with dimensions, fonts, DPI
            preserve_layout: If True, preserve user's interactive layout choices
                           (axis limits, legend position, etc.)

        Returns:
            ExportResult with binary data and metadata

        Raises:
            ValueError: If figure is invalid or conversion fails
        """
        pass

    def get_supported_formats(self) -> List[str]:
        """
        Get list of output formats this converter supports.

        Returns:
            List of format strings (e.g., ["pdf", "pgf", "png"])
        """
        return []

    def validate_figure(self, figure: go.Figure) -> None:
        """
        Validate that figure is compatible with this converter.

        Args:
            figure: Plotly figure to validate

        Raises:
            ValueError: If figure is invalid (empty, unsupported trace types, etc.)
        """
        if not figure.data:
            raise ValueError("Figure has no data (no traces)")
