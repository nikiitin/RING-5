"""Tests for ordered, encoded parallel-coordinate traces."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import ParallelCoordinatesTraceConfig
from src.web.pages.ui.plotting.types.parallel_coordinates_plot import ParallelCoordinatesPlot


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "profile": ["base", "tuned", "base"],
            "ipc": [1.0, 2.0, 1.5],
            "power": [10.0, 20.0, 15.0],
            "cores": [2, 4, 8],
        }
    )


def test_parallel_coordinates_preserve_order_encoding_ranges_and_brushes() -> None:
    # [test->req~ring5.plot.parallel-coordinates~1]
    data = _data()
    original = data.copy(deep=True)
    result = ParallelCoordinatesPlot(1, "Profiles").create_traces(
        data,
        {
            "parallel_dimensions": ["power", "profile", "ipc"],
            "parallel_color": "profile",
            "parallel_labels": {"profile": "Configuration"},
            "parallel_range_mode": "zero",
            "parallel_ranges": {"power": [0, 25]},
            "parallel_brushes": {"ipc": [1.2, 2.0]},
            "parallel_colorscale": "Cividis",
            "parallel_reverse_colorscale": True,
            "parallel_unselected_opacity": 0.12,
        },
    )

    assert len(result.traces) == 1
    trace = result.traces[0]
    assert isinstance(trace, ParallelCoordinatesTraceConfig)
    assert [dimension.column for dimension in trace.dimensions] == ["power", "profile", "ipc"]
    assert [dimension.label for dimension in trace.dimensions] == [
        "power",
        "Configuration",
        "ipc",
    ]
    assert trace.dimensions[0].range == (0.0, 25.0)
    assert trace.dimensions[1].values == [0.0, 1.0, 0.0]
    assert trace.dimensions[1].tick_labels == ["base", "tuned"]
    assert trace.dimensions[2].constraintrange == (1.2, 2.0)
    assert trace.line_color_values == [0.0, 1.0, 0.0]
    assert trace.color_tick_labels == ["base", "tuned"]
    assert trace.colorscale == "Cividis" and trace.reverse_colorscale
    assert trace.unselected_opacity == 0.12
    assert len(trace.custom_data["drilldown"]) == 3
    assert (
        ParallelCoordinatesPlot(1, "Profiles").get_legend_column({"parallel_color": "profile"})
        == "profile"
    )
    pd.testing.assert_frame_equal(data, original)


def test_parallel_coordinates_support_uniform_color_and_single_category_axis() -> None:
    data = pd.DataFrame({"kind": ["same", "same"], "x": [1.0, 2.0]})
    trace = (
        ParallelCoordinatesPlot(2, "Uniform")
        .create_traces(
            data,
            {
                "parallel_dimensions": ["kind", "x"],
                "parallel_line_color": "#abcdef",
                "parallel_show_colorbar": False,
            },
        )
        .traces[0]
    )

    assert isinstance(trace, ParallelCoordinatesTraceConfig)
    assert trace.dimensions[0].range == (-0.5, 0.5)
    assert trace.line_color_values is None
    assert trace.line_color == "#abcdef"
    assert not trace.show_colorbar
    assert ParallelCoordinatesPlot(2, "Uniform").get_legend_column({}) is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"parallel_dimensions": ["ipc"]}, "at least two"),
        ({"parallel_dimensions": ["ipc", "ipc"]}, "unique"),
        ({"parallel_range_mode": "shared"}, "range mode"),
        ({"parallel_ranges": []}, "must map"),
        ({"parallel_ranges": {"ipc": [2, 1]}}, "maximum"),
        ({"parallel_brushes": {"ipc": [1]}}, "minimum and maximum"),
        ({"parallel_brush_dimension": "missing"}, "brush dimension"),
        ({"parallel_labels": {"ipc": 3}}, "map to strings"),
        ({"parallel_colorscale": "Rainbow"}, "color scale"),
        ({"parallel_unselected_opacity": 2}, "opacity"),
        (
            {
                "parallel_color": "ipc",
                "parallel_color_min": 2,
                "parallel_color_max": 1,
            },
            "color maximum",
        ),
    ],
)
def test_parallel_coordinate_validation_is_explicit(
    change: dict[str, object], message: str
) -> None:
    config: dict[str, object] = {"parallel_dimensions": ["profile", "ipc"]}
    config.update(change)
    with pytest.raises(ValueError, match=message):
        ParallelCoordinatesPlot(1, "Invalid").create_traces(_data(), config)


def test_parallel_coordinates_reject_missing_columns_cells_and_infinite_values() -> None:
    plot = ParallelCoordinatesPlot(1, "Invalid")
    with pytest.raises(ValueError, match="must exist"):
        plot.create_traces(_data(), {"parallel_dimensions": ["profile", "missing"]})
    with pytest.raises(ValueError, match="cannot be missing"):
        plot.create_traces(
            pd.DataFrame({"a": [1, None], "b": [2, 3]}),
            {"parallel_dimensions": ["a", "b"]},
        )
    with pytest.raises(ValueError, match="finite"):
        plot.create_traces(
            pd.DataFrame({"a": [1.0, float("inf")], "b": [2.0, 3.0]}),
            {"parallel_dimensions": ["a", "b"]},
        )


@patch(
    "src.web.pages.ui.plotting.types.parallel_coordinates_plot.parallel_coordinates_config.render"
)
def test_parallel_coordinates_config_ui_delegates_with_plot_identity(
    mock_render: MagicMock,
) -> None:
    plot = ParallelCoordinatesPlot(7, "Profiles")
    data = _data()
    config = {"parallel_dimensions": ["profile", "ipc"]}
    expected = copy.deepcopy(config)
    mock_render.return_value = expected

    assert plot.render_config_ui(data, config) == expected
    mock_render.assert_called_once_with(data, config, 7)
