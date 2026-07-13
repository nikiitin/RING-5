"""Tests for DataLabelConfig — construction, serialization, immutability."""

from __future__ import annotations

import pytest

from src.core.models.visualization.data_label_config import DataLabelConfig


class TestDataLabelSpecDefaults:
    """Test that default construction produces safe no-op values."""

    def test_default_values(self) -> None:
        """All defaults should produce no visible labels."""
        spec = DataLabelConfig()

        assert spec.enabled is False
        assert spec.color_mode == "auto"
        assert spec.custom_color == "#000000"
        assert spec.font_size == 10
        assert spec.rotation == 0
        assert spec.position == "auto"
        assert spec.anchor == "auto"
        assert spec.format_string == ".2f"
        assert spec.display_logic == "all"
        assert spec.threshold == 0.0
        assert spec.size_constraint == "none"
        assert spec.auto_contrast is True


class TestDataLabelSpecCustom:
    """Test custom construction with all fields."""

    def test_custom_values(self) -> None:
        """Constructor accepts all fields."""
        spec = DataLabelConfig(
            enabled=True,
            color_mode="contrast",
            custom_color="#FF0000",
            font_size=14,
            rotation=45,
            position="outside",
            anchor="top",
            format_string=".1%",
            display_logic="above_threshold",
            threshold=1.5,
            size_constraint="inside",
            auto_contrast=False,
        )

        assert spec.enabled is True
        assert spec.color_mode == "contrast"
        assert spec.custom_color == "#FF0000"
        assert spec.font_size == 14
        assert spec.rotation == 45
        assert spec.position == "outside"
        assert spec.anchor == "top"
        assert spec.format_string == ".1%"
        assert spec.display_logic == "above_threshold"
        assert spec.threshold == 1.5
        assert spec.size_constraint == "inside"
        assert spec.auto_contrast is False


class TestDataLabelSpecFrozen:
    """Test immutability."""

    def test_frozen(self) -> None:
        """Spec must be immutable."""
        spec = DataLabelConfig()
        with pytest.raises(AttributeError):
            spec.enabled = True  # type: ignore[misc]

    def test_frozen_custom_color(self) -> None:
        """Cannot mutate custom_color."""
        spec = DataLabelConfig(custom_color="#00FF00")
        with pytest.raises(AttributeError):
            spec.custom_color = "#AABBCC"  # type: ignore[misc]


class TestDataLabelSpecSerialization:
    """Test to_dict/from_dict round-trip."""

    def test_default_round_trip(self) -> None:
        """Default spec round-trips through dict."""
        original = DataLabelConfig()
        restored = DataLabelConfig.from_dict(original.to_dict())
        assert restored == original

    def test_custom_round_trip(self) -> None:
        """Custom spec preserves all values through round-trip."""
        original = DataLabelConfig(
            enabled=True,
            color_mode="custom",
            custom_color="#ABCDEF",
            font_size=8,
            rotation=-30,
            position="inside",
            anchor="bottom",
            format_string=".3f",
            display_logic="below_threshold",
            threshold=42.5,
            size_constraint="inside",
            auto_contrast=False,
        )
        restored = DataLabelConfig.from_dict(original.to_dict())
        assert restored == original

    def test_to_dict_produces_plain_dict(self) -> None:
        """to_dict() should produce plain Python types."""
        spec = DataLabelConfig(enabled=True, font_size=12)
        d = spec.to_dict()

        assert isinstance(d, dict)
        assert d["enabled"] is True
        assert d["font_size"] == 12
        assert isinstance(d["threshold"], float)

    def test_from_dict_ignores_unknown_keys(self) -> None:
        """Unknown keys in input dict should not raise."""
        spec = DataLabelConfig.from_dict(
            {
                "enabled": True,
                "unknown_key": "should_be_ignored",
            }
        )
        assert spec.enabled is True
        assert spec.font_size == 10  # default

    def test_from_dict_empty_dict(self) -> None:
        """Empty dict produces default spec."""
        spec = DataLabelConfig.from_dict({})
        assert spec == DataLabelConfig()


class TestDataLabelSpecOnFigureSpec:
    """Test DataLabelConfig integration with FigureConfig."""

    def test_figure_spec_default_data_labels_is_none(self) -> None:
        """FigureConfig default has no data labels."""
        from src.core.models.visualization.figure_config import FigureConfig

        spec = FigureConfig()
        assert spec.data_labels is None

    def test_figure_spec_with_data_labels(self) -> None:
        """FigureConfig accepts DataLabelConfig."""
        from src.core.models.visualization.figure_config import FigureConfig

        dl = DataLabelConfig(enabled=True, font_size=12)
        spec = FigureConfig(data_labels=dl)

        assert spec.data_labels is not None
        assert spec.data_labels.enabled is True
        assert spec.data_labels.font_size == 12

    def test_figure_spec_round_trip_with_data_labels(self) -> None:
        """FigureConfig with data_labels round-trips through dict."""
        from src.core.models.visualization.figure_config import FigureConfig

        dl = DataLabelConfig(
            enabled=True,
            color_mode="contrast",
            format_string=".1f",
        )
        spec = FigureConfig(data_labels=dl, title="Test")
        restored = FigureConfig.from_dict(spec.to_dict())

        assert restored.data_labels is not None
        assert restored.data_labels.enabled is True
        assert restored.data_labels.color_mode == "contrast"
        assert restored.data_labels.format_string == ".1f"

    def test_figure_spec_round_trip_without_data_labels(self) -> None:
        """FigureConfig without data_labels round-trips as None."""
        from src.core.models.visualization.figure_config import FigureConfig

        spec = FigureConfig(title="No Labels")
        restored = FigureConfig.from_dict(spec.to_dict())

        assert restored.data_labels is None
