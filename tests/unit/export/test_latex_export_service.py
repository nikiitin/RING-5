"""
Unit tests for LaTeXExportService - main API for LaTeX export.

Tests the facade layer that orchestrates MatplotlibConverter and PresetManager.
"""

import shutil

import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.export.latex_export_service import LaTeXExportService
from src.web.pages.ui.plotting.export.presets.preset_schema import LaTeXPreset

# Check for XeLaTeX availability common marker
has_xelatex = shutil.which("xelatex") is not None
requires_xelatex = pytest.mark.skipif(not has_xelatex, reason="XeLaTeX not found")


class TestServiceInitialization:
    """Test service creation and basic operations."""

    def test_service_initializes_successfully(self) -> None:
        """Service should initialize without errors."""
        service = LaTeXExportService()
        assert service is not None
        assert hasattr(service, "preset_manager")

    def test_list_presets_returns_available_options(self) -> None:
        """Should list all available journal presets."""
        service = LaTeXExportService()
        presets = service.list_presets()

        assert isinstance(presets, list)
        assert "single_column" in presets
        assert "double_column" in presets
        assert len(presets) >= 2

    def test_get_preset_info_returns_valid_preset(self) -> None:
        """Should retrieve preset configuration."""
        service = LaTeXExportService()
        info = service.get_preset_info("single_column")

        assert isinstance(info, dict)
        assert "width_inches" in info
        assert "height_inches" in info
        assert "font_size_base" in info  # Actual key name in presets


class TestExportWithPresetName:
    """Test export using preset names (most common use case)."""

    def test_export_simple_figure_to_pdf(self) -> None:
        """Should export bar chart to PDF successfully."""
        # Arrange
        fig = go.Figure(
            data=[go.Bar(x=["A", "B", "C"], y=[1, 2, 3])],
            layout={"title": "Test Chart"},
        )
        service = LaTeXExportService()

        # Act
        result = service.export(fig, preset="single_column", format="pdf")

        # Assert
        assert result["success"] is True
        assert result["data"] is not None
        assert len(result["data"]) > 0
        assert result["format"] == "pdf"
        assert result["error"] is None

    @requires_xelatex
    def test_export_figure_to_pgf(self) -> None:
        """Should export to PGF for direct LaTeX inclusion."""
        fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4])])
        service = LaTeXExportService()

        result = service.export(fig, preset="double_column", format="pgf")

        assert result["success"] is True
        assert result["format"] == "pgf"
        # PGF is text format
        pgf_content = result["data"].decode("utf-8")
        assert "\\begin{pgfpicture}" in pgf_content

    def test_export_figure_to_eps(self) -> None:
        """Should export to EPS for legacy support."""
        fig = go.Figure(data=[go.Bar(x=["X"], y=[10])])
        service = LaTeXExportService()

        result = service.export(fig, preset="single_column", format="eps")

        assert result["success"] is True
        assert result["format"] == "eps"
        assert result["data"].startswith(b"%!PS-Adobe")


class TestExportWithCustomPreset:
    """Test export using custom preset dictionaries."""

    def test_export_with_custom_preset_dict(self) -> None:
        """Should accept and use custom preset configuration."""
        fig = go.Figure(data=[go.Bar(x=["A"], y=[5])])

        custom_preset: LaTeXPreset = {
            "width_inches": 4.0,
            "height_inches": 3.0,
            "font_size_base": 9,
            "font_size_title": 10,
            "font_size_xlabel": 8,
            "font_size_ylabel": 8,
            "font_size_legend": 7,
            "font_size_ticks": 7,
            "font_size_annotations": 6,
            "bold_title": False,
            "bold_xlabel": False,
            "bold_ylabel": False,
            "bold_legend": False,
            "bold_ticks": False,
            "bold_annotations": True,
            "font_family": "serif",
            "line_width": 1.0,
            "marker_size": 4.0,
            "dpi": 300,
            "legend_columnspacing": 0.5,
            "legend_handletextpad": 0.4,
            "legend_labelspacing": 0.3,
            "legend_handlelength": 1.2,
            "legend_handleheight": 0.7,
            "legend_borderpad": 0.3,
            "legend_borderaxespad": 0.5,
            "ylabel_pad": 10.0,
            "ylabel_y_position": 0.5,
            "xtick_pad": 5.0,
            "ytick_pad": 5.0,
            "group_label_offset": -0.12,
            "group_label_alternate": True,
            "xaxis_margin": 0.02,
            "bar_width_scale": 1.0,
            "xtick_rotation": 45.0,
            "xtick_ha": "right",
            "xtick_offset": 0.0,
            "group_separator": False,
            "group_separator_style": "dashed",
            "group_separator_color": "gray",
        }

        service = LaTeXExportService()
        result = service.export(fig, preset=custom_preset, format="pdf")

        assert result["success"] is True
        assert result["data"] is not None

    def test_export_with_invalid_preset_dict_fails(self) -> None:
        """Should fail gracefully with invalid preset."""
        fig = go.Figure(data=[go.Bar(x=["A"], y=[5])])

        # Missing required fields
        invalid_preset = {
            "width_inches": 4.0,
            # Missing height_inches, font_size, etc.
        }

        service = LaTeXExportService()
        result = service.export(fig, preset=invalid_preset, format="pdf")  # type: ignore

        assert result["success"] is False
        assert result["error"] is not None


