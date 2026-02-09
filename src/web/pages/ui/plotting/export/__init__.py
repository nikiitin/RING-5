"""
Export module - LaTeX-optimized export with Matplotlib.

Main API: Use LaTeXExportService for simple, high-level export operations.
Advanced: Use MatplotlibConverter directly for custom workflows.
"""

from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (
    MatplotlibConverter,
)
from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService
from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager

__all__ = ["LaTeXExportService", "MatplotlibConverter", "PresetManager"]
