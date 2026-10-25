"""Canonical preparation owns data descriptions before native rendering."""

from copy import deepcopy
from typing import Any, Literal, cast
from unittest.mock import Mock, patch

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import ring5
from scripts.generate_example_portfolio import build_example_data, build_example_plots
from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig, TraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.figure_preparation import prepare_figure
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib


def test_all_registered_examples_prepare_once_without_constructing_native_figures() -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    plots = build_example_plots(build_example_data())
    assert len(plots) == 17
    for plot in plots:
        data = cast(pd.DataFrame, plot.processed_data)
        before = data.copy(deep=True)
        config = deepcopy(plot.config)
        callback = Mock(wraps=plot.create_traces)
        with (
            patch(
                "plotly.graph_objects.Figure", side_effect=AssertionError("native Plotly figure")
            ),
            patch("matplotlib.pyplot.subplots", side_effect=AssertionError("native MPL figure")),
            patch.object(
                ConfigSpecBuilder, "from_config", wraps=ConfigSpecBuilder.from_config
            ) as build,
            patch(
                "src.web.rendering.figure_preparation.resolve_config", wraps=resolve_config
            ) as resolve,
        ):
            prepared = prepare_figure(data, plot.config, plot.plot_type, callback)
        assert callback.call_count == build.call_count == resolve.call_count == 1
        assert prepared.trace_result.traces
        assert prepared.config == config
        assert plot.config == config
        pd.testing.assert_frame_equal(data, before)


def test_preparation_owns_callback_config_and_reusable_trace_metadata() -> None:
    # [test->req~ring5.render.engine-independent-traces~1]
    config = {"custom": {"values": ["source"]}, "legend_labels": {"raw": "Display"}}
    original = deepcopy(config)
    shared = TraceBuildResult(
        traces=[BarTraceConfig(name="raw", x=["a"], y=[2.0], custom_data={"labels": ["source"]})],
        annotations=[AnnotationConfig(text="Source")],
    )

    def callback(data: pd.DataFrame, owned: dict[str, Any]) -> TraceBuildResult:
        owned["custom"]["values"].append("callback")
        return shared

    prepared = prepare_figure(pd.DataFrame({"value": [2.0]}), config, "custom", callback)
    assert config == original
    assert prepared.config["custom"]["values"] == ["source", "callback"]
    assert prepared.trace_result.traces[0].name == "Display"
    prepared.trace_result.traces[0].custom_data["labels"].append("changed")
    prepared.trace_result.traces[0].y.append(99.0)
    prepared.trace_result.annotations.clear()
    assert shared.traces[0].name == "raw" and shared.traces[0].y == [2.0]
    assert shared.traces[0].custom_data == {"labels": ["source"]}
    assert len(shared.annotations) == len(prepared.spec.annotations) == 1


@pytest.mark.parametrize("separate", [False, True])
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_numbered_font_role_resolves_for_real_public_native_renders(
    separate: bool, engine: Literal["plotly", "matplotlib"]
) -> None:
    # [test->req~ring5.figure.numbered-xaxis~1]
    data = pd.DataFrame(
        {"bench": ["a", "b"], "group": ["G", "G"], "value": [2.0, 5.0], "right": [4.0, 10.0]}
    )
    role_prefix = "legend3_" if separate else "legend2_"
    config = {
        "x": "bench",
        "group": "group",
        "y_columns": ["value"],
        "numbered_xaxis_modes": ["Number legend"],
        "legend_font_size": 18,
        f"{role_prefix}font_size": -1,
        "dual_axis": separate,
        "unified_legend": not separate,
        "y_columns_right": ["right"],
    }
    with ring5.Session() as session:
        plot = session.create_plot("grouped_stacked_bar", data=ring5.Table(data), config=config)
        native = cast(Any, session.render(plot, engine=engine))
        if engine == "plotly":
            number = next(a for a in native.layout.annotations if a.text.startswith("1."))
            assert number.font.size == 18 and number.font.family == "monospace"
        else:
            number = next(t for t in native.axes[0].texts if t.get_text().startswith("1."))
            assert number.get_fontsize() == 18 and number.get_fontfamily() == ["monospace"]
            plt.close(native)


def test_preparation_rejects_unsupported_family_before_spec_building() -> None:
    with patch.object(ConfigSpecBuilder, "from_config", side_effect=AssertionError("style build")):
        with pytest.raises(TypeError, match="Unsupported trace type: TraceConfig"):
            prepare_figure(
                pd.DataFrame(),
                {},
                "custom",
                lambda data, config: TraceBuildResult(traces=[TraceConfig()]),
            )


def test_numbered_annotation_does_not_create_a_trace_legend_on_another_panel() -> None:
    # [test->req~ring5.figure.legends~1]
    result = TraceBuildResult(
        annotations=[AnnotationConfig(text="1. Group", font_size=10, legend_role="secondary")]
    )
    prepared = prepare_figure(pd.DataFrame(), {}, "custom", lambda data, config: result)
    figure, axes = plt.subplots(1, 2)
    try:
        axes[0].plot([0, 1], [1, 2], label="left panel")
        axes[1].plot([0, 1], [3, 4], label="right panel")
        FigureSpecToMatplotlib.apply(prepared.spec, axes[0])
        assert axes[0].get_legend() is not None
        assert axes[1].get_legend() is None
        assert [legend.role for legend in prepared.spec.legends] == ["primary"]
    finally:
        plt.close(figure)
