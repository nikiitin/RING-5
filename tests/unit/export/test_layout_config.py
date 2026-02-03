"""
Unit tests for layout configuration dataclasses.

Tests FontStyleConfig, PositioningConfig, and SeparatorConfig to ensure
proper defaults, type safety, and construction from presets.
"""

from src.plotting.export.converters.layout_config import (
    FontStyleConfig,
    PositioningConfig,
    SeparatorConfig,
)


class TestFontStyleConfig:
    """Test FontStyleConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify default font sizes and bold flags."""
        config = FontStyleConfig()

        assert config.font_size_title == 10
        assert config.font_size_xlabel == 9
        assert config.font_size_ylabel == 9
        assert config.font_size_ticks == 7
        assert config.font_size_annotations == 6
        assert config.bold_title is False
        assert config.bold_xlabel is False
        assert config.bold_ylabel is False
        assert config.bold_ticks is False
        assert config.bold_annotations is True  # Bold by default

    def test_custom_values(self) -> None:
        """Verify can set custom font sizes and bold flags."""
        config = FontStyleConfig(
            font_size_title=12,
            font_size_xlabel=11,
            font_size_ylabel=11,
            font_size_ticks=9,
            font_size_annotations=8,
            bold_title=True,
            bold_xlabel=True,
            bold_ylabel=True,
            bold_ticks=True,
            bold_annotations=False,
        )

        assert config.font_size_title == 12
        assert config.font_size_xlabel == 11
        assert config.font_size_ylabel == 11
        assert config.font_size_ticks == 9
        assert config.font_size_annotations == 8
        assert config.bold_title is True
        assert config.bold_xlabel is True
        assert config.bold_ylabel is True
        assert config.bold_ticks is True
        assert config.bold_annotations is False

    def test_partial_initialization(self) -> None:
        """Verify can set some values while keeping others default."""
        config = FontStyleConfig(
            font_size_title=14,
            bold_title=True,
        )

        assert config.font_size_title == 14
        assert config.bold_title is True
        assert config.font_size_xlabel == 9  # Still default
        assert config.bold_xlabel is False  # Still default


class TestPositioningConfig:
    """Test PositioningConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify default positioning parameters."""
        config = PositioningConfig()

        assert config.ylabel_pad == 10.0
        assert config.ylabel_y_position == 0.5
        assert config.xtick_pad == 5.0
        assert config.ytick_pad == 5.0
        assert config.xtick_rotation == 45.0
        assert config.xtick_ha == "right"
        assert config.xtick_offset == 0.0
        assert config.xaxis_margin == 0.02
        assert config.group_label_offset == -0.12
        assert config.group_label_alternate is True

    def test_custom_values(self) -> None:
        """Verify can set custom positioning parameters."""
        config = PositioningConfig(
            ylabel_pad=20.0,
            ylabel_y_position=1.0,
            xtick_pad=10.0,
            ytick_pad=10.0,
            xtick_rotation=90.0,
            xtick_ha="center",
            xtick_offset=5.0,
            xaxis_margin=0.05,
            group_label_offset=-0.2,
            group_label_alternate=False,
        )

        assert config.ylabel_pad == 20.0
        assert config.ylabel_y_position == 1.0
        assert config.xtick_pad == 10.0
        assert config.ytick_pad == 10.0
        assert config.xtick_rotation == 90.0
        assert config.xtick_ha == "center"
        assert config.xtick_offset == 5.0
        assert config.xaxis_margin == 0.05
        assert config.group_label_offset == -0.2
        assert config.group_label_alternate is False

    def test_ylabel_position_range(self) -> None:
        """Verify ylabel_y_position accepts 0-1 range."""
        config_bottom = PositioningConfig(ylabel_y_position=0.0)
        config_middle = PositioningConfig(ylabel_y_position=0.5)
        config_top = PositioningConfig(ylabel_y_position=1.0)

        assert config_bottom.ylabel_y_position == 0.0
        assert config_middle.ylabel_y_position == 0.5
        assert config_top.ylabel_y_position == 1.0


class TestSeparatorConfig:
    """Test SeparatorConfig dataclass."""

    def test_default_values(self) -> None:
        """Verify default separator settings."""
        config = SeparatorConfig()

        assert config.enabled is False
        assert config.style == "dashed"
        assert config.color == "gray"

    def test_custom_values(self) -> None:
        """Verify can set custom separator settings."""
        config = SeparatorConfig(
            enabled=True,
            style="solid",
            color="black",
        )

        assert config.enabled is True
        assert config.style == "solid"
        assert config.color == "black"

    def test_all_line_styles(self) -> None:
        """Verify all supported line styles."""
        styles = ["solid", "dashed", "dotted", "dashdot"]
        for style in styles:
            config = SeparatorConfig(style=style)  # type: ignore
            assert config.style == style