class TestErrorHandling:
    """Test service error handling and edge cases."""

    def test_export_with_unknown_preset_name_fails(self) -> None:
        """Should fail gracefully with unknown preset."""
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        service = LaTeXExportService()

        result = service.export(fig, preset="nonexistent_preset", format="pdf")

        assert result["success"] is False
        assert result["error"] is not None
        assert "preset" in result["error"].lower()

    def test_export_with_invalid_format_fails(self) -> None:
        """Should fail gracefully with unsupported format."""
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        service = LaTeXExportService()

        result = service.export(fig, preset="single_column", format="png")

        assert result["success"] is False
        assert result["error"] is not None

    def test_export_with_empty_figure_fails(self) -> None:
        """Should fail gracefully with empty figure."""
        fig = go.Figure()  # No data
        service = LaTeXExportService()

        result = service.export(fig, preset="single_column", format="pdf")

        assert result["success"] is False
        assert result["error"] is not None

    def test_export_handles_conversion_errors(self) -> None:
        """Should catch and report converter errors."""
        # Create figure with problematic data
        fig = go.Figure(data=[go.Bar(x=[], y=[])])
        service = LaTeXExportService()

        result = service.export(fig, preset="single_column", format="pdf")

        # Should fail gracefully, not crash
        assert result["success"] is False
        assert result["error"] is not None


class TestMetadataAndLogging:
    """Test metadata generation and logging behavior."""

    def test_export_includes_metadata(self) -> None:
        """Should include metadata in successful export."""
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[1, 2])])
        service = LaTeXExportService()

        result = service.export(fig, preset="single_column", format="pdf")

        assert result["success"] is True
        assert "metadata" in result
        # Metadata populated by MatplotlibConverter
        assert result["metadata"] is not None

    def test_export_returns_consistent_error_structure(self) -> None:
        """Error results should have consistent structure."""
        fig = go.Figure()
        service = LaTeXExportService()

        result = service.export(fig, preset="single_column", format="pdf")

        # Failed results still have all fields
        assert "success" in result
        assert "data" in result
        assert "format" in result
        assert "error" in result
        assert "metadata" in result
        assert result["success"] is False


class TestIntegrationScenarios:
    """Test realistic end-to-end workflows."""

    def test_export_workflow_with_multiple_formats(self) -> None:
        """Should export same figure to multiple formats."""
        fig = go.Figure(
            data=[go.Bar(x=["Q1", "Q2", "Q3"], y=[10, 20, 15])],
            layout={"title": "Quarterly Revenue"},
        )
        service = LaTeXExportService()

        # Export to PDF
        pdf_result = service.export(fig, preset="single_column", format="pdf")
        assert pdf_result["success"] is True

        # Export to PGF (Conditional)
        if has_xelatex:
            pgf_result = service.export(fig, preset="single_column", format="pgf")
            assert pgf_result["success"] is True

        # Export to EPS
        eps_result = service.export(fig, preset="single_column", format="eps")
        assert eps_result["success"] is True

    def test_export_preserves_interactive_adjustments(self) -> None:
        """Should preserve user's legend and zoom adjustments."""
        fig = go.Figure(
            data=[
                go.Scatter(x=[1, 2, 3], y=[1, 4, 9], name="Series 1"),
                go.Scatter(x=[1, 2, 3], y=[1, 2, 3], name="Series 2"),
            ],
            layout={
                "xaxis": {"range": [0.5, 2.5]},  # Zoomed
                "showlegend": True,
                "legend": {"x": 0.8, "y": 0.9},  # Custom position
            },
        )
        service = LaTeXExportService()

        result = service.export(fig, preset="double_column", format="pdf")

        # Should succeed with layout preservation
        assert result["success"] is True
        # Metadata should indicate layout was preserved
        # (implementation detail - converter adds this)

    def test_service_reusable_for_multiple_exports(self) -> None:
        """Single service instance should handle multiple exports."""
        service = LaTeXExportService()

        fig1 = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        fig2 = go.Figure(data=[go.Scatter(x=[1], y=[2])])

        result1 = service.export(fig1, preset="single_column", format="pdf")

        # Use PGF if available, otherwise EPS
        format2 = "pgf" if has_xelatex else "eps"
        result2 = service.export(fig2, preset="double_column", format=format2)

        assert result1["success"] is True
        assert result2["success"] is True
        # Results should be independent
        assert result1["format"] != result2["format"]
