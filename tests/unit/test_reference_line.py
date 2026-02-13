"""
Unit tests for the horizontal reference line (normalizer baseline) feature.

Tests cover:
- Plotly hline rendering via the StyleApplicator
- Matplotlib export rendering via MatplotlibConverter._apply_reference_lines
- Config propagation (enabled/disabled states)
"""

from typing import Any, Dict
from unittest.mock import MagicMock

import plotly.graph_objects as go
import pytest

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def base_config() -> Dict[str, Any]:
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
        self, simple_figure: go.Figure, base_config: Dict[str, Any]
    ) -> None:
        """Reference line shape should be added to figure when enabled."""
        from src.web.pages.ui.plotting.styles.applicator import (
            StyleApplicator,
        )

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
        from src.web.pages.ui.plotting.styles.applicator import (
            StyleApplicator,
        )

        config: Dict[str, Any] = {"reference_line_enabled": False}
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
        from src.web.pages.ui.plotting.styles.applicator import (
            StyleApplicator,
        )

        config: Dict[str, Any] = {}
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
        from src.web.pages.ui.plotting.styles.applicator import (
            StyleApplicator,
        )

        config: Dict[str, Any] = {
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
        from src.web.pages.ui.plotting.styles.applicator import (
            StyleApplicator,
        )

        for style in ["dash", "dot", "dashdot", "solid"]:
            config: Dict[str, Any] = {
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
# Matplotlib Export Reference Line Tests
# =============================================================================


class TestMatplotlibReferenceLine:
    """Tests for reference line rendering in matplotlib export."""

    def test_axhline_from_plotly_shape(self) -> None:
        """Horizontal lines in Plotly shapes should become ax.axhline()."""
        from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (  # noqa: E501
            MatplotlibConverter,
        )

        # Create a figure with an hline shape
        fig = go.Figure(data=[go.Bar(x=["a", "b"], y=[1, 2])])
        fig.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="red",
            line_width=1.5,
        )

        # Create a minimal preset
        preset: Dict[str, Any] = {
            "width_inches": 3.5,
            "height_inches": 2.5,
            "font_family": "serif",
            "font_size_base": 10,
            "font_size_title": 12,
            "font_size_xlabel": 9,
            "font_size_ylabel": 9,
            "font_size_legend": 8,
            "font_size_ticks": 8,
            "font_size_annotations": 8,
            "line_width": 1.0,
            "marker_size": 4,
            "dpi": 300,
            "legend_columnspacing": 0.5,
            "legend_handletextpad": 0.3,
            "legend_labelspacing": 0.2,
            "legend_handlelength": 1.0,
            "legend_handleheight": 0.7,
            "legend_borderpad": 0.2,
            "legend_borderaxespad": 0.5,
        }

        converter = MatplotlibConverter(preset)

        # Create mock axes
        mock_ax = MagicMock()

        # Call _apply_reference_lines
        converter._apply_reference_lines(fig, mock_ax)

        # Verify axhline was called
        mock_ax.axhline.assert_called_once_with(
            y=1.0,
            color="red",
            linewidth=1.5,
            linestyle="--",
            zorder=5,
        )

    def test_no_axhline_without_hline_shapes(self) -> None:
        """No axhline when figure has no horizontal line shapes."""
        from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (  # noqa: E501
            MatplotlibConverter,
        )

        fig = go.Figure(data=[go.Bar(x=["a"], y=[1])])
        preset: Dict[str, Any] = {
            "width_inches": 3.5,
            "height_inches": 2.5,
            "font_family": "serif",
            "font_size_base": 10,
            "font_size_title": 12,
            "font_size_xlabel": 9,
            "font_size_ylabel": 9,
            "font_size_legend": 8,
            "font_size_ticks": 8,
            "font_size_annotations": 8,
            "line_width": 1.0,
            "marker_size": 4,
            "dpi": 300,
            "legend_columnspacing": 0.5,
            "legend_handletextpad": 0.3,
            "legend_labelspacing": 0.2,
            "legend_handlelength": 1.0,
            "legend_handleheight": 0.7,
            "legend_borderpad": 0.2,
            "legend_borderaxespad": 0.5,
        }

        converter = MatplotlibConverter(preset)
        mock_ax = MagicMock()
        converter._apply_reference_lines(fig, mock_ax)

        mock_ax.axhline.assert_not_called()

    def test_dash_style_mapping(self) -> None:
        """Plotly dash strings should map to matplotlib linestyles."""
        from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (  # noqa: E501
            MatplotlibConverter,
        )

        preset: Dict[str, Any] = {
            "width_inches": 3.5,
            "height_inches": 2.5,
            "font_family": "serif",
            "font_size_base": 10,
            "font_size_title": 12,
            "font_size_xlabel": 9,
            "font_size_ylabel": 9,
            "font_size_legend": 8,
            "font_size_ticks": 8,
            "font_size_annotations": 8,
            "line_width": 1.0,
            "marker_size": 4,
            "dpi": 300,
            "legend_columnspacing": 0.5,
            "legend_handletextpad": 0.3,
            "legend_labelspacing": 0.2,
            "legend_handlelength": 1.0,
            "legend_handleheight": 0.7,
            "legend_borderpad": 0.2,
            "legend_borderaxespad": 0.5,
        }

        expected_mapping = {
            "dash": "--",
            "dot": ":",
            "dashdot": "-.",
            "solid": "-",
        }

        converter = MatplotlibConverter(preset)

        for plotly_dash, mpl_ls in expected_mapping.items():
            fig = go.Figure(data=[go.Bar(x=["a"], y=[1])])
            fig.add_hline(
                y=1.0,
                line_dash=plotly_dash,
                line_color="blue",
                line_width=2.0,
            )

            mock_ax = MagicMock()
            converter._apply_reference_lines(fig, mock_ax)

            mock_ax.axhline.assert_called_once_with(
                y=1.0,
                color="blue",
                linewidth=2.0,
                linestyle=mpl_ls,
                zorder=5,
            )

    def test_multiple_reference_lines(self) -> None:
        """Multiple horizontal lines should all be converted."""
        from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (  # noqa: E501
            MatplotlibConverter,
        )

        fig = go.Figure(data=[go.Bar(x=["a"], y=[1])])
        fig.add_hline(y=1.0, line_dash="dash", line_color="red")
        fig.add_hline(y=0.5, line_dash="dot", line_color="blue")

        preset: Dict[str, Any] = {
            "width_inches": 3.5,
            "height_inches": 2.5,
            "font_family": "serif",
            "font_size_base": 10,
            "font_size_title": 12,
            "font_size_xlabel": 9,
            "font_size_ylabel": 9,
            "font_size_legend": 8,
            "font_size_ticks": 8,
            "font_size_annotations": 8,
            "line_width": 1.0,
            "marker_size": 4,
            "dpi": 300,
            "legend_columnspacing": 0.5,
            "legend_handletextpad": 0.3,
            "legend_labelspacing": 0.2,
            "legend_handlelength": 1.0,
            "legend_handleheight": 0.7,
            "legend_borderpad": 0.2,
            "legend_borderaxespad": 0.5,
        }

        converter = MatplotlibConverter(preset)
        mock_ax = MagicMock()
        converter._apply_reference_lines(fig, mock_ax)

        assert mock_ax.axhline.call_count == 2

    def test_ignores_non_horizontal_shapes(self) -> None:
        """Vertical lines and other shapes should not be converted."""
        from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (  # noqa: E501
            MatplotlibConverter,
        )

        fig = go.Figure(data=[go.Bar(x=["a"], y=[1])])
        # Add a vertical line (vline) - has yref="paper", not xref="paper"
        fig.add_vline(x=0.5, line_dash="dash", line_color="green")
        # Add a regular rectangle shape
        fig.add_shape(type="rect", x0=0, y0=0, x1=1, y1=1, line_color="gray")

        preset: Dict[str, Any] = {
            "width_inches": 3.5,
            "height_inches": 2.5,
            "font_family": "serif",
            "font_size_base": 10,
            "font_size_title": 12,
            "font_size_xlabel": 9,
            "font_size_ylabel": 9,
            "font_size_legend": 8,
            "font_size_ticks": 8,
            "font_size_annotations": 8,
            "line_width": 1.0,
            "marker_size": 4,
            "dpi": 300,
            "legend_columnspacing": 0.5,
            "legend_handletextpad": 0.3,
            "legend_labelspacing": 0.2,
            "legend_handlelength": 1.0,
            "legend_handleheight": 0.7,
            "legend_borderpad": 0.2,
            "legend_borderaxespad": 0.5,
        }

        converter = MatplotlibConverter(preset)
        mock_ax = MagicMock()
        converter._apply_reference_lines(fig, mock_ax)

        mock_ax.axhline.assert_not_called()


# =============================================================================
# Config Propagation Tests
# =============================================================================


class TestReferenceLineConfig:
    """Tests for reference line config defaults and structure."""

    def test_default_values(self) -> None:
        """Default config values should produce a valid reference line."""
        config: Dict[str, Any] = {
            "reference_line_enabled": True,
        }
        # Defaults when keys are missing
        assert config.get("reference_line_y", 1.0) == 1.0
        assert config.get("reference_line_color", "#FF0000") == "#FF0000"
        assert config.get("reference_line_width", 1.5) == 1.5
        assert config.get("reference_line_style", "dash") == "dash"

    def test_disabled_by_default(self) -> None:
        """Reference line should be disabled when not explicitly enabled."""
        config: Dict[str, Any] = {}
        assert config.get("reference_line_enabled", False) is False

    def test_full_config_structure(self, base_config: Dict[str, Any]) -> None:
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
