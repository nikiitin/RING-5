"""
Export module - LaTeX-optimized export with Matplotlib.

Legacy Kaleido-based export has been removed. Use MatplotlibConverter for
publication-quality PDF/PGF/EPS export.
"""

from src.plotting.export.converters.matplotlib_converter import MatplotlibConverter
from src.plotting.export.presets.preset_manager import PresetManager

__all__ = ["MatplotlibConverter", "PresetManager"]
