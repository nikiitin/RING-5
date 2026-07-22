"""Tests for grouped empirical cumulative distribution traces."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import LineTraceConfig
from src.web.pages.ui.plotting.types.ecdf_plot import EcdfPlot


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "variant": ["base", "base", "base", "base", "new", "new", "new"],
            "latency": [1.0, 2.0, 2.0, "bad", 2.0, 3.0, 5.0],
        }
    )


def test_grouped_ecdf_aggregates_duplicates_and_preserves_source() -> None:
    # [test->req~ring5.plot.ecdf~1]
    data = _data()
    original = data.copy(deep=True)
    result = EcdfPlot(1, "Latency distribution").create_traces(
        data,
        {
            "x": "latency",
            "color": "variant",
            "ecdf_y_mode": "count",
            "ecdf_markers": True,
            "marker_size": 8,
            "legend_order": ["new", "base"],
            "series_styles": {"base": {"use_color": True, "color": "#336699"}},
        },
    )

    assert [trace.name for trace in result.traces] == ["new", "base"]
    base = result.traces[1]
    assert isinstance(base, LineTraceConfig)
    assert base.x == [1.0, 2.0]
    assert base.y == [1.0, 3.0]
    assert base.line_shape == "hv"
    assert base.show_markers and base.marker_size == 8
    assert base.color == "#336699"
    assert len(base.custom_data["drilldown"]) == 2
    assert EcdfPlot(1, "ECDF").get_legend_column({"color": "variant"}) == "variant"
    pd.testing.assert_frame_equal(data, original)


def test_complementary_proportion_is_remaining_fraction_after_threshold() -> None:
    trace = (
        EcdfPlot(2, "Survival")
        .create_traces(
            _data(),
            {
                "x": "latency",
                "ecdf_complementary": True,
                "ecdf_y_mode": "proportion",
            },
        )
        .traces[0]
    )

    assert isinstance(trace, LineTraceConfig)
    assert trace.x == [1.0, 2.0, 3.0, 5.0]
    assert trace.y == pytest.approx([5 / 6, 1 / 3, 1 / 6, 0.0])
    assert not trace.show_markers
    assert EcdfPlot(2, "ECDF").get_legend_column({}) is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"ecdf_y_mode": "percent"}, "Y-axis mode"),
        ({"marker_size": 0}, "marker size"),
        ({"marker_size": 31}, "marker size"),
    ],
)
def test_ecdf_validation_is_explicit(change: dict[str, object], message: str) -> None:
    config: dict[str, object] = {"x": "latency"}
    config.update(change)
    with pytest.raises(ValueError, match=message):
        EcdfPlot(1, "Invalid").create_traces(_data(), config)


def test_ecdf_rejects_missing_mapping_columns() -> None:
    plot = EcdfPlot(1, "Invalid")
    with pytest.raises(ValueError, match="value column"):
        plot.create_traces(_data(), {"x": "missing"})
    with pytest.raises(ValueError, match="color column"):
        plot.create_traces(_data(), {"x": "latency", "color": "missing"})


@patch("src.web.pages.ui.plotting.types.ecdf_plot.ecdf_config.render")
def test_ecdf_config_ui_delegates_with_plot_identity(mock_render: MagicMock) -> None:
    plot = EcdfPlot(7, "ECDF")
    data = _data()
    config = {"x": "latency"}
    expected = copy.deepcopy(config)
    mock_render.return_value = expected

    assert plot.render_config_ui(data, config) == expected
    mock_render.assert_called_once_with(data, config, 7)
