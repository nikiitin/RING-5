"""
Unit tests for base converter (abstract strategy).

Tests the abstract converter interface that all converters must implement.
"""

from typing import List

import plotly.graph_objects as go
import pytest

from src.plotting.export.converters.base_converter import BaseConverter
from src.plotting.export.presets.preset_schema import ExportResult, LaTeXPreset


class MockConverter(BaseConverter):
    """Concrete implementation for testing base class."""

    def __init__(self, preset: LaTeXPreset) -> None:
        """Initialize with preset."""
        super().__init__(preset)

    def convert(
        self,
        figure: go.Figure,
        format: str,
        preserve_layout: bool = True,
    ) -> ExportResult:
        """Mock conversion that returns success."""
        return {
            "success": True,
            "data": b"mock data",
            "format": format,
            "error": None,
            "metadata": {"converter": "mock"},
        }

    def get_supported_formats(self) -> List[str]:
        """Return mock supported formats."""
        return ["mock", "test"]


class TestBaseConverter:
    """Test base converter interface."""

    @staticmethod
    def _create_test_preset() -> LaTeXPreset:
        """Create a standard preset for testing."""
        return {
            "width_inches": 3.5,
            "height_inches": 2.625,
            "font_family": "serif",
            "font_size_base": 9,
            "font_size_labels": 8,
            "font_size_title": 10,
            "font_size_ticks": 7,
            "line_width": 1.0,
            "marker_size": 4,
            "dpi": 300,
        }

    def test_base_converter_is_abstract(self) -> None:
        """Verify BaseConverter cannot be instantiated directly."""
        preset = self._create_test_preset()
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseConverter(preset)  # type: ignore

    def test_concrete_converter_can_instantiate(self) -> None:
        """Verify concrete implementations can be created."""
        preset = self._create_test_preset()
        converter = MockConverter(preset)
        assert converter is not None
        assert converter.preset == preset

    def test_convert_method_required(self) -> None:
        """Verify convert() method is required in subclasses."""
        # MockConverter implements convert(), so this should work
        preset = self._create_test_preset()
        converter = MockConverter(preset)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))

        result = converter.convert(fig, "mock")
        assert result["success"] is True

    def test_get_supported_formats_method(self) -> None:
        """Verify converters declare supported formats."""
        preset = self._create_test_preset()
        converter = MockConverter(preset)

        # Base class should have this method
        formats = converter.get_supported_formats()

        # Should return list of strings
        assert isinstance(formats, list)
        assert all(isinstance(fmt, str) for fmt in formats)

    def test_validate_figure_method(self) -> None:
        """Verify converters can validate Plotly figures."""
        preset = self._create_test_preset()
        converter = MockConverter(preset)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))

        # Should return True for valid figure
        result = converter.validate_figure(fig)
        assert result is True

    def test_validate_figure_rejects_empty_figure(self) -> None:
        """Verify validation catches empty figures."""
        preset = self._create_test_preset()
        converter = MockConverter(preset)

        empty_fig = go.Figure()

        # Should return False for empty figure
        result = converter.validate_figure(empty_fig)
        assert result is False
