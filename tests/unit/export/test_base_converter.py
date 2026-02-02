"""
Unit tests for base converter (abstract strategy).

Tests the abstract converter interface that all converters must implement.
"""

import plotly.graph_objects as go
import pytest

from src.plotting.export.converters.base_converter import BaseConverter
from src.plotting.export.presets.preset_schema import ExportResult, LaTeXPreset


class MockConverter(BaseConverter):
    """Concrete implementation for testing base class."""

    def convert(
        self,
        figure: go.Figure,
        preset: LaTeXPreset,
        preserve_layout: bool = True,
    ) -> ExportResult:
        """Mock conversion that returns success."""
        return {
            "success": True,
            "data": b"mock data",
            "format": "mock",
            "error": None,
            "metadata": {"converter": "mock"},
        }


class TestBaseConverter:
    """Test base converter interface."""

    def test_base_converter_is_abstract(self) -> None:
        """Verify BaseConverter cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseConverter()  # type: ignore

    def test_concrete_converter_can_instantiate(self) -> None:
        """Verify concrete implementations can be created."""
        converter = MockConverter()
        assert converter is not None

    def test_convert_method_required(self) -> None:
        """Verify convert() method is required in subclasses."""
        # MockConverter implements convert(), so this should work
        converter = MockConverter()

        fig = go.Figure()
        preset: LaTeXPreset = {
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

        result = converter.convert(fig, preset)
        assert result["success"] is True

    def test_get_supported_formats_method(self) -> None:
        """Verify converters declare supported formats."""
        converter = MockConverter()

        # Base class should have this method
        formats = converter.get_supported_formats()

        # Should return list of strings
        assert isinstance(formats, list)
        assert all(isinstance(fmt, str) for fmt in formats)

    def test_validate_figure_method(self) -> None:
        """Verify converters can validate Plotly figures."""
        converter = MockConverter()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))

        # Should not raise for valid figure
        converter.validate_figure(fig)

    def test_validate_figure_rejects_empty_figure(self) -> None:
        """Verify validation catches empty figures."""
        converter = MockConverter()

        empty_fig = go.Figure()

        with pytest.raises(ValueError, match="Figure has no data"):
            converter.validate_figure(empty_fig)
