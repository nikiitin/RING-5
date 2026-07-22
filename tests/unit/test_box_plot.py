"""Tests for grouped, engine-independent box plot traces."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import BoxTraceConfig
from src.web.pages.ui.plotting.types.box_plot import BoxPlot, _quartiles


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["A"] * 8 + ["B"] * 4,
            "variant": ["base"] * 5 + ["new"] * 3 + ["base"] * 4,
            "ipc": [1.0, 2.0, 2.0, 3.0, 20.0, 2.0, 3.0, 4.0, 4.0, 5.0, 6.0, 7.0],
        }
    )


def test_grouped_box_traces_precompute_distribution_without_mutating_data() -> None:
    # [test->req~ring5.plot.box~1]
    plot = BoxPlot(1, "IPC distribution")
    data = _data()
    original = data.copy(deep=True)
    config = {
        "x": "benchmark",
        "y": "ipc",
        "color": "variant",
        "point_mode": "outliers",
        "quartile_method": "linear",
        "whisker_mode": "tukey",
        "whisker_multiplier": 1.5,
        "xaxis_order": ["B", "A"],
        "legend_order": ["new", "base"],
        "show_mean": True,
    }

    result = plot.create_traces(data, config)

    assert all(isinstance(trace, BoxTraceConfig) for trace in result.traces)
    assert [(trace.category, trace.name) for trace in result.traces] == [
        ("B", "base"),
        ("A", "new"),
        ("A", "base"),
    ]
    base_a = result.traces[-1]
    assert isinstance(base_a, BoxTraceConfig)
    assert base_a.median == 2.0
    assert base_a.outliers == [20.0]
    assert base_a.show_mean
    assert not result.traces[1].show_in_legend
    assert result.boxmode == "group"
    assert result.custom_x_ticks == {"vals": [0.0, 1.0], "text": ["B", "A"]}
    assert [trace.position for trace in result.traces] == pytest.approx([0.15, 0.85, 1.15])
    assert plot.get_legend_column(config) == "variant"
    pd.testing.assert_frame_equal(data, original)


def test_horizontal_percentile_boxes_and_category_legend() -> None:
    plot = BoxPlot(2, "Horizontal")
    result = plot.create_traces(
        _data(),
        {
            "x": "benchmark",
            "y": "ipc",
            "orientation": "horizontal",
            "quartile_method": "exclusive",
            "whisker_mode": "percentile",
            "whisker_percentiles": [10, 90],
            "point_mode": "all",
            "notched": True,
        },
    )

    first = result.traces[0]
    assert isinstance(first, BoxTraceConfig)
    assert first.orientation == "horizontal"
    assert first.point_mode == "all"
    assert first.notched
    assert first.lower_whisker < first.upper_whisker
    assert result.custom_y_ticks == {"vals": [0.0, 1.0], "text": ["A", "B"]}
    assert plot.get_legend_column({"x": "benchmark"}) == "benchmark"


def test_quartile_methods_follow_inclusive_and_exclusive_median_rules() -> None:
    values = pd.Series([1.0, 2.0, 3.0, 4.0, 20.0]).to_numpy()

    linear = _quartiles(values, "linear")
    inclusive = _quartiles(values, "inclusive")
    exclusive = _quartiles(values, "exclusive")

    assert linear == (2.0, 3.0, 4.0)
    assert inclusive == (2.0, 3.0, 4.0)
    assert exclusive == (1.5, 3.0, 12.0)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"orientation": "diagonal"}, "orientation"),
        ({"quartile_method": "unknown"}, "quartile"),
        ({"whisker_mode": "unknown"}, "whisker mode"),
        ({"point_mode": "unknown"}, "point mode"),
        ({"whisker_percentiles": [95, 5]}, "percentiles"),
        ({"whisker_multiplier": -1}, "multiplier"),
        ({"jitter": 0.75}, "jitter"),
        ({"point_position": 2}, "point position"),
        ({"box_width": 0}, "width"),
        ({"whisker_cap_width": 2}, "cap width"),
    ],
)
def test_box_trace_validation_is_explicit(change: dict[str, object], message: str) -> None:
    config: dict[str, object] = {"x": "benchmark", "y": "ipc"}
    config.update(change)

    with pytest.raises(ValueError, match=message):
        BoxPlot(1, "Invalid").create_traces(_data(), config)


def test_box_trace_rejects_missing_columns_and_bad_percentile_shape() -> None:
    plot = BoxPlot(1, "Invalid")
    with pytest.raises(ValueError, match="must exist"):
        plot.create_traces(_data(), {"x": "missing", "y": "ipc"})
    with pytest.raises(ValueError, match="two values"):
        plot.create_traces(
            _data(),
            {"x": "benchmark", "y": "ipc", "whisker_percentiles": [5]},
        )


@patch("src.web.pages.ui.plotting.types.box_plot.box_config.render")
def test_box_config_ui_delegates_with_plot_identity(mock_render: MagicMock) -> None:
    plot = BoxPlot(7, "Box")
    data = _data()
    config = {"x": "benchmark", "y": "ipc"}
    expected = copy.deepcopy(config)
    mock_render.return_value = expected

    assert plot.render_config_ui(data, config) == expected
    mock_render.assert_called_once_with(data, config, 7)
