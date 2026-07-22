"""Tests for grouped, engine-independent violin density traces."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import ViolinTraceConfig
from src.web.pages.ui.plotting.types.violin_plot import ViolinPlot


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["A"] * 7 + ["B"] * 4,
            "variant": ["base"] * 5 + ["new"] * 2 + ["base"] * 4,
            "ipc": [1.0, 1.4, 1.8, 2.2, 2.6, 2.0, 3.0, 4.0, 4.5, 5.0, 5.5],
        }
    )


def test_grouped_violin_precomputes_density_and_count_width_without_mutation() -> None:
    # [test->req~ring5.plot.violin~1]
    data = _data()
    original = data.copy(deep=True)
    result = ViolinPlot(1, "IPC density").create_traces(
        data,
        {
            "x": "benchmark",
            "y": "ipc",
            "color": "variant",
            "bandwidth_method": "silverman",
            "bandwidth_scale": 0.8,
            "density_span": "soft",
            "density_scale": "count",
            "summary_mode": "box+mean",
            "point_mode": "all",
            "xaxis_order": ["B", "A"],
            "legend_order": ["new", "base"],
            "series_styles": {"base": {"use_color": True, "color": "#336699"}},
        },
    )

    assert all(isinstance(trace, ViolinTraceConfig) for trace in result.traces)
    assert [(trace.category, trace.name) for trace in result.traces] == [
        ("B", "base"),
        ("A", "new"),
        ("A", "base"),
    ]
    base_a = result.traces[-1]
    assert isinstance(base_a, ViolinTraceConfig)
    assert len(base_a.density_coordinates) == len(base_a.density) == 128
    assert max(base_a.density) == pytest.approx(1.0)
    assert base_a.bandwidth > 0
    assert base_a.width_scale == 1.0
    assert result.traces[1].width_scale == pytest.approx(2 / 5)
    assert base_a.show_box and base_a.show_mean
    assert base_a.point_mode == "all"
    assert base_a.color == "#336699"
    assert not result.traces[1].show_in_legend
    assert result.custom_x_ticks == {"vals": [0.0, 1.0], "text": ["B", "A"]}
    assert [trace.position for trace in result.traces] == pytest.approx([0.2, 0.8, 1.2])
    pd.testing.assert_frame_equal(data, original)


def test_horizontal_half_violin_uses_hard_span_and_category_legend() -> None:
    plot = ViolinPlot(2, "Horizontal")
    result = plot.create_traces(
        _data(),
        {
            "x": "benchmark",
            "y": "ipc",
            "orientation": "horizontal",
            "density_span": "hard",
            "violin_side": "negative",
            "summary_mode": "mean",
        },
    )

    first = result.traces[0]
    assert isinstance(first, ViolinTraceConfig)
    assert first.orientation == "horizontal"
    assert first.side == "negative"
    assert min(first.density_coordinates) == min(first.values)
    assert max(first.density_coordinates) == max(first.values)
    assert not first.show_box and first.show_mean
    assert result.custom_y_ticks == {"vals": [0.0, 1.0], "text": ["A", "B"]}
    assert plot.get_legend_column({"x": "benchmark"}) == "benchmark"


def test_constant_and_singleton_distributions_have_finite_density() -> None:
    data = pd.DataFrame({"category": ["one", "flat", "flat"], "value": [0.0, 3.0, 3.0]})
    result = ViolinPlot(3, "Stable").create_traces(data, {"x": "category", "y": "value"})

    assert len(result.traces) == 2
    for trace in result.traces:
        assert isinstance(trace, ViolinTraceConfig)
        assert trace.bandwidth > 0
        assert all(value >= 0 for value in trace.density)
        assert max(trace.density) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"orientation": "diagonal"}, "orientation"),
        ({"bandwidth_method": "manual"}, "bandwidth method"),
        ({"density_span": "unknown"}, "density span"),
        ({"density_scale": "area"}, "density scale"),
        ({"violin_side": "center"}, "side"),
        ({"point_mode": "outliers"}, "point mode"),
        ({"summary_mode": "median"}, "summary mode"),
        ({"bandwidth_scale": 0}, "bandwidth scale"),
        ({"jitter": 0.75}, "jitter"),
        ({"violin_width": 0}, "width"),
    ],
)
def test_violin_validation_is_explicit(change: dict[str, object], message: str) -> None:
    config: dict[str, object] = {"x": "benchmark", "y": "ipc"}
    config.update(change)
    with pytest.raises(ValueError, match=message):
        ViolinPlot(1, "Invalid").create_traces(_data(), config)


def test_violin_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="must exist"):
        ViolinPlot(1, "Invalid").create_traces(_data(), {"x": "missing", "y": "ipc"})


@patch("src.web.pages.ui.plotting.types.violin_plot.violin_config.render")
def test_violin_config_ui_delegates_with_plot_identity(mock_render: MagicMock) -> None:
    plot = ViolinPlot(7, "Violin")
    data = _data()
    config = {"x": "benchmark", "y": "ipc"}
    expected = copy.deepcopy(config)
    mock_render.return_value = expected

    assert plot.render_config_ui(data, config) == expected
    mock_render.assert_called_once_with(data, config, 7)
