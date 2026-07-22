"""Tests for validated engine-independent Sankey flow traces."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import SankeyTraceConfig
from src.web.pages.ui.plotting.types.sankey_plot import SankeyPlot


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source": ["Input", "Input", "Clean", "Clean"],
            "target": ["Clean", "Reject", "Output", "Output"],
            "amount": [8.0, 2.0, 5.0, 3.0],
            "note": ["accepted", "discarded", "first", "second"],
        }
    )


def test_sankey_aggregates_links_resolves_labels_colors_and_layout_without_mutation() -> None:
    # [test->req~ring5.plot.sankey~1]
    data = _data()
    original = data.copy(deep=True)
    result = SankeyPlot(1, "Flow").create_traces(
        data,
        {
            "sankey_source": "source",
            "sankey_target": "target",
            "sankey_value": "amount",
            "sankey_label": "note",
            "sankey_node_labels": {"Input": "Raw input"},
            "sankey_label_mode": "names_with_totals",
            "sankey_number_format": ".1f",
            "sankey_color_mode": "target",
            "sankey_show_link_labels": True,
            "color_palette": ["#111111", "#222222", "#333333", "#444444"],
        },
    )

    assert len(result.traces) == 1
    trace = result.traces[0]
    assert isinstance(trace, SankeyTraceConfig)
    assert trace.node_labels == [
        "Raw input (10.0)",
        "Clean (8.0)",
        "Reject (2.0)",
        "Output (8.0)",
    ]
    assert trace.source_indices == [0, 0, 1]
    assert trace.target_indices == [1, 2, 3]
    assert trace.values == [8.0, 2.0, 8.0]
    assert trace.link_labels == ["accepted", "discarded", "first, second"]
    assert trace.node_x == [0.0, 0.5, 0.5, 1.0]
    assert trace.link_colors == ["#222222", "#333333", "#444444"]
    assert trace.custom_data["drilldown"][-1] == {
        "source": "Clean",
        "target": "Output",
    }
    pd.testing.assert_frame_equal(data, original)


def test_sankey_fixed_positions_hidden_labels_and_uniform_color() -> None:
    trace = (
        SankeyPlot(2, "Fixed")
        .create_traces(
            _data(),
            {
                "sankey_source": "source",
                "sankey_target": "target",
                "sankey_value": "amount",
                "sankey_arrangement": "fixed",
                "sankey_node_positions": {"Clean": [0.4, 0.25]},
                "sankey_label_mode": "hidden",
                "sankey_color_mode": "uniform",
                "sankey_link_color": "#abcdef",
                "sankey_link_opacity": 0.6,
            },
        )
        .traces[0]
    )

    assert isinstance(trace, SankeyTraceConfig)
    assert trace.arrangement == "fixed"
    assert trace.node_x[1] == 0.4 and trace.node_y[1] == 0.25
    assert trace.node_labels == ["", "", "", ""]
    assert trace.link_colors == ["#abcdef"] * 3
    assert trace.link_opacity == 0.6
    assert not trace.show_node_labels
    assert SankeyPlot(2, "Fixed").get_legend_column({}) is None


@pytest.mark.parametrize(
    ("data", "change", "message"),
    [
        (_data(), {"sankey_arrangement": "stacked"}, "arrangement"),
        (_data(), {"sankey_color_mode": "random"}, "color mode"),
        (_data(), {"sankey_label_mode": "values"}, "label mode"),
        (_data(), {"sankey_link_opacity": 0}, "opacity"),
        (_data(), {"sankey_node_pad": 101}, "padding"),
        (_data(), {"sankey_node_thickness": 1}, "thickness"),
        (_data(), {"sankey_node_line_width": -1}, "border width"),
        (_data(), {"sankey_node_labels": ["bad"]}, "aliases"),
        (
            _data(),
            {
                "sankey_arrangement": "fixed",
                "sankey_node_positions": {"Clean": [2, 0]},
            },
            "between 0 and 1",
        ),
        (
            pd.DataFrame({"source": ["A", "B"], "target": ["B", "A"], "amount": [1, 1]}),
            {},
            "acyclic",
        ),
        (
            pd.DataFrame({"source": ["A"], "target": ["B"], "amount": [0]}),
            {},
            "greater than zero",
        ),
    ],
)
def test_sankey_validation_is_explicit(
    data: pd.DataFrame, change: dict[str, object], message: str
) -> None:
    config: dict[str, object] = {
        "sankey_source": "source",
        "sankey_target": "target",
        "sankey_value": "amount",
    }
    config.update(change)
    with pytest.raises(ValueError, match=message):
        SankeyPlot(1, "Invalid").create_traces(data, config)


def test_sankey_rejects_missing_columns_cells_and_non_numeric_values() -> None:
    plot = SankeyPlot(1, "Invalid")
    with pytest.raises(ValueError, match="must exist"):
        plot.create_traces(
            _data(),
            {"sankey_source": "missing", "sankey_target": "target", "sankey_value": "amount"},
        )
    with pytest.raises(ValueError, match="cannot be missing"):
        plot.create_traces(
            pd.DataFrame({"source": ["A"], "target": [None], "amount": [1]}),
            {"sankey_source": "source", "sankey_target": "target", "sankey_value": "amount"},
        )
    with pytest.raises(ValueError, match="finite numbers"):
        plot.create_traces(
            pd.DataFrame({"source": ["A"], "target": ["B"], "amount": ["many"]}),
            {"sankey_source": "source", "sankey_target": "target", "sankey_value": "amount"},
        )


@patch("src.web.pages.ui.plotting.types.sankey_plot.sankey_config.render")
def test_sankey_config_ui_delegates_with_plot_identity(mock_render: MagicMock) -> None:
    plot = SankeyPlot(7, "Flow")
    data = _data()
    config = {"sankey_source": "source", "sankey_target": "target", "sankey_value": "amount"}
    expected = copy.deepcopy(config)
    mock_render.return_value = expected

    assert plot.render_config_ui(data, config) == expected
    mock_render.assert_called_once_with(data, config, 7)
