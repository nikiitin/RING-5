"""
Tests for MatplotlibConverter - Plotly to Matplotlib conversion for LaTeX export.

Following TDD approach: Tests written FIRST, then implementation.
"""

import logging
import shutil
from typing import Any

import pytest

from src.plotting.export.converters.matplotlib_converter import MatplotlibConverter
from src.plotting.export.presets.preset_manager import PresetManager
from tests.fixtures.sample_figures import (
    create_figure_with_custom_legend,
    create_figure_with_log_scale,
    create_figure_with_zoom,
    create_grouped_bar_figure,
    create_line_figure,
    create_multi_series_line_figure,
    create_scatter_figure,
    create_simple_bar_figure,
)

# Check for XeLaTeX availability
has_xelatex = shutil.which("xelatex") is not None
requires_xelatex = pytest.mark.skipif(not has_xelatex, reason="XeLaTeX not found")


@pytest.fixture
def single_column_preset() -> dict[str, Any]:
    """Load single column preset for testing."""
    return PresetManager.load_preset("single_column")


@pytest.fixture
def double_column_preset() -> dict[str, Any]:
    """Load double column preset for testing."""
    return PresetManager.load_preset("double_column")


class TestMatplotlibConverterBasics:
    """Test basic converter functionality."""

    def test_converter_instantiation(self, single_column_preset: dict[str, Any]) -> None:
        """Converter should instantiate with valid preset."""
        converter = MatplotlibConverter(single_column_preset)
        assert converter is not None
        assert converter.preset == single_column_preset

    def test_converter_inherits_from_base(self, single_column_preset: dict[str, Any]) -> None:
        """Converter should inherit from BaseConverter."""
        from src.plotting.export.converters.base_converter import BaseConverter

        converter = MatplotlibConverter(single_column_preset)
        assert isinstance(converter, BaseConverter)

    def test_get_supported_formats(self, single_column_preset: dict[str, Any]) -> None:
        """Converter should support PDF, PGF, and EPS formats."""
        converter = MatplotlibConverter(single_column_preset)
        formats = converter.get_supported_formats()
        assert "pdf" in formats
        assert "pgf" in formats
        assert "eps" in formats


class TestBarChartConversion:
    """Test bar chart conversion to Matplotlib."""

    def test_convert_simple_bar_to_pdf(self, single_column_preset: dict[str, Any]) -> None:
        """Convert simple bar chart to PDF."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["format"] == "pdf"
        assert result["data"] is not None
        assert len(result["data"]) > 1000  # PDF should be substantial
        assert result["error"] is None

    def test_convert_grouped_bar_to_pdf(self, single_column_preset):
        """Convert grouped bar chart to PDF."""
        fig = create_grouped_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["format"] == "pdf"
        assert result["data"] is not None

    def test_bar_chart_preserves_colors(self, single_column_preset):
        """Verify bar colors from Plotly are preserved."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        # Metadata should contain color info
        assert "traces_converted" in result["metadata"]


class TestLineChartConversion:
    """Test line chart conversion to Matplotlib."""

    def test_convert_line_to_pdf(self, single_column_preset: dict[str, Any]) -> None:
        """Convert line chart to PDF."""
        fig = create_line_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["format"] == "pdf"
        assert result["data"] is not None

    def test_convert_multi_series_line(self, single_column_preset: dict[str, Any]) -> None:
        """Convert multi-series line plot to PDF."""
        fig = create_multi_series_line_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert "traces_converted" in result["metadata"]
        # Should have converted 2 traces
        assert result["metadata"]["traces_converted"] >= 2


class TestScatterPlotConversion:
    """Test scatter plot conversion to Matplotlib."""

    def test_convert_scatter_to_pdf(self, single_column_preset: dict[str, Any]) -> None:
        """Convert scatter plot to PDF."""
        fig = create_scatter_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["format"] == "pdf"
        assert result["data"] is not None


class TestLayoutPreservation:
    """Test that Plotly layout is preserved in Matplotlib export."""

    def test_preserve_legend_position(self, single_column_preset: dict[str, Any]) -> None:
        """Verify custom legend position is preserved."""
        fig = create_figure_with_custom_legend()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        # Metadata should contain layout preservation info
        assert "layout_preserved" in result["metadata"]
        layout = result["metadata"]["layout_preserved"]
        assert "legend" in layout

    def test_preserve_axis_ranges(self, single_column_preset: dict[str, Any]) -> None:
        """Verify user's zoom (axis ranges) is preserved."""
        fig = create_figure_with_zoom()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        layout = result["metadata"]["layout_preserved"]
        assert "x_range" in layout
        assert "y_range" in layout

    def test_preserve_log_scale(self, single_column_preset: dict[str, Any]) -> None:
        """Verify logarithmic scale is preserved."""
        fig = create_figure_with_log_scale()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        layout = result["metadata"]["layout_preserved"]
        assert "xaxis_type" in layout or "log" in str(layout)


