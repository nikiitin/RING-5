"""Tests for SeriesStyleSpec — construction, serialization, immutability."""

from __future__ import annotations

import pytest

from src.core.visualization.series_style_spec import SeriesStyleSpec


class TestSeriesStyleSpecDefaults:
    """Test that default construction produces safe values."""

    def test_default_values(self) -> None:
        """All defaults should produce standard trace styling."""
        spec = SeriesStyleSpec()

        assert spec.line_width == 2.0
        assert spec.marker_size == 6
        assert spec.opacity == 1.0
        assert spec.bar_border_width == 0.0
        assert spec.bar_border_color == ""
        assert spec.hatching_pattern == ""


class TestSeriesStyleSpecCustom:
    """Test custom construction with all fields."""

    def test_custom_values(self) -> None:
        """Constructor accepts all fields."""
        spec = SeriesStyleSpec(
            line_width=3.5,
            marker_size=10,
            opacity=0.7,
            bar_border_width=1.5,
            bar_border_color="#333333",
            hatching_pattern="/",
        )

        assert spec.line_width == 3.5
        assert spec.marker_size == 10
        assert spec.opacity == 0.7
        assert spec.bar_border_width == 1.5
        assert spec.bar_border_color == "#333333"
        assert spec.hatching_pattern == "/"

    def test_hatching_patterns(self) -> None:
        """Various hatching patterns should be accepted."""
        for pattern in ["/", "\\", "|", "-", "+", "x", "o", "O", ".", "*"]:
            spec = SeriesStyleSpec(hatching_pattern=pattern)
            assert spec.hatching_pattern == pattern


class TestSeriesStyleSpecFrozen:
    """Test immutability."""

    def test_frozen(self) -> None:
        """Spec must be immutable."""
        spec = SeriesStyleSpec()
        with pytest.raises(AttributeError):
            spec.line_width = 5.0  # type: ignore[misc]

    def test_frozen_hatching(self) -> None:
        """Cannot mutate hatching_pattern."""
        spec = SeriesStyleSpec(hatching_pattern="/")
        with pytest.raises(AttributeError):
            spec.hatching_pattern = "x"  # type: ignore[misc]


class TestSeriesStyleSpecSerialization:
    """Test to_dict/from_dict round-trip."""

    def test_default_round_trip(self) -> None:
        """Default spec round-trips through dict."""
        original = SeriesStyleSpec()
        restored = SeriesStyleSpec.from_dict(original.to_dict())
        assert restored == original

    def test_custom_round_trip(self) -> None:
        """Custom spec preserves all values through round-trip."""
        original = SeriesStyleSpec(
            line_width=4.0,
            marker_size=12,
            opacity=0.5,
            bar_border_width=2.0,
            bar_border_color="#AABBCC",
            hatching_pattern="x",
        )
        restored = SeriesStyleSpec.from_dict(original.to_dict())
        assert restored == original

    def test_to_dict_produces_plain_dict(self) -> None:
        """to_dict() should produce plain Python types."""
        spec = SeriesStyleSpec(line_width=3.0, opacity=0.8)
        d = spec.to_dict()

        assert isinstance(d, dict)
        assert d["line_width"] == 3.0
        assert d["opacity"] == 0.8

    def test_from_dict_ignores_unknown_keys(self) -> None:
        """Unknown keys in input dict should not raise."""
        spec = SeriesStyleSpec.from_dict(
            {
                "line_width": 5.0,
                "unknown_key": "ignored",
            }
        )
        assert spec.line_width == 5.0
        assert spec.marker_size == 6  # default

    def test_from_dict_empty_dict(self) -> None:
        """Empty dict produces default spec."""
        spec = SeriesStyleSpec.from_dict({})
        assert spec == SeriesStyleSpec()


class TestSeriesStyleSpecOnFigureSpec:
    """Test SeriesStyleSpec integration with FigureSpec."""

    def test_figure_spec_default_series_styles_empty(self) -> None:
        """FigureSpec default has empty series_styles list."""
        from src.core.visualization.figure_spec import FigureSpec

        spec = FigureSpec()
        assert spec.series_styles == []

    def test_figure_spec_with_series_styles(self) -> None:
        """FigureSpec accepts list of SeriesStyleSpec."""
        from src.core.visualization.figure_spec import FigureSpec

        styles = [
            SeriesStyleSpec(line_width=3.0, opacity=0.9),
            SeriesStyleSpec(line_width=1.5, hatching_pattern="/"),
        ]
        spec = FigureSpec(series_styles=styles)

        assert len(spec.series_styles) == 2
        assert spec.series_styles[0].line_width == 3.0
        assert spec.series_styles[1].hatching_pattern == "/"

    def test_figure_spec_round_trip_with_series_styles(self) -> None:
        """FigureSpec with series_styles round-trips through dict."""
        from src.core.visualization.figure_spec import FigureSpec

        styles = [
            SeriesStyleSpec(opacity=0.6, bar_border_width=1.0),
            SeriesStyleSpec(marker_size=10),
        ]
        spec = FigureSpec(series_styles=styles, title="Test")
        restored = FigureSpec.from_dict(spec.to_dict())

        assert len(restored.series_styles) == 2
        assert restored.series_styles[0].opacity == 0.6
        assert restored.series_styles[0].bar_border_width == 1.0
        assert restored.series_styles[1].marker_size == 10

    def test_figure_spec_round_trip_without_series_styles(self) -> None:
        """FigureSpec without series_styles round-trips as empty list."""
        from src.core.visualization.figure_spec import FigureSpec

        spec = FigureSpec(title="No Styles")
        restored = FigureSpec.from_dict(spec.to_dict())

        assert restored.series_styles == []
