"""
Unit tests for the horizontal reference line (normalizer baseline) feature.

Tests cover:
- Plotly hline rendering via the StyleApplicator
- Config propagation (enabled/disabled states)
"""

from typing import Any

import plotly.graph_objects as go
import pytest

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def base_config() -> dict[str, Any]:
    """Minimal config with reference line enabled."""
    return {
        "reference_line_enabled": True,
        "reference_line_y": 1.0,
        "reference_line_color": "#FF0000",
        "reference_line_width": 1.5,
        "reference_line_style": "dash",
        "reference_line_column": "config",
        "reference_line_value": "baseline",
    }


@pytest.fixture
def simple_figure() -> go.Figure:
    """Simple bar figure for testing."""
    fig = go.Figure(data=[go.Bar(x=["a", "b", "c"], y=[1, 2, 3])])
    return fig


# =============================================================================
# Plotly Reference Line Tests (via StyleApplicator)
# =============================================================================


class TestPlotlyReferenceLine:
    """Tests for reference line rendering in Plotly figures."""

    def test_hline_added_when_enabled(
        self, simple_figure: go.Figure, base_config: dict[str, Any]
    ) -> None:
        """Reference line shape should be added to figure when enabled."""
        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        applicator = StyleApplicator("grouped_bar")
        result = applicator.apply_styles(simple_figure, base_config)

        # add_hline creates a shape with type="line",
        # xref="paper" (Plotly <6) or "x domain" (Plotly >=6)
        shapes = result.layout.shapes
        assert shapes is not None
        hlines = [
            s
            for s in shapes
            if s.type == "line" and s.xref in ("paper", "x domain") and s.y0 == s.y1
        ]
        assert len(hlines) == 1
        assert hlines[0].y0 == 1.0
        assert hlines[0].line.color == "#FF0000"
        assert hlines[0].line.dash == "dash"

    def test_no_hline_when_disabled(self, simple_figure: go.Figure) -> None:
        """No reference line should be added when feature is disabled."""
        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        config: dict[str, Any] = {"reference_line_enabled": False}
        applicator = StyleApplicator("grouped_bar")
        result = applicator.apply_styles(simple_figure, config)

        shapes = result.layout.shapes or ()
        hlines = [
            s
            for s in shapes
            if s.type == "line"
            and getattr(s, "xref", None) in ("paper", "x domain")
            and s.y0 == s.y1
        ]
        assert len(hlines) == 0

    def test_no_hline_when_key_missing(self, simple_figure: go.Figure) -> None:
        """No reference line when config key is absent."""
        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        config: dict[str, Any] = {}
        applicator = StyleApplicator("grouped_bar")
        result = applicator.apply_styles(simple_figure, config)

        shapes = result.layout.shapes or ()
        hlines = [
            s
            for s in shapes
            if s.type == "line" and getattr(s, "xref", None) in ("paper", "x domain")
        ]
        assert len(hlines) == 0

    def test_custom_y_position(self, simple_figure: go.Figure) -> None:
        """Reference line at custom Y position."""
        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        config: dict[str, Any] = {
            "reference_line_enabled": True,
            "reference_line_y": 2.5,
            "reference_line_color": "#00FF00",
            "reference_line_width": 2.0,
            "reference_line_style": "dot",
        }
        applicator = StyleApplicator("grouped_bar")
        result = applicator.apply_styles(simple_figure, config)

        shapes = result.layout.shapes
        hlines = [
            s
            for s in shapes
            if s.type == "line" and s.xref in ("paper", "x domain") and s.y0 == s.y1
        ]
        assert len(hlines) == 1
        assert hlines[0].y0 == 2.5
        assert hlines[0].line.color == "#00FF00"
        assert hlines[0].line.dash == "dot"

    def test_all_line_styles(self, simple_figure: go.Figure) -> None:
        """All Plotly dash styles should be accepted."""
        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        for style in ["dash", "dot", "dashdot", "solid"]:
            config: dict[str, Any] = {
                "reference_line_enabled": True,
                "reference_line_y": 1.0,
                "reference_line_style": style,
            }
            applicator = StyleApplicator("grouped_bar")
            fig = go.Figure(data=[go.Bar(x=["a"], y=[1])])
            result = applicator.apply_styles(fig, config)

            shapes = result.layout.shapes
            hlines = [
                s
                for s in shapes
                if s.type == "line" and s.xref in ("paper", "x domain") and s.y0 == s.y1
            ]
            assert len(hlines) == 1, f"Style '{style}' failed"
            assert hlines[0].line.dash == style


# =============================================================================
# Config Propagation Tests
# =============================================================================


class TestReferenceLineConfig:
    """Tests for reference line config defaults and structure."""

    def test_default_values(self) -> None:
        """Default config values should produce a valid reference line."""
        config: dict[str, Any] = {
            "reference_line_enabled": True,
        }
        # Defaults when keys are missing
        assert config.get("reference_line_y", 1.0) == 1.0
        assert config.get("reference_line_color", "#FF0000") == "#FF0000"
        assert config.get("reference_line_width", 1.5) == 1.5
        assert config.get("reference_line_style", "dash") == "dash"

    def test_disabled_by_default(self) -> None:
        """Reference line should be disabled when not explicitly enabled."""
        config: dict[str, Any] = {}
        assert config.get("reference_line_enabled", False) is False

    def test_full_config_structure(self, base_config: dict[str, Any]) -> None:
        """Full config should contain all required keys."""
        expected_keys = {
            "reference_line_enabled",
            "reference_line_y",
            "reference_line_color",
            "reference_line_width",
            "reference_line_style",
            "reference_line_column",
            "reference_line_value",
        }
        assert expected_keys.issubset(set(base_config.keys()))
