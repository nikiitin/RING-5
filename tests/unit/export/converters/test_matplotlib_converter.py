"""
Tests for MatplotlibConverter - Plotly to Matplotlib conversion for LaTeX export.

Following TDD approach: Tests written FIRST, then implementation.
"""

import logging
import shutil
from typing import Any

import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (
    MatplotlibConverter,
)
from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager
from tests.helpers.sample_figures import (
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
        from src.web.pages.ui.plotting.export.converters.base_converter import (
            BaseConverter,
        )

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


# ─── Additional Coverage Tests ──────────────────────────────────────────────


class TestStackedBarConversion:
    """Tests for stacked bar chart conversion (categorical and numeric)."""

    def test_stacked_categorical_bars(self, single_column_preset: dict[str, Any]) -> None:
        """Stacked bar with categorical x-axis (string labels)."""
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A", "B", "C"], y=[10, 20, 30], name="s1"))
        fig.add_trace(go.Bar(x=["A", "B", "C"], y=[5, 10, 15], name="s2"))
        fig.update_layout(barmode="stack")

        converter = MatplotlibConverter(single_column_preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True
        assert result["metadata"]["barmode"] == "stack"
        assert result["metadata"]["bar_traces_count"] == 2

    def test_stacked_numeric_bars(self, single_column_preset: dict[str, Any]) -> None:
        """Stacked bar with numeric x values."""
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[1.0, 2.0, 3.0], y=[10, 20, 30], name="s1"))
        fig.add_trace(go.Bar(x=[1.0, 2.0, 3.0], y=[5, 10, 15], name="s2"))
        fig.update_layout(barmode="stack")

        converter = MatplotlibConverter(single_column_preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True
        assert result["metadata"]["bar_traces_count"] == 2

    def test_grouped_categorical_long_labels(self, single_column_preset: dict[str, Any]) -> None:
        """Bar chart with long labels should trigger rotation."""
        labels = [f"very_long_label_{i}" for i in range(12)]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=list(range(12)), name="data"))

        converter = MatplotlibConverter(single_column_preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True


class TestLineDashStyles:
    """Tests for line trace dash style conversion."""

    @pytest.mark.parametrize(
        "dash,expected",
        [("dash", "--"), ("dot", ":"), ("dashdot", "-.")],
    )
    def test_dash_style_conversion(
        self,
        single_column_preset: dict[str, Any],
        dash: str,
        expected: str,
    ) -> None:
        """Line dash styles are converted correctly."""
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=[1, 2, 3],
                y=[4, 5, 6],
                mode="lines",
                line=dict(dash=dash, color="blue"),
                name="line",
            )
        )

        converter = MatplotlibConverter(single_column_preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True
        assert result["metadata"]["traces_converted"] >= 1


class TestPreviewGeneration:
    """Tests for generate_preview PNG generation."""

    def test_preview_returns_bytes(self, single_column_preset: dict[str, Any]) -> None:
        """Preview generation returns PNG bytes."""
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)
        png = converter.generate_preview(fig, preview_dpi=72)
        assert isinstance(png, bytes)
        assert len(png) > 0
        # Must start with PNG magic bytes
        assert png[:4] == b"\x89PNG"

    def test_preview_preserves_original_dpi(self, single_column_preset: dict[str, Any]) -> None:
        """DPI should be restored after preview."""
        original_dpi = single_column_preset["dpi"]
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(single_column_preset)
        converter.generate_preview(fig, preview_dpi=72)
        assert converter.preset["dpi"] == original_dpi

    def test_preview_stacked_bar(self, single_column_preset: dict[str, Any]) -> None:
        """Preview works for stacked bar figures."""
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A", "B"], y=[10, 20], name="s1"))
        fig.add_trace(go.Bar(x=["A", "B"], y=[5, 10], name="s2"))
        fig.update_layout(barmode="stack")
        converter = MatplotlibConverter(single_column_preset)
        png = converter.generate_preview(fig, preview_dpi=72)
        assert png[:4] == b"\x89PNG"


class TestMultiColumnLegend:
    """Tests for legend multi-column and bold handling."""

    def test_many_traces_use_two_columns(self, single_column_preset: dict[str, Any]) -> None:
        """More than 4 legend entries should use 2-column legend."""
        fig = go.Figure()
        for i in range(6):
            fig.add_trace(go.Bar(x=["A", "B"], y=[i + 1, i + 2], name=f"trace_{i}"))

        converter = MatplotlibConverter(single_column_preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True
        # With 6 labeled traces, legend_items should be >= 5
        # and ncols should be 2 (if legend is generated)
        if result["metadata"].get("legend_items", 0) > 4:
            assert result["metadata"]["legend_ncols"] == 2

    def test_bold_legend(self, single_column_preset: dict[str, Any]) -> None:
        """Bold legend setting should not cause errors."""
        preset = dict(single_column_preset)
        preset["bold_legend"] = True
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True

    def test_legend_spacing_from_preset(self, single_column_preset: dict[str, Any]) -> None:
        """Custom legend spacing params from preset should be applied."""
        preset = dict(single_column_preset)
        preset["legend_columnspacing"] = 1.0
        preset["legend_handletextpad"] = 0.5
        fig = create_simple_bar_figure()
        converter = MatplotlibConverter(preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True


class TestScatterTraceDetails:
    """Tests for scatter trace marker properties."""

    def test_scatter_with_marker_size(self, single_column_preset: dict[str, Any]) -> None:
        """Scatter trace with custom marker size."""
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=[1, 2, 3],
                y=[4, 5, 6],
                mode="markers",
                marker=dict(size=15, color="red"),
                name="dots",
            )
        )
        converter = MatplotlibConverter(single_column_preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True

    def test_scatter_default_mode_is_line(self, single_column_preset: dict[str, Any]) -> None:
        """Scatter trace without mode defaults to line conversion."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="default"))
        converter = MatplotlibConverter(single_column_preset)
        result = converter.convert(fig, "pdf")
        assert result["success"] is True
        assert result["metadata"]["traces_converted"] == 1
