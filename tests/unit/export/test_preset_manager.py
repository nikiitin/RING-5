"""
Unit tests for preset manager.

Tests loading, validation, and management of LaTeX export presets.
"""

import pytest

from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager
from src.web.pages.ui.plotting.export.presets.preset_schema import LaTeXPreset


def create_valid_preset(**overrides: float | str | int | bool) -> LaTeXPreset:
    """Create a valid test preset with optional overrides."""
    default_preset: LaTeXPreset = {
        "width_inches": 3.5,
        "height_inches": 1.96875,
        "font_family": "serif",
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
        "line_width": 1.0,
        "marker_size": 4,
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
    return {**default_preset, **overrides}  # type: ignore[return-value]


class TestPresetManager:
    """Test PresetManager functionality."""

    def test_load_single_column_preset(self) -> None:
        """Verify single column preset loads correctly."""
        preset = PresetManager.load_preset("single_column")

        assert preset["width_inches"] == 3.5
        assert preset["height_inches"] == 1.96875  # Updated 9:16 aspect ratio
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
        valid_preset = create_valid_preset()

        # Should not raise
        PresetManager.validate_preset(valid_preset)

    def test_validate_preset_with_negative_width_raises_error(self) -> None:
        """Verify validation catches negative width."""
        invalid_preset = create_valid_preset(width_inches=-1.0)

        with pytest.raises(ValueError, match="width_inches must be positive"):
            PresetManager.validate_preset(invalid_preset)

    def test_validate_preset_with_zero_dpi_raises_error(self) -> None:
        """Verify validation catches invalid DPI."""
        invalid_preset = create_valid_preset(dpi=0)

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
        invalid_preset = create_valid_preset(font_size_base=-5)

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
