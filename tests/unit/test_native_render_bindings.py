"""Whole-root binding admission precedes every native style or label mutation."""

from dataclasses import replace
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import pytest
from matplotlib.colors import to_rgba
from matplotlib.axes import Axes
from matplotlib.container import BarContainer

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import LegendConfig
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering._render_result import (
    MatplotlibFigureResult,
    MatplotlibRenderResult,
    MatplotlibTraceBinding,
    PlotlyRenderResult,
    PlotlyTraceBinding,
    PlotlyLayoutRole,
)
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.plotly_connector import FigureSpecToPlotly
from src.web.rendering.trace_to_plotly import traces_to_plotly


def _spec() -> FigureConfig:
    return resolve_config(
        FigureConfig(
            title="After",
            legends=[LegendConfig()],
            legend_labels={"A": "Shown"},
            trace_overrides={"A": SeriesStyleConfig(color="red", marker_size=0, line_width=0)},
        )
    )


def _panel(axes: Axes, name: str = "A") -> MatplotlibRenderResult:
    bars = axes.bar([0.0, 1.0], [3.0, 5.0], color="blue", label=name)
    return MatplotlibRenderResult(
        axes,
        bindings=(
            MatplotlibTraceBinding(
                0, name, axes, "primary", "", True, "bar", (bars,), (bars,), bars
            ),
        ),
    )


def test_plotly_foreign_data_fails_before_any_valid_source_is_mutated() -> None:
    figure = go.Figure(go.Bar(name="A", x=[0.0, 1.0], y=[3.0, 5.0], marker_color="blue"))
    rendered = PlotlyRenderResult(
        figure, ((PlotlyTraceBinding(0, "A", figure.data[0], "primary", "", True),),)
    )
    figure.add_trace(go.Bar(name="foreign", x=[0.0], y=[7.0]))
    before = figure.to_plotly_json()
    with pytest.raises(ValueError, match="membership"):
        FigureSpecToPlotly.apply(_spec(), rendered)
    assert figure.to_plotly_json() == before


def test_matplotlib_later_panel_failure_precedes_earlier_panel_mutation() -> None:
    figure, axes = plt.subplots(1, 2)
    panels = (_panel(axes[0]), _panel(axes[1], "B"))
    rendered = MatplotlibFigureResult(figure, panels)
    first = panels[0].bindings[0].legend_handle
    assert isinstance(first, BarContainer)
    panels[1].bindings[0].owned_data[0].get_children()[0].remove()
    with pytest.raises(ValueError, match="attached"):
        FigureSpecToMatplotlib.apply(_spec(), rendered)
    assert axes[0].get_title() == ""
    assert tuple(first.patches[0].get_facecolor()) == to_rgba("blue")
    plt.close(figure)


@pytest.mark.parametrize("invalid", ["ordinal", "shared", "subset", "family"])
def test_matplotlib_invalid_associations_are_rejected_before_styling(invalid: str) -> None:
    figure, axes = plt.subplots()
    panel = _panel(axes)
    original = panel.bindings[0]
    rendered = MatplotlibFigureResult(figure, (panel,))
    if invalid == "ordinal":
        panel.bindings = (replace(original, source_ordinal=1),)
    elif invalid == "shared":
        panel.bindings = (original, replace(original, source_ordinal=1))
    elif invalid == "subset":
        decoration = axes.plot([0.0, 1.0], [7.0, 9.0], color="black")[0]
        panel.bindings = (replace(original, style_targets=(decoration,)),)
    else:
        panel.bindings = (replace(original, family="line"),)
    with pytest.raises(ValueError):
        FigureSpecToMatplotlib.apply(_spec(), rendered)
    assert axes.get_title() == ""
    assert isinstance(original.owned_data[0], BarContainer)
    assert tuple(original.owned_data[0].patches[0].get_facecolor()) == to_rgba("blue")
    plt.close(figure)


