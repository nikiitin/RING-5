"""Tests for engine-independent grouped and stacked area traces."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.core.models.visualization.trace_config import LineTraceConfig
from src.web.pages.ui.plotting.types.area_plot import AreaPlot


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": [1, 2, 3, 1, 2, 3],
            "component": ["cpu"] * 3 + ["memory"] * 3,
            "power": [2.0, 4.0, 6.0, 2.0, np.nan, 3.0],
        }
    )


def test_normalized_area_precomputes_cumulative_baselines_without_mutation() -> None:
    # [test->req~ring5.plot.area~1]
    data = _data()
    original = data.copy(deep=True)
    result = AreaPlot(1, "Power share").create_traces(
        data,
        {
            "x": "time",
            "y": "power",
            "color": "component",
            "area_mode": "normalize",
            "area_missing": "zero",
            "area_interpolation": "hv",
            "legend_order": ["memory", "cpu"],
            "series_styles": {"cpu": {"use_color": True, "color": "#336699"}},
        },
    )

    assert [trace.name for trace in result.traces] == ["memory", "cpu"]
    first, second = result.traces
    assert isinstance(first, LineTraceConfig)
    assert first.fill == "tozeroy" and first.fill_base == [0.0, 0.0, 0.0]
    assert second.fill == "tonexty"
    assert second.fill_base == pytest.approx(first.y)
    assert second.y == pytest.approx([100.0, 100.0, 100.0])
    assert second.color == "#336699"
    assert first.line_shape == "hv"
    assert not first.show_markers
    pd.testing.assert_frame_equal(data, original)


def test_overlay_interpolates_missing_values_and_keeps_zero_baseline() -> None:
    result = AreaPlot(2, "Interpolated").create_traces(
        _data(),
        {
            "x": "time",
            "y": "power",
            "color": "component",
            "area_mode": "overlay",
            "area_missing": "interpolate",
            "area_interpolation": "linear",
            "area_opacity": 0.7,
        },
    )

    memory = result.traces[1]
    assert isinstance(memory, LineTraceConfig)
    assert memory.y == [2.0, 2.5, 3.0]
    assert memory.fill == "tozeroy"
    assert memory.fill_base == [0.0, 0.0, 0.0]
    assert memory.opacity == 0.7
    assert AreaPlot(2, "Area").get_legend_column({"color": "component"}) == "component"


def test_stacked_gap_treats_missing_contribution_as_zero_thickness() -> None:
    result = AreaPlot(3, "Stacked").create_traces(
        _data(),
        {"x": "time", "y": "power", "color": "component", "area_mode": "stack"},
    )

    assert result.traces[-1].y == [4.0, 4.0, 9.0]
    assert AreaPlot(3, "Area").get_legend_column({}) is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"area_mode": "cluster"}, "arrangement"),
        ({"area_interpolation": "spline"}, "interpolation"),
        ({"area_missing": "drop"}, "missing-value"),
        ({"area_opacity": 0}, "opacity"),
    ],
)
def test_area_validation_is_explicit(change: dict[str, object], message: str) -> None:
    config: dict[str, object] = {"x": "time", "y": "power"}
    config.update(change)
    with pytest.raises(ValueError, match=message):
        AreaPlot(1, "Invalid").create_traces(_data(), config)


def test_normalized_area_rejects_negative_values_and_missing_columns() -> None:
    plot = AreaPlot(1, "Invalid")
    negative = pd.DataFrame({"x": [1, 2], "y": [1.0, -1.0]})
    with pytest.raises(ValueError, match="non-negative"):
        plot.create_traces(negative, {"x": "x", "y": "y", "area_mode": "normalize"})
    with pytest.raises(ValueError, match="must exist"):
        plot.create_traces(_data(), {"x": "missing", "y": "power"})
    with pytest.raises(ValueError, match="color column"):
        plot.create_traces(_data(), {"x": "time", "y": "power", "color": "missing"})


@patch("src.web.pages.ui.plotting.types.area_plot.area_config.render")
def test_area_config_ui_delegates_with_plot_identity(mock_render: MagicMock) -> None:
    plot = AreaPlot(7, "Area")
    data = _data()
    config = {"x": "time", "y": "power"}
    expected = copy.deepcopy(config)
    mock_render.return_value = expected

    assert plot.render_config_ui(data, config) == expected
    mock_render.assert_called_once_with(data, config, 7)
