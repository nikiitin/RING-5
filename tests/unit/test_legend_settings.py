"""Unit tests for legend_settings — legend tier constants and component init."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.web.components.plotting.settings.legend_settings import (
    _LEGEND_PREFIXES,
    LegendSettingsComponent,
)


class TestLegendSettingsInit:
    """Verify __init__ stores plot_id and plot_type."""

    def test_stores_plot_id(self) -> None:
        comp = LegendSettingsComponent(plot_id=7, plot_type="bar")
        assert comp.plot_id == 7

    def test_stores_plot_type(self) -> None:
        comp = LegendSettingsComponent(plot_id=1, plot_type="scatter")
        assert comp.plot_type == "scatter"


class TestLegendPrefixes:
    """Validate the _LEGEND_PREFIXES module-level constant."""

    def test_covers_all_three_tiers(self) -> None:
        assert set(_LEGEND_PREFIXES.keys()) == {"primary", "secondary", "tertiary"}

    def test_primary_prefix(self) -> None:
        assert _LEGEND_PREFIXES["primary"] == "legend_"

    def test_secondary_prefix(self) -> None:
        assert _LEGEND_PREFIXES["secondary"] == "legend2_"

    def test_tertiary_prefix(self) -> None:
        assert _LEGEND_PREFIXES["tertiary"] == "legend3_"


class TestRenderPrimaryOnly:
    """Render with only primary legend (no secondary/tertiary)."""

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_render_calls_render_legend_section_once(self, mock_st: MagicMock) -> None:
        """When has_secondary=False and has_tertiary=False, _render_legend_section
        is called exactly once (for the primary legend)."""
        mock_st.pills.return_value = "primary"

        comp = LegendSettingsComponent(plot_id=1, plot_type="bar")
        comp._render_legend_section = MagicMock(return_value={})  # type: ignore[method-assign]

        comp.render({}, has_secondary=False, has_tertiary=False)

        comp._render_legend_section.assert_called_once()