def test_unowned_matplotlib_decorations_and_foreign_figure_legends_are_preserved() -> None:
    figure, axes = plt.subplots()
    panel = _panel(axes)
    decoration = axes.plot([0.0, 1.0], [7.0, 9.0], color="black", label="A")[0]
    foreign = figure.legend([decoration], ["External"])
    rendered = MatplotlibFigureResult(figure, (panel,), shared_legend=True)
    FigureSpecToMatplotlib.apply(_spec(), rendered)
    first_owned = rendered.native_outputs.legend
    FigureSpecToMatplotlib.apply(_spec(), rendered)
    assert decoration.get_color() == "black"
    assert any(foreign is legend for legend in figure.legends)
    assert all(legend is not first_owned for legend in figure.legends)
    assert len(figure.legends) == 2
    assert rendered.native_outputs.legend is not None
    assert [text.get_text() for text in rendered.native_outputs.legend.texts] == ["Shown"]
    plt.close(figure)


def _heatmaps() -> PlotlyRenderResult:
    return traces_to_plotly(
        TraceBuildResult(
            traces=[
                HeatmapTraceConfig(
                    name="source_A", z=[[3.0, 5.0]], col_labels=["x", "y"], row_labels=["row"]
                ),
                HeatmapTraceConfig(
                    name="source_B", z=[[7.0, 9.0]], col_labels=["x", "y"], row_labels=["row"]
                ),
            ]
        )
    )


def _heatmap_names(figure: go.Figure) -> list[str]:
    names = []
    for trace in figure.data:
        assert isinstance(trace, go.Heatmap) and isinstance(trace.name, str)
        names.append(trace.name)
    return names


def test_generated_roles_survive_native_reconstruction_without_source_text_in_role_name() -> None:
    rendered = _heatmaps()
    figure = rendered.figure
    figure.add_annotation(text="Shown", x=0.0, y=0.0)
    figure.update_layout(annotations=list(figure.layout.annotations))
    figure.layout.annotations = tuple(reversed(figure.layout.annotations))
    spec = resolve_config(FigureConfig(legend_labels={"source_A": "Shown", "source_B": "Shown"}))
    FigureSpecToPlotly.apply(spec, rendered)
    FigureSpecToPlotly.apply(spec, rendered)
    assert _heatmap_names(figure) == ["Shown", "Shown"]
    for trace, values in zip(figure.data, ([[3.0, 5.0]], [[7.0, 9.0]]), strict=True):
        assert isinstance(trace, go.Heatmap)
        np.testing.assert_array_equal(np.asarray(trace.z), values)
    assert all(
        "source" not in role.role_name and "Shown" not in role.role_name
        for role in rendered.layout_roles
    )
    assert (
        len(
            [
                annotation
                for annotation in figure.layout.annotations
                if annotation.name is None and annotation.text == "Shown"
            ]
        )
        == 1
    )
    assert {
        annotation.text for annotation in figure.layout.annotations if annotation.name is not None
    } == {"Shown"}


@pytest.mark.parametrize("invalid", ["missing", "duplicate"])
def test_generated_role_failure_precedes_any_native_style_change(invalid: str) -> None:
    rendered = _heatmaps()
    figure = rendered.figure
    role = rendered.layout_roles[0].role_name
    title = next(annotation for annotation in figure.layout.annotations if annotation.name == role)
    if invalid == "duplicate":
        figure.add_annotation(title.to_plotly_json())
    else:
        figure.layout.annotations = tuple(
            annotation for annotation in figure.layout.annotations if annotation.name != role
        )
    before = figure.to_plotly_json()
    with pytest.raises(ValueError, match="role membership"):
        FigureSpecToPlotly.apply(_spec(), rendered)
    assert figure.to_plotly_json() == before


def test_native_figure_copy_requires_new_explicit_handle_associations() -> None:
    original = _heatmaps()
    copied = go.Figure(original.figure)
    with pytest.raises(ValueError, match="data membership"):
        PlotlyRenderResult(copied, original.panel_bindings, original.layout_roles)
    assert _heatmap_names(copied) == ["source_A", "source_B"]


