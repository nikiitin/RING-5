"""
Unit tests for LaTeX export preset schema definitions.

Tests TypedDict structures for type safety and documentation.
"""

from typing import get_type_hints

from src.plotting.export.presets.preset_schema import (
    ExportResult,
    LaTeXPreset,
)


class TestLaTeXPreset:
    """Test LaTeXPreset TypedDict structure."""

    def test_latex_preset_has_required_fields(self) -> None:
        """Verify LaTeXPreset has all required fields."""
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

        assert preset["width_inches"] == 3.5
        assert preset["height_inches"] == 2.625
        assert preset["font_family"] == "serif"
        assert preset["font_size_base"] == 9
        assert preset["dpi"] == 300

    def test_latex_preset_type_annotations(self) -> None:
        """Verify LaTeXPreset has correct type annotations."""
        hints = get_type_hints(LaTeXPreset)

        assert hints["width_inches"] == float
        assert hints["height_inches"] == float
        assert hints["font_family"] == str
        assert hints["font_size_base"] == int
        assert hints["dpi"] == int

    def test_latex_preset_accepts_valid_values(self) -> None:
        """Test LaTeXPreset accepts valid preset configurations."""
        single_column: LaTeXPreset = {
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

        double_column: LaTeXPreset = {
            "width_inches": 7.0,
            "height_inches": 5.25,
            "font_family": "serif",
            "font_size_base": 10,
            "font_size_labels": 9,
            "font_size_title": 11,
            "font_size_ticks": 8,
            "line_width": 1.2,
            "marker_size": 5,
            "dpi": 300,
        }

        assert single_column["width_inches"] < double_column["width_inches"]
        assert single_column["font_size_base"] < double_column["font_size_base"]


class TestExportResult:
    """Test ExportResult TypedDict structure."""

    def test_export_result_success_structure(self) -> None:
        """Verify ExportResult structure for successful export."""
        result: ExportResult = {
            "success": True,
            "data": b"mock PDF data",
            "format": "pdf",
            "error": None,
            "metadata": {"width": 3.5, "height": 2.625},
        }

        assert result["success"] is True
        assert result["data"] == b"mock PDF data"
        assert result["format"] == "pdf"
        assert result["error"] is None
        assert "width" in result["metadata"]

    def test_export_result_failure_structure(self) -> None:
        """Verify ExportResult structure for failed export."""
        result: ExportResult = {
            "success": False,
            "data": None,
            "format": "pdf",
            "error": "Conversion failed: LaTeX not installed",
            "metadata": {},
        }

        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] is not None
        assert "LaTeX not installed" in result["error"]

    def test_export_result_type_annotations(self) -> None:
        """Verify ExportResult has correct type annotations."""
        hints = get_type_hints(ExportResult)

        assert hints["success"] == bool
        assert hints["format"] == str
        # Optional types are represented as Union in get_type_hints

    def test_export_result_metadata_can_store_layout_info(self) -> None:
        """Verify metadata can store preserved layout information."""
        result: ExportResult = {
            "success": True,
            "data": b"data",
            "format": "pdf",
            "error": None,
            "metadata": {
                "layout_preserved": {
                    "legend_x": 0.05,
                    "legend_y": 0.95,
                    "xaxis_range": [0, 10],
                },
                "preset_applied": "single_column",
            },
        }

        assert "layout_preserved" in result["metadata"]
        assert result["metadata"]["layout_preserved"]["legend_x"] == 0.05
