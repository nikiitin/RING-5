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
            def __init__(self, preset: LaTeXPreset):
                self.preset = preset

            def convert(self, figure, format):
                # Convert via Matplotlib
                return result
    """

    def __init__(self, preset: LaTeXPreset) -> None:
        """
        Initialize converter with LaTeX preset.

        Args:
            preset: LaTeX export configuration
        """
        self.preset = preset

    @abstractmethod
    def convert(
        self,
        figure: go.Figure,
        format: str,
    ) -> ExportResult:
        """
        Convert Plotly figure to target format.

        Args:
            figure: Plotly figure to convert
            format: Output format (e.g., "pdf", "pgf", "eps")

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

    def validate_figure(self, figure: go.Figure) -> bool:
        """
        Validate that figure is compatible with this converter.

        Args:
            figure: Plotly figure to validate

        Returns:
            True if valid, False otherwise
        """
        return bool(figure.data)
