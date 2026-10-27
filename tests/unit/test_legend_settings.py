"""Unit tests for legend_settings — legend tier constants and component init."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from typing import Any

import pytest

from tests.conftest import columns_side_effect

from src.core.models.plot_config import PlotConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering.config_builder import ConfigSpecBuilder

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


@pytest.mark.parametrize(
    "coordinates",
    [{}, {"legend_x": 0.4}, {"legend_y": 0.6}, {"legend_x": 1.2, "legend_y": 1.1}],
)
@patch("src.web.components.plotting.settings.legend_settings.st")
def test_primary_position_controls_preserve_automatic_and_explicit_values(
    mock_st: MagicMock, coordinates: PlotConfig
) -> None:
    """Opening legend controls never changes automatic placement into outside placement."""
    mock_st.columns.side_effect = columns_side_effect
    original = dict(coordinates)
    calls: dict[str, dict[str, Any]] = {}

    def numeric(
        label: str, saved: PlotConfig, key: str, plot_id: int, **kwargs: Any
    ) -> int | float:
        calls[key] = kwargs
        value: int | float = saved.get(key, kwargs["default"])
        return value

    component = LegendSettingsComponent(plot_id=7, plot_type="bar")
    with (
        patch("src.web.components.plotting.settings.legend_settings.numeric_input", numeric),
        patch(
            "src.web.components.plotting.settings.legend_settings.select_option",
            return_value="vertical",
        ),
    ):
        emitted = component._render_legend_position(coordinates, "theme_", "legend_")
    assert emitted["legend_x"] == coordinates.get("legend_x", -1.0)
    assert emitted["legend_y"] == coordinates.get("legend_y", -1.0)
    assert all(options["default"] == -1.0 for options in calls.values())
    assert all("-1.0 = automatic" in options["help"] for options in calls.values())
    legend = ConfigSpecBuilder.from_config(emitted).legends[0]
    assert legend.custom_position is bool(coordinates)
    restored = FigureConfig.from_dict(ConfigSpecBuilder.from_config(emitted).to_dict())
    assert restored.legends[0] == legend
    assert coordinates == original
    assert mock_st.caption.called
