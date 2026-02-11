"""Tests for PresetManager and PresetSchema — target 0% → 80%+."""

from typing import Any, Dict

import pytest

from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager


class TestPresetManager:
    """Tests for PresetManager."""

    def setup_method(self) -> None:
        """Reset cache and initialized flag to avoid cross-test contamination."""
        PresetManager._cache = {}
        PresetManager._presets_data = {}
        PresetManager._initialized = False

    def test_list_presets_returns_list(self) -> None:
        names = PresetManager.list_presets()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_load_preset_returns_typed_dict(self) -> None:
        names = PresetManager.list_presets()
        preset = PresetManager.load_preset(names[0])
        assert "width_inches" in preset
        assert "height_inches" in preset
        assert "font_family" in preset

    def test_load_preset_caches(self) -> None:
        names = PresetManager.list_presets()
        name = names[0]
        p1 = PresetManager.load_preset(name)
        p2 = PresetManager.load_preset(name)
        assert p1 is p2  # same object from cache

    def test_load_unknown_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown preset"):
            PresetManager.load_preset("nonexistent_preset_xyz")

    def test_get_preset_info(self) -> None:
        names = PresetManager.list_presets()
        info = PresetManager.get_preset_info(names[0])
        assert "description" in info
        assert "typical_use" in info

    def test_get_preset_info_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown preset"):
            PresetManager.get_preset_info("nonexistent")

    def test_validate_preset_missing_field(self) -> None:
        incomplete: Dict[str, Any] = {"width_inches": 3.5}
        with pytest.raises(ValueError, match="Missing required field"):
            PresetManager.validate_preset(incomplete)

    def test_validate_preset_negative_width(self) -> None:
        preset = self._make_valid_preset()
        preset["width_inches"] = -1.0
        with pytest.raises(ValueError, match="width_inches must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_height(self) -> None:
        preset = self._make_valid_preset()
        preset["height_inches"] = 0
        with pytest.raises(ValueError, match="height_inches must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_font_size_base(self) -> None:
        preset = self._make_valid_preset()
        preset["font_size_base"] = -1
        with pytest.raises(ValueError, match="font_size_base must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_font_size_title(self) -> None:
        preset = self._make_valid_preset()
        preset["font_size_title"] = 0
        with pytest.raises(ValueError, match="font_size_title must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_font_size_xlabel(self) -> None:
        preset = self._make_valid_preset()
        preset["font_size_xlabel"] = -5
        with pytest.raises(ValueError, match="font_size_xlabel must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_font_size_ylabel(self) -> None:
        preset = self._make_valid_preset()
        preset["font_size_ylabel"] = 0
        with pytest.raises(ValueError, match="font_size_ylabel must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_font_size_legend(self) -> None:
        preset = self._make_valid_preset()
        preset["font_size_legend"] = -1
        with pytest.raises(ValueError, match="font_size_legend must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_font_size_ticks(self) -> None:
        preset = self._make_valid_preset()
        preset["font_size_ticks"] = -1
        with pytest.raises(ValueError, match="font_size_ticks must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_line_width(self) -> None:
        preset = self._make_valid_preset()
        preset["line_width"] = 0
        with pytest.raises(ValueError, match="line_width must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_marker_size(self) -> None:
        preset = self._make_valid_preset()
        preset["marker_size"] = -1
        with pytest.raises(ValueError, match="marker_size must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_dpi(self) -> None:
        preset = self._make_valid_preset()
        preset["dpi"] = 0
        with pytest.raises(ValueError, match="dpi must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_valid_preset_ok(self) -> None:
        preset = self._make_valid_preset()
        # Should not raise
        PresetManager.validate_preset(preset)

    def _make_valid_preset(self) -> Dict[str, Any]:
        """Create a minimal valid preset for testing validation."""
        return {
            "width_inches": 3.5,
            "height_inches": 2.625,
            "font_family": "serif",
            "font_size_base": 9,
            "font_size_title": 10,
            "font_size_xlabel": 9,
            "font_size_ylabel": 9,
            "font_size_legend": 8,
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
            "legend_columnspacing": 2.0,
            "legend_handletextpad": 0.8,
            "legend_labelspacing": 0.5,
            "legend_handlelength": 2.0,
            "legend_handleheight": 0.7,
            "legend_borderpad": 0.4,
            "legend_borderaxespad": 0.5,
        }
