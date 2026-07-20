"""Tests for engine-independent waterfall semantics."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import WaterfallTraceConfig
from src.web.pages.ui.plotting.types.waterfall_plot import WaterfallPlot


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step": ["Revenue", "Costs", "Reset", "Tax", "Checkpoint", "Revenue"],
            "change": [100.0, -30.0, 80.0, -10.0, 999.0, 120.0],
        }
    )


def test_waterfall_resolves_relative_absolute_subtotal_and_total_without_mutation() -> None:
    # [test->req~ring5.plot.waterfall~1]
    data = _data()
    original = data.copy(deep=True)
    result = WaterfallPlot(1, "Bridge").create_traces(
        data,
        {
            "x": "step",
            "y": "change",
            "xaxis_order": ["Revenue", "Costs", "Reset", "Tax", "Checkpoint"],
            "waterfall_absolute": ["Reset"],
            "waterfall_subtotals": ["Checkpoint"],
            "waterfall_final_total": True,
            "waterfall_total_label": "Ending balance",
            "waterfall_number_format": ".1f",
            "waterfall_connector_color": "#123456",
            "waterfall_increasing_color": "#00aa00",
            "waterfall_decreasing_color": "#aa0000",
            "waterfall_total_color": "#0000aa",
        },
    )

    assert len(result.traces) == 1
    trace = result.traces[0]
    assert isinstance(trace, WaterfallTraceConfig)
    assert trace.categories == [
        "Revenue",
        "Costs",
        "Reset",
        "Tax",
        "Checkpoint",
        "Ending balance",
    ]
    assert trace.values == [110.0, -30.0, 80.0, -10.0, 0.0, 0.0]
    assert trace.measures == ["relative", "relative", "absolute", "relative", "total", "total"]
    assert trace.kinds == ["relative", "relative", "absolute", "relative", "subtotal", "total"]
    assert trace.starts == [0.0, 110.0, 0.0, 80.0, 0.0, 0.0]
    assert trace.ends == [110.0, 80.0, 80.0, 70.0, 70.0, 70.0]
    assert trace.value_labels == ["110.0", "-30.0", "80.0", "-10.0", "70.0", "70.0"]
    assert trace.connector_color == "#123456"
    assert trace.increasing_color == "#00aa00"
    assert trace.decreasing_color == "#aa0000"
    assert trace.total_color == "#0000aa"
    assert trace.custom_data["source_row_counts"] == [2, 1, 1, 1, 1, 6]
    assert trace.custom_data["drilldown"][-2:] == [{}, {}]
    pd.testing.assert_frame_equal(data, original)


def test_waterfall_can_hide_connectors_labels_and_final_total() -> None:
    trace = (
        WaterfallPlot(2, "Simple")
        .create_traces(
            pd.DataFrame({"step": ["A", "B"], "change": [4.0, -1.0]}),
            {
                "x": "step",
                "y": "change",
                "waterfall_final_total": False,
                "waterfall_connectors": False,
                "waterfall_show_values": False,
                "waterfall_bar_width": 0.5,
                "waterfall_opacity": 0.6,
            },
        )
        .traces[0]
    )

    assert isinstance(trace, WaterfallTraceConfig)
    assert trace.categories == ["A", "B"]
    assert not trace.connector_visible
    assert not trace.show_values
    assert trace.bar_width == 0.5
    assert trace.opacity == 0.6
    assert WaterfallPlot(2, "Simple").get_legend_column({}) is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"waterfall_absolute": ["A"], "waterfall_subtotals": ["A"]}, "both"),
        ({"waterfall_bar_width": 0}, "bar width"),
        ({"waterfall_connector_width": 0}, "connector width"),
        ({"waterfall_opacity": 0}, "opacity"),
        ({"waterfall_total_label": " "}, "total label"),
        ({"waterfall_absolute": "A"}, "list of category labels"),
    ],
)
def test_waterfall_validation_is_explicit(change: dict[str, object], message: str) -> None:
    config: dict[str, object] = {"x": "step", "y": "change"}
    config.update(change)
    with pytest.raises(ValueError, match=message):
        WaterfallPlot(1, "Invalid").create_traces(
            pd.DataFrame({"step": ["A"], "change": [1.0]}), config
        )


def test_waterfall_rejects_missing_or_non_numeric_values() -> None:
    plot = WaterfallPlot(1, "Invalid")
    with pytest.raises(ValueError, match="must exist"):
        plot.create_traces(_data(), {"x": "missing", "y": "change"})
    with pytest.raises(ValueError, match="no numeric"):
        plot.create_traces(
            pd.DataFrame({"step": ["A"], "change": ["unknown"]}),
            {"x": "step", "y": "change"},
        )


@patch("src.web.pages.ui.plotting.types.waterfall_plot.waterfall_config.render")
def test_waterfall_config_ui_delegates_with_plot_identity(mock_render: MagicMock) -> None:
    plot = WaterfallPlot(7, "Bridge")
    data = _data()
    config = {"x": "step", "y": "change"}
    expected = copy.deepcopy(config)
    mock_render.return_value = expected

    assert plot.render_config_ui(data, config) == expected
    mock_render.assert_called_once_with(data, config, 7)
