"""Tests for shared-scale engine-independent radar traces."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.core.models.visualization.trace_config import RadarTraceConfig
from src.web.pages.ui.plotting.types.radar_plot import RadarPlot


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "metric": ["speed", "energy", "size", "speed", "energy", "size"],
            "variant": ["base"] * 3 + ["new"] * 3,
            "score": [0.6, 0.8, 0.7, 0.9, np.nan, 0.5],
        }
    )


def test_grouped_radar_resolves_one_scale_order_and_missing_value_without_mutation() -> None:
    # [test->req~ring5.plot.radar~1]
    data = _data()
    original = data.copy(deep=True)
    result = RadarPlot(1, "Profile").create_traces(
        data,
        {
            "x": "metric",
            "y": "score",
            "color": "variant",
            "xaxis_order": ["size", "speed", "energy"],
            "legend_order": ["new", "base"],
            "radar_scale_mode": "zero",
            "series_styles": {"base": {"use_color": True, "color": "#336699"}},
        },
    )

    assert [trace.name for trace in result.traces] == ["new", "base"]
    first, second = result.traces
    assert isinstance(first, RadarTraceConfig)
    assert first.categories == ["size", "speed", "energy"]
    assert first.values == [0.5, 0.9, 0.0]
    assert first.radial_min == second.radial_min == 0.0
    assert first.radial_max == second.radial_max == 0.9
    assert second.color == "#336699"
    assert len(first.custom_data["drilldown"]) == 3
    assert RadarPlot(1, "Radar").get_legend_column({"color": "variant"}) == "variant"
    pd.testing.assert_frame_equal(data, original)


def test_custom_radar_geometry_and_profile_controls() -> None:
    trace = (
        RadarPlot(2, "Custom")
        .create_traces(
            _data(),
            {
                "x": "metric",
                "y": "score",
                "radar_scale_mode": "custom",
                "radar_min": -1,
                "radar_max": 2,
                "radar_start_angle": 30,
                "radar_clockwise": False,
                "radar_fill": False,
                "radar_markers": False,
                "radar_opacity": 0.6,
                "radar_line_width": 3,
            },
        )
        .traces[0]
    )

    assert isinstance(trace, RadarTraceConfig)
    assert (trace.radial_min, trace.radial_max) == (-1, 2)
    assert trace.start_angle == 30 and not trace.clockwise
    assert not trace.fill_area and not trace.show_markers
    assert trace.opacity == 0.6 and trace.line_width == 3
    assert RadarPlot(2, "Radar").get_legend_column({}) is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"radar_scale_mode": "local"}, "scale mode"),
        ({"radar_start_angle": 361}, "start angle"),
        ({"radar_opacity": 0}, "opacity"),
        ({"marker_size": 0}, "marker size"),
        ({"radar_line_width": 0}, "line width"),
        ({"radar_scale_mode": "custom", "radar_min": 2, "radar_max": 1}, "maximum"),
    ],
)
def test_radar_validation_is_explicit(change: dict[str, object], message: str) -> None:
    config: dict[str, object] = {"x": "metric", "y": "score"}
    config.update(change)
    with pytest.raises(ValueError, match=message):
        RadarPlot(1, "Invalid").create_traces(_data(), config)


def test_radar_requires_columns_and_three_categories() -> None:
    plot = RadarPlot(1, "Invalid")
    with pytest.raises(ValueError, match="must exist"):
        plot.create_traces(_data(), {"x": "missing", "y": "score"})
    with pytest.raises(ValueError, match="three categories"):
        plot.create_traces(
            pd.DataFrame({"metric": ["a", "b"], "score": [1, 2]}),
            {"x": "metric", "y": "score"},
        )
    with pytest.raises(ValueError, match="color column"):
        plot.create_traces(_data(), {"x": "metric", "y": "score", "color": "missing"})


@patch("src.web.pages.ui.plotting.types.radar_plot.radar_config.render")
def test_radar_config_ui_delegates_with_plot_identity(mock_render: MagicMock) -> None:
    plot = RadarPlot(7, "Radar")
    data = _data()
    config = {"x": "metric", "y": "score"}
    expected = copy.deepcopy(config)
    mock_render.return_value = expected

    assert plot.render_config_ui(data, config) == expected
    mock_render.assert_called_once_with(data, config, 7)
