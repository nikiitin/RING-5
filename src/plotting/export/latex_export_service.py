"""
LaTeX Export Service - Main API for publication-quality plot export.

Simple facade over MatplotlibConverter for easy integration.
"""

import logging
from typing import Union

import plotly.graph_objects as go

from src.plotting.export.converters.matplotlib_converter import MatplotlibConverter
from src.plotting.export.presets.preset_manager import PresetManager
from src.plotting.export.presets.preset_schema import ExportResult, LaTeXPreset

logger = logging.getLogger(__name__)


class LaTeXExportService:
    """
    Main API for exporting Plotly figures to LaTeX-optimized formats.

    Provides simple interface for converting interactive Plotly figures
    to publication-ready PDF, PGF, or EPS files with journal-specific presets.

    Example:
        >>> service = LaTeXExportService()
        >>> result = service.export(
        ...     fig=my_plotly_figure,
        ...     preset="single_column",
        ...     format="pdf"
        ... )
        >>> if result["success"]:
        ...     with open("figure.pdf", "wb") as f:
        ...         f.write(result["data"])
    """

    def __init__(self) -> None:
        """Initialize export service."""
        self.preset_manager = PresetManager()

    def export(
        self,
        fig: go.Figure,
        preset: Union[str, LaTeXPreset],
        format: str = "pdf",
    ) -> ExportResult:
        """
        Export Plotly figure to LaTeX-optimized format.

        Args:
            fig: Plotly Figure with user's interactive adjustments
            preset: Preset name (e.g., "single_column") or custom preset dict
            format: Output format - "pdf" (recommended), "pgf" (best for LaTeX),
                   or "eps" (legacy)

        Returns:
            ExportResult with binary data or error message

        Example:
            >>> result = service.export(fig, "single_column", "pdf")
            >>> if result["success"]:
            ...     print(f"Exported {len(result['data'])} bytes")
            ... else:
            ...     print(f"Error: {result['error']}")
        """
        try:
            # Load or validate preset
            if isinstance(preset, str):
                preset_dict = self.preset_manager.load_preset(preset)
            else:
                preset_dict = preset
                self.preset_manager.validate_preset(preset_dict)

            # Create converter and export
            converter = MatplotlibConverter(preset_dict)
            result = converter.convert(fig, format)

            logger.info(
                f"Exported figure to {format} "
                f"({len(result['data']) if result['data'] else 0} bytes)"
            )
            return result

        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            return ExportResult(
                success=False,
                data=None,
                format=format,
                error=str(e),
                metadata={},
            )

    def list_presets(self) -> list[str]:
        """
        Get list of available journal presets.

        Returns:
            List of preset names

        Example:
            >>> service.list_presets()
            ['single_column', 'double_column', 'nature', 'ieee', ...]
        """
        return self.preset_manager.list_presets()

    def get_preset_info(self, preset_name: str) -> LaTeXPreset:
        """
        Get the full configuration for a preset.

        This is a convenience wrapper around ``PresetManager.load_preset`` and
        returns the complete LaTeX export preset configuration, not just
        summary metadata.

        Args:
            preset_name: Name of preset to inspect.

        Returns:
            LaTeXPreset: Full preset configuration dictionary.

        Example:
            >>> info = service.get_preset_info("single_column")
            >>> print(f"Width: {info['width_inches']} inches")
        """
        return self.preset_manager.load_preset(preset_name)

    def generate_preview(
        self,
        fig: go.Figure,
        preset: Union[str, LaTeXPreset],
        preview_dpi: int = 150,
    ) -> bytes:
        """
        Generate a PNG preview of how the exported figure will look.

        Useful for showing users the export result before generating
        the full-resolution file.

        Args:
            fig: Plotly Figure to preview
            preset: Preset name or custom preset dict
            preview_dpi: DPI for preview image (default 150 for fast rendering)

        Returns:
            PNG image data as bytes

        Example:
            >>> preview_png = service.generate_preview(fig, "single_column")
            >>> with open("preview.png", "wb") as f:
            ...     f.write(preview_png)
        """
        try:
            # Load or validate preset
            if isinstance(preset, str):
                preset_dict = self.preset_manager.load_preset(preset)
            else:
                preset_dict = preset
                self.preset_manager.validate_preset(preset_dict)

            # Create converter and generate preview
            converter = MatplotlibConverter(preset_dict)
            preview_data = converter.generate_preview(fig, preview_dpi=preview_dpi)

            logger.info(f"Generated preview ({len(preview_data)} bytes)")
            return preview_data

        except Exception as e:
            logger.error(f"Preview generation failed: {e}", exc_info=True)
            raise
