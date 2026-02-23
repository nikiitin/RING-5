"""Unit tests for StyleApplicator — public ``apply_styles`` API.

After Phase 2 Step 20 the private ``_apply_*`` helpers were deleted.
This file retains only the public-API integration tests.
"""

from typing import Any, cast

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


def _multi_bar_fig() -> go.Figure:
    """Multi-trace bar figure."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["a", "b"], y=[1, 2], name="base"))
    fig.add_trace(go.Bar(x=["a", "b"], y=[3, 4], name="opt"))
    return fig


# ===================================================================
# Public API: apply_styles
# ===================================================================


class TestApplyStyles:
    """Integration test for the full apply_styles pipeline."""

    def test_full_pipeline(self) -> None:
        sa = StyleApplicator("grouped_bar")
        fig = _multi_bar_fig()
        config: dict[str, Any] = {
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

        assert result.to_plotly_json()["layout"]["width"] == 1000
        assert result.to_plotly_json()["layout"]["title"]["text"] == "Test"

    def test_with_show_values(self) -> None:
        sa = StyleApplicator("bar")
        fig = _bar_fig()
        config: dict[str, Any] = {
            "show_values": True,
            "text_format": "%{y:.1f}",
            "text_position": "outside",
        }
        result = sa.apply_styles(fig, config)
        assert cast(go.Bar, result.data[0]).textposition == "outside"

    def test_with_shapes(self) -> None:
        sa = StyleApplicator("bar")
        fig = _bar_fig()
        shapes = [{"type": "line", "x0": 0, "x1": 1, "y0": 0.5, "y1": 0.5}]
        result = sa.apply_styles(fig, {"shapes": shapes})
        assert len(result.to_plotly_json()["layout"].get("shapes", [])) == 1
