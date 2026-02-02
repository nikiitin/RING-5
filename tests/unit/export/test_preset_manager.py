"""
Unit tests for preset manager.

Tests loading, validation, and management of LaTeX export presets.
"""

import pytest

from src.plotting.export.presets.preset_manager import PresetManager
from src.plotting.export.presets.preset_schema import LaTeXPreset


class TestPresetManager:
    """Test PresetManager functionality."""

    def test_load_single_column_preset(self) -> None:
        """Verify single column preset loads correctly."""
        preset = PresetManager.load_preset("single_column")

        assert preset["width_inches"] == 3.5
        assert preset["height_inches"] == 2.625
        assert preset["font_family"] == "serif"
        assert preset["dpi"] == 300

    def test_load_double_column_preset(self) -> None:
        """Verify double column preset loads correctly."""
        preset = PresetManager.load_preset("double_column")

        assert preset["width_inches"] == 7.0
        assert preset["height_inches"] == 5.25
        assert preset["font_size_base"] == 10

    def test_load_nature_preset(self) -> None:
        """Verify Nature journal preset loads correctly."""
        preset = PresetManager.load_preset("nature")

        assert preset["width_inches"] == 3.5
        assert preset["height_inches"] == 3.5  # Square for Nature
        assert preset["font_family"] == "Arial"  # Nature requires Arial
        assert preset["dpi"] == 600  # Nature requires high DPI

    def test_load_ieee_preset(self) -> None:
        """Verify IEEE conference preset loads correctly."""
        preset = PresetManager.load_preset("ieee_single")

        assert preset["width_inches"] == 3.5
        assert preset["dpi"] == 300

    def test_invalid_preset_raises_error(self) -> None:
        """Verify unknown preset raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            PresetManager.load_preset("nonexistent_preset")

    def test_list_available_presets(self) -> None:
        """Verify can list all available presets."""
        presets = PresetManager.list_presets()

        assert "single_column" in presets
        assert "double_column" in presets
        assert "nature" in presets
        assert "ieee_single" in presets
        assert len(presets) >= 4

    def test_validate_preset_with_valid_data(self) -> None:
        """Verify validation passes for valid preset."""
        valid_preset: LaTeXPreset = {
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

        # Should not raise
        PresetManager.validate_preset(valid_preset)

    def test_validate_preset_with_negative_width_raises_error(self) -> None:
        """Verify validation catches negative width."""
        invalid_preset = {
            "width_inches": -1.0,  # Invalid: negative
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

        with pytest.raises(ValueError, match="width_inches must be positive"):
            PresetManager.validate_preset(invalid_preset)

    def test_validate_preset_with_zero_dpi_raises_error(self) -> None:
        """Verify validation catches invalid DPI."""
        invalid_preset = {
            "width_inches": 3.5,
            "height_inches": 2.625,
            "font_family": "serif",
            "font_size_base": 9,
            "font_size_labels": 8,
            "font_size_title": 10,
            "font_size_ticks": 7,
            "line_width": 1.0,
            "marker_size": 4,
            "dpi": 0,  # Invalid: zero
        }

        with pytest.raises(ValueError, match="dpi must be positive"):
            PresetManager.validate_preset(invalid_preset)

    def test_validate_preset_with_missing_field_raises_error(self) -> None:
        """Verify validation catches missing required fields."""
        incomplete_preset = {
            "width_inches": 3.5,
            # Missing height_inches and other fields
        }

        with pytest.raises(ValueError, match="Missing required field"):
            PresetManager.validate_preset(incomplete_preset)

    def test_validate_preset_with_negative_font_size_raises_error(self) -> None:
        """Verify validation catches negative font sizes."""
        invalid_preset = {
            "width_inches": 3.5,
            "height_inches": 2.625,
            "font_family": "serif",
            "font_size_base": -5,  # Invalid: negative
            "font_size_labels": 8,
            "font_size_title": 10,
            "font_size_ticks": 7,
            "line_width": 1.0,
            "marker_size": 4,
            "dpi": 300,
        }

        with pytest.raises(ValueError, match="font_size_base must be positive"):
            PresetManager.validate_preset(invalid_preset)

    def test_preset_manager_caches_loaded_presets(self) -> None:
        """Verify PresetManager caches loaded presets for performance."""
        manager = PresetManager()

        # Load twice
        preset1 = manager.load_preset("single_column")
        preset2 = manager.load_preset("single_column")

        # Should be same object (cached)
        assert preset1 is preset2

    def test_get_preset_info(self) -> None:
        """Verify can get preset metadata without loading full preset."""
        info = PresetManager.get_preset_info("single_column")

        assert "description" in info
        assert "typical_use" in info
        # Check for "single" and "column" separately (handles hyphenation)
        desc_lower = info["description"].lower()
        assert "single" in desc_lower
        assert "column" in desc_lower