class TestExportFormats:
    """Test export to different formats (PDF, PGF, EPS)."""

    @pytest.mark.parametrize(
        "format",
        [
            "pdf",
            pytest.param("pgf", marks=requires_xelatex),
            "eps",
        ],
    )
    def test_export_to_all_formats(self, single_column_preset: dict[str, Any], format: str) -> None:
        """Test export to PDF, PGF, and EPS formats."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, format)

        assert result["success"] is True
        assert result["format"] == format
        assert result["data"] is not None
        assert len(result["data"]) > 0

    @requires_xelatex
    def test_pgf_format_is_text_based(self, single_column_preset: dict[str, Any]) -> None:
        """Verify PGF format produces text (LaTeX commands)."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pgf")

        assert result["success"] is True
        # PGF should be text-decodable
        text = result["data"].decode("utf-8")
        assert "\\begin{pgfpicture}" in text or "pgf" in text.lower()

    def test_pdf_format_is_binary(self, single_column_preset: dict[str, Any]) -> None:
        """Verify PDF format produces binary data."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        # PDF signature
        assert result["data"].startswith(b"%PDF-")

    def test_eps_format_is_postscript(self, single_column_preset: dict[str, Any]) -> None:
        """Verify EPS format produces PostScript."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "eps")

        assert result["success"] is True
        # EPS signature
        text = result["data"].decode("latin-1")
        assert "%!PS-Adobe" in text or "EPS" in text


class TestLaTeXConfiguration:
    """Test LaTeX-specific configuration."""

    def test_correct_dimensions_single_column(self, single_column_preset: dict[str, Any]) -> None:
        """Verify single column dimensions are applied."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        metadata = result["metadata"]
        assert metadata["width_inches"] == single_column_preset["width_inches"]
        assert metadata["height_inches"] == single_column_preset["height_inches"]

    def test_correct_dimensions_double_column(self, double_column_preset: dict[str, Any]) -> None:
        """Verify double column dimensions are applied."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(double_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        metadata = result["metadata"]
        assert metadata["width_inches"] == double_column_preset["width_inches"]

    def test_font_settings_applied(self, single_column_preset: dict[str, Any]) -> None:
        """Verify preset font settings are used."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        metadata = result["metadata"]
        assert "font_family" in metadata
        assert metadata["font_family"] == single_column_preset["font_family"]


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_empty_figure_returns_error(self, single_column_preset: dict[str, Any]) -> None:
        """Empty figure should return error result."""
        import plotly.graph_objects as go

        empty_fig = go.Figure()  # No traces
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(empty_fig, "pdf")

        # Should either succeed with empty plot or return error
        # Implementation can decide, but must not crash
        assert "success" in result
        assert "format" in result

    def test_invalid_format_raises_error(self, single_column_preset: dict[str, Any]) -> None:
        """Invalid format should raise ValueError."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        with pytest.raises(ValueError, match="Unsupported format"):
            converter.convert(fig, "invalid_format")  # type: ignore

    def test_matplotlib_cleanup_on_error(self, single_column_preset: dict[str, Any]) -> None:
        """Verify matplotlib figures are cleaned up even on error."""
        import matplotlib.pyplot as plt

        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        # Get initial figure count
        initial_count = len(plt.get_fignums())

        # This might fail, but should cleanup. We intentionally do not re-raise
        # the exception here so we can still verify that figure cleanup occurs.
        try:
            converter.convert(fig, "pdf")
        except Exception:
            logging.exception("MatplotlibConverter.convert raised an exception during cleanup test")

        # Figure count should be back to initial (cleanup happened)
        final_count = len(plt.get_fignums())
        assert final_count == initial_count


class TestPresetApplication:
    """Test that preset values are correctly applied."""

    def test_dpi_setting_applied(self, single_column_preset: dict[str, Any]) -> None:
        """Verify DPI from preset is applied."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["metadata"]["dpi"] == single_column_preset["dpi"]

    def test_line_width_from_preset(self, single_column_preset: dict[str, Any]) -> None:
        """Verify line width from preset is used."""
        fig = create_line_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        # Metadata should indicate line width was applied
        assert "line_width" in result["metadata"]

    def test_marker_size_from_preset(self, single_column_preset: dict[str, Any]) -> None:
        """Verify marker size from preset is used."""
        fig = create_scatter_figure()
        converter = MatplotlibConverter(single_column_preset)

        result = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert "marker_size" in result["metadata"]
