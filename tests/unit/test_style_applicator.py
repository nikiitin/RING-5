"""Unit tests for StyleApplicator — Plotly figure styling engine.

Focuses on methods NOT covered by test_applicator_standoff.py and
test_data_labels.py: dimensions, backgrounds, legend, series styling,
contrast color, titles, and conditional labels.
"""

from typing import Any, Dict

import plotly.graph_objects as go

from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bar_fig() -> go.Figure:
    """Create a simple bar figure for testing."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["a", "b"], y=[1, 2], name="trace1"))
    return fig


def _scatter_fig() -> go.Figure:
    """Create a scatter figure for testing."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2], y=[3, 4], name="s1", mode="markers"))
    return fig


def _multi_bar_fig() -> go.Figure:
    """Multi-trace bar figure."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["a", "b"], y=[1, 2], name="base"))
    fig.add_trace(go.Bar(x=["a", "b"], y=[3, 4], name="opt"))
    return fig


# ===================================================================
# Dimensions & Margins
# ===================================================================


class TestDimensionsAndMargins:
    """Tests for _apply_dimensions_and_margins."""

    def test_default_dimensions(self) -> None:
        sa = StyleApplicator("bar")
        fig = sa._apply_dimensions_and_margins(_bar_fig(), {})
        assert fig.layout.width == 800
        assert fig.layout.height == 500

    def test_custom_dimensions(self) -> None:
        sa = StyleApplicator("bar")
        fig = sa._apply_dimensions_and_margins(_bar_fig(), {"width": 1200, "height": 600})
        assert fig.layout.width == 1200
        assert fig.layout.height == 600

    def test_bar_type_adds_bargap(self) -> None:
        sa = StyleApplicator("bar")
        fig = sa._apply_dimensions_and_margins(_bar_fig(), {"bargap": 0.3})
        assert fig.layout.bargap == 0.3

    def test_grouped_bar_adds_bargroupgap(self) -> None:
        sa = StyleApplicator("grouped_bar")
        fig = sa._apply_dimensions_and_margins(_bar_fig(), {"bargroupgap": 0.5})
        assert fig.layout.bargroupgap == 0.5

    def test_non_bar_type_no_bargap(self) -> None:
        sa = StyleApplicator("scatter")
        fig = sa._apply_dimensions_and_margins(_scatter_fig(), {})
        assert fig.layout.bargap is None


# ===================================================================
# Backgrounds
# ===================================================================


class TestBackgrounds:
    """Tests for _apply_backgrounds."""

    def test_plot_bgcolor(self) -> None:
        sa = StyleApplicator("bar")
        fig = sa._apply_backgrounds(_bar_fig(), {"plot_bgcolor": "#FAFAFA"})
        assert fig.layout.plot_bgcolor == "#FAFAFA"

    def test_paper_bgcolor(self) -> None:
        sa = StyleApplicator("bar")
        fig = sa._apply_backgrounds(_bar_fig(), {"paper_bgcolor": "#EEEEEE"})
        assert fig.layout.paper_bgcolor == "#EEEEEE"

    def test_no_color_set(self) -> None:
        sa = StyleApplicator("bar")
        result = sa._apply_backgrounds(_bar_fig(), {})
        assert result is not None


# ===================================================================
# Legend Config
# ===================================================================


class TestBuildLegendConfig:
    """Tests for _build_legend_config."""

    def test_default_legend(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({})
        assert lc["orientation"] == "v"
        assert lc["xanchor"] == "right"
        assert lc["yanchor"] == "top"

    def test_auto_xanchor_left(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({"legend_x": 0.1})
        assert lc["xanchor"] == "left"

    def test_explicit_xanchor(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({"legend_xanchor": "center"})
        assert lc["xanchor"] == "center"

    def test_auto_yanchor_bottom(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({"legend_y": 0.2})
        assert lc["yanchor"] == "bottom"

    def test_legend_font_color(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({"legend_font_color": "#FF0000"})
        assert lc["font"]["color"] == "#FF0000"

    def test_legend_title_font(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({"legend_title_font_color": "#00FF00"})
        assert lc["title"]["font"]["color"] == "#00FF00"

    def test_legend_bgcolor(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({"legend_bgcolor": "white"})
        assert lc["bgcolor"] == "white"

    def test_legend_border(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({"legend_border_width": 2, "legend_border_color": "#333"})
        assert lc["borderwidth"] == 2
        assert lc["bordercolor"] == "#333"

    def test_legend_itemsizing(self) -> None:
        sa = StyleApplicator("bar")
        lc = sa._build_legend_config({"legend_itemsizing": "constant"})
        assert lc["itemsizing"] == "constant"


# ===================================================================
# Titles
# ===================================================================


class TestApplyTitles:
    """Tests for _apply_titles."""

    def test_title_applied(self) -> None:
        sa = StyleApplicator("bar")
        fig = sa._apply_titles(_bar_fig(), {"title": "My Chart"})
        assert fig.layout.title.text == "My Chart"

    def test_title_undefined_replaced(self) -> None:
        sa = StyleApplicator("bar")
        fig = sa._apply_titles(_bar_fig(), {"title": "undefined"})
        assert fig.layout.title.text == ""

    def test_legend_title(self) -> None:
        sa = StyleApplicator("bar")
        fig = sa._apply_titles(_bar_fig(), {"legend_title": "Groups"})
        assert fig.layout.legend.title.text == "Groups"


# ===================================================================
# Contrast Color
# ===================================================================


class TestGetContrastColor:
    """Tests for _get_contrast_color luminance helper."""

    def test_white_returns_black(self) -> None:
        sa = StyleApplicator("bar")
        assert sa._get_contrast_color("#FFFFFF") == "#000000"

    def test_black_returns_white(self) -> None:
        sa = StyleApplicator("bar")
        assert sa._get_contrast_color("#000000") == "#FFFFFF"

    def test_invalid_returns_black(self) -> None:
        sa = StyleApplicator("bar")
        assert sa._get_contrast_color("") == "#000000"
        assert sa._get_contrast_color("#ABC") == "#000000"

    def test_midtone(self) -> None:
        sa = StyleApplicator("bar")
        # Dark blue → should return white
        assert sa._get_contrast_color("#0000FF") == "#FFFFFF"
        # Light yellow → should return black
        assert sa._get_contrast_color("#FFFF00") == "#000000"


# ===================================================================
# Series Styling
# ===================================================================


class TestApplySeriesStyling:
    """Tests for _apply_series_styling."""

    def test_custom_color(self) -> None:
        sa = StyleApplicator("bar")
        fig = _bar_fig()
        config: Dict[str, Any] = {
            "series_styles": {"trace1": {"use_color": True, "color": "#FF0000"}}
        }
        sa._apply_series_styling(fig, config)
        assert fig.data[0].marker.color == "#FF0000"

    def test_palette_colors(self) -> None:
        sa = StyleApplicator("bar")
        fig = _multi_bar_fig()
        config: Dict[str, Any] = {"color_palette": "Plotly"}
        sa._apply_series_styling(fig, config)
        # Should apply palette colors to both traces
        assert fig.data[0].marker.color is not None

    def test_rename_series(self) -> None:
        sa = StyleApplicator("bar")
        fig = _bar_fig()
        config: Dict[str, Any] = {"series_styles": {"trace1": {"name": "renamed"}}}
        sa._apply_series_styling(fig, config)
        assert fig.data[0].name == "renamed"

    def test_pattern_applied(self) -> None:
        sa = StyleApplicator("bar")
        fig = _bar_fig()
        config: Dict[str, Any] = {"series_styles": {"trace1": {"pattern": "/"}}}
        sa._apply_series_styling(fig, config)
        assert fig.data[0].marker.pattern.shape == "/"

    def test_enable_stripes(self) -> None:
        sa = StyleApplicator("bar")
        fig = _bar_fig()
        sa._apply_series_styling(fig, {"enable_stripes": True})
        assert fig.data[0].marker.pattern.shape == "/"


# ===================================================================
# Full apply_styles
# ===================================================================


class TestApplyStyles:
    """Integration test for the full apply_styles pipeline."""

    def test_full_pipeline(self) -> None:
        sa = StyleApplicator("grouped_bar")
        fig = _multi_bar_fig()
        config: Dict[str, Any] = {
            "width": 1000,
            "height": 600,
            "title": "Test",
            "xlabel": "Category",
            "ylabel": "Value",
            "plot_bgcolor": "#FFFFFF",
            "bargap": 0.2,
            "bargroupgap": 0.1,
        }
        result = sa.apply_styles(fig, config)

        assert result.layout.width == 1000
        assert result.layout.title.text == "Test"

    def test_with_show_values(self) -> None:
        sa = StyleApplicator("bar")
        fig = _bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_format": "%{y:.1f}",
            "text_position": "outside",
        }
        result = sa.apply_styles(fig, config)
        assert result.data[0].textposition == "outside"

    def test_with_shapes(self) -> None:
        sa = StyleApplicator("bar")
        fig = _bar_fig()
        shapes = [{"type": "line", "x0": 0, "x1": 1, "y0": 0.5, "y1": 0.5}]
        result = sa.apply_styles(fig, {"shapes": shapes})
        assert len(result.layout.shapes) == 1


# ===================================================================
# Legend Layout
# ===================================================================


class TestApplyLegendLayout:
    """Tests for _apply_legend_layout with multi-column legends."""

    def test_single_column(self) -> None:
        sa = StyleApplicator("bar")
        fig = _multi_bar_fig()
        legend_cfg: Dict[str, Any] = {"x": 1.0, "y": 1.0, "orientation": "v"}
        sa._apply_legend_layout(fig, {}, legend_cfg)
        assert fig.layout.legend.x == 1.0

    def test_multi_column(self) -> None:
        sa = StyleApplicator("bar")
        fig = _multi_bar_fig()
        legend_cfg: Dict[str, Any] = {"x": 1.0, "y": 1.0, "xanchor": "left"}
        config: Dict[str, Any] = {"legend_ncols": 2, "width": 1000}
        sa._apply_legend_layout(fig, config, legend_cfg)
        # Both traces should have different legend assignments
        legends = [t.legend for t in fig.data]
        assert "legend" in legends  # First trace uses default legend

    def test_multi_column_empty_fig(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        legend_cfg: Dict[str, Any] = {"x": 1.0, "y": 1.0}
        config: Dict[str, Any] = {"legend_ncols": 3}
        # Should not crash on empty figure
        sa._apply_legend_layout(fig, config, legend_cfg)