def test_owned_copy_uses_explicit_associations_without_reverse_guessing_display_text() -> None:
    original = _heatmaps()
    FigureSpecToPlotly.apply(
        resolve_config(FigureConfig(legend_labels={"source_A": "Same", "source_B": "Same"})),
        original,
    )
    copied = go.Figure(original.figure)
    bindings = tuple(
        replace(source, native_trace=copied.data[index])
        for index, source in enumerate(original.panel_bindings[0])
    )
    transferred = PlotlyRenderResult(
        copied,
        (bindings,),
        tuple(
            PlotlyLayoutRole(role.role_name, bindings[role.source.source_ordinal])
            for role in original.layout_roles
        ),
    )
    FigureSpecToPlotly.apply(
        resolve_config(FigureConfig(legend_labels={"source_A": "First", "source_B": "Second"})),
        transferred,
    )
    assert _heatmap_names(copied) == ["First", "Second"]
    assert _heatmap_names(original.figure) == ["Same", "Same"]
    assert [binding.original_name for binding in bindings] == ["source_A", "source_B"]


def test_typed_display_name_is_retired_at_constructor_and_codec() -> None:
    with pytest.raises(TypeError, match="display_name"):
        invalid: Any = {"display_name": "Shown"}
        SeriesStyleConfig(**invalid)
    with pytest.raises(ValueError, match="Use legend_labels"):
        SeriesStyleConfig.from_dict({"display_name": "Shown"})
    with pytest.raises(ValueError, match="Use legend_labels"):
        FigureConfig.from_dict({"trace_overrides": {"A": {"display_name": "Shown"}}})


def test_shared_plotly_entries_do_not_equate_data_mapped_marker_colors() -> None:
    figure = go.Figure(
        [
            go.Scatter(
                name="A",
                x=[0.0, 1.0],
                y=[3.0, 5.0],
                marker={"color": [1.0, 2.0], "colorscale": scale},
            )
            for scale in ("Viridis", "Plasma")
        ]
    )
    native = PlotlyRenderResult(
        figure,
        tuple((PlotlyTraceBinding(0, "A", trace, "primary", "", True),) for trace in figure.data),
        shared_legend=True,
    )
    FigureSpecToPlotly.apply(resolve_config(FigureConfig(legend_labels={"A": "Same"})), native)
    for trace in figure.data:
        assert isinstance(trace, go.Scatter)
        assert trace.name == "Same" and trace.showlegend is True
        np.testing.assert_array_equal(np.asarray(trace.y), [3.0, 5.0])
        np.testing.assert_array_equal(np.asarray(trace.marker.color), [1.0, 2.0])


def test_shared_matplotlib_entries_keep_unknown_data_mapped_swatches_separate() -> None:
    figure, axes = plt.subplots(1, 2)
    panels = []
    for axis, cmap in zip(axes, ("viridis", "plasma"), strict=True):
        points = axis.scatter([0.0, 1.0], [3.0, 5.0], c=[1.0, 2.0], cmap=cmap)
        panels.append(
            MatplotlibRenderResult(
                axis,
                bindings=(
                    MatplotlibTraceBinding(
                        0, "A", axis, "primary", "", True, "scatter", (points,), (points,), points
                    ),
                ),
            )
        )
    native = MatplotlibFigureResult(figure, tuple(panels), shared_legend=True)
    try:
        FigureSpecToMatplotlib.apply(
            resolve_config(FigureConfig(legends=[LegendConfig()], legend_labels={"A": "Same"})),
            native,
        )
        owned = native.native_outputs.legend
        assert owned is not None
        assert [text.get_text() for text in owned.texts] == ["Same", "Same"]
        for panel in panels:
            collection = panel.primary_axes.collections[0]
            np.testing.assert_array_equal(
                np.asarray(collection.get_offsets()), [[0.0, 3.0], [1.0, 5.0]]
            )
            np.testing.assert_array_equal(np.asarray(collection.get_array()), [1.0, 2.0])
    finally:
        plt.close(figure)
