"""Explicit source/output ownership keeps whole-root heatmap reapply bounded."""

from dataclasses import replace
from typing import Literal, cast

import matplotlib.pyplot as plt
import numpy as np
import pytest

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import ColorbarConfig, LegendConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering._render_result import MatplotlibFigureResult
from src.web.rendering._matplotlib_copy import copy_matplotlib_figure
from src.web.rendering.figure_preparation import PreparedFigure
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_colorbar import _ColorbarBacklink
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer


def _spec(
    *, shared: bool = True, orientation: Literal["horizontal", "vertical"] = "vertical"
) -> FigureConfig:
    return resolve_config(
        FigureConfig(
            legends=[LegendConfig(orientation=orientation, colorbar=ColorbarConfig(shared=shared))]
        )
    )


def _native(spec: FigureConfig) -> MatplotlibFigureResult:
    sources: tuple[tuple[str, list[float | None]], ...] = (("A", [3.0, 5.0]), ("B", [7.0, 9.0]))
    result = TraceBuildResult(
        traces=[
            HeatmapTraceConfig(name=name, z=[values], col_labels=["001", "NA"], row_labels=["row"])
            for name, values in sources
        ]
    )
    return build_matplotlib_figure_from_prepared(PreparedFigure({}, result, spec))


def _positions(native: MatplotlibFigureResult) -> np.ndarray:
    return np.asarray(
        [panel.primary_axes.get_position(original=True).bounds for panel in native.panels]
    )


def _measurements(native: MatplotlibFigureResult) -> None:
    for panel, values in zip(native.panels, ([3.0, 5.0], [7.0, 9.0]), strict=True):
        assert panel.heatmap_image is not None
        np.testing.assert_array_equal(np.asarray(panel.heatmap_image.get_array()).ravel(), values)
        assert [text.get_text() for text in panel.primary_axes.get_xticklabels()] in (
            [],
            ["001", "NA"],
        )


@pytest.mark.parametrize("shared", [True, False])
def test_reapply_and_visibility_reuse_actual_outputs_without_layout_drift(shared: bool) -> None:
    spec = _spec(shared=shared)
    native = _native(spec)
    try:
        initial = _positions(native)
        outputs = native.native_outputs.colorbars
        native.figure.canvas.draw()
        for visible in (True, False, True, True):
            changed = replace(
                spec, legends=[replace(spec.legends[0], visible=visible, title="Scale")]
            )
            FigureSpecToMatplotlib.apply(changed, native)
            assert native.native_outputs.colorbars == outputs
            assert len(native.figure.axes) == 2 + len(outputs)
            assert all(output.colorbar.ax.get_visible() is visible for output in outputs)
            assert all(output.colorbar.ax.get_title() == "Scale" for output in outputs)
            np.testing.assert_allclose(_positions(native), initial)
            _measurements(native)
    finally:
        plt.close(native.figure)


def test_owned_topology_and_orientation_reversals_restore_allocation_once() -> None:
    initial_spec = _spec()
    native = _native(initial_spec)
    try:
        initial = _positions(native)
        transitions: tuple[tuple[bool, Literal["horizontal", "vertical"]], ...] = (
            (False, "vertical"),
            (True, "horizontal"),
            (False, "horizontal"),
            (True, "vertical"),
        )
        for shared, orientation in transitions:
            spec = _spec(shared=shared, orientation=orientation)
            FigureSpecToMatplotlib.apply(spec, native)
            outputs = native.native_outputs.colorbars
            positions = _positions(native)
            FigureSpecToMatplotlib.apply(spec, native)
            assert native.native_outputs.colorbars == outputs
            assert len(outputs) == (1 if shared else 2)
            assert len(native.figure.axes) == 2 + len(outputs)
            assert all(output.colorbar.orientation == orientation for output in outputs)
            np.testing.assert_allclose(_positions(native), positions)
            _measurements(native)
        np.testing.assert_allclose(_positions(native), initial)
    finally:
        plt.close(native.figure)


def test_foreign_adoption_is_preserved_and_structural_change_rejects_before_any_style() -> None:
    spec = _spec()
    native = _native(spec)
    try:
        owned = native.native_outputs.colorbars[0]
        foreign = native.figure.colorbar(owned.colorbar.mappable, ax=native.panels[1].primary_axes)
        image = owned.colorbar.mappable
        backlink = cast(_ColorbarBacklink, image)
        foreign_callback = backlink.colorbar_cid
        FigureSpecToMatplotlib.apply(spec, native)
        assert image.colorbar is foreign and backlink.colorbar_cid == foreign_callback
        before = _positions(native)
        title = native.panels[0].primary_axes.get_title()
        with pytest.raises(ValueError, match="ownership changed"):
            FigureSpecToMatplotlib.apply(replace(_spec(shared=False), title="Changed"), native)
        assert native.panels[0].primary_axes.get_title() == title
        assert image.colorbar is foreign and backlink.colorbar_cid == foreign_callback
        assert foreign_callback in image.callbacks.callbacks["changed"]
        assert any(axes is foreign.ax for axes in native.figure.axes)
        np.testing.assert_array_equal(_positions(native), before)
        _measurements(native)
    finally:
        plt.close(native.figure)


def test_foreign_layout_edit_requires_fresh_context_before_structural_change() -> None:
    native = _native(_spec())
    try:
        axes = native.panels[0].primary_axes
        axes.set_position((0.2, 0.2, 0.3, 0.3))
        before = _positions(native)
        with pytest.raises(ValueError, match="layout changed"):
            FigureSpecToMatplotlib.apply(_spec(orientation="horizontal"), native)
        np.testing.assert_array_equal(_positions(native), before)
        assert len(native.figure.axes) == 3
        _measurements(native)
    finally:
        plt.close(native.figure)


def test_foreign_colorbar_subplotspec_cannot_redirect_owned_structural_teardown() -> None:
    native = _native(_spec())
    try:
        output = native.native_outputs.colorbars[0]
        foreign = native.figure.add_subplot(3, 1, 3)
        foreign_parent = foreign.get_subplotspec()
        assert foreign_parent is not None
        output.colorbar.ax.set_subplotspec(foreign_parent)
        positions = _positions(native)
        with pytest.raises(ValueError, match="ownership changed"):
            FigureSpecToMatplotlib.apply(_spec(orientation="horizontal"), native)
        assert output.colorbar.ax.get_subplotspec() is foreign_parent
        np.testing.assert_array_equal(_positions(native), positions)
        assert len(native.figure.axes) == 4
        _measurements(native)
    finally:
        plt.close(native.figure)


@pytest.mark.parametrize("automatic", [True, False])
def test_structural_reapply_supports_actual_manual_and_automatic_native_layout(
    automatic: bool,
) -> None:
    figure = plt.figure(layout="constrained" if automatic else None)
    axes = figure.add_subplot() if automatic else figure.add_axes((0.2, 0.2, 0.6, 0.6))
    panel = MatplotlibTraceRenderer.render(
        [
            HeatmapTraceConfig(
                name="A", z=[[3.0, 5.0]], col_labels=["001", "NA"], row_labels=["row"]
            )
        ],
        axes,
    )
    native = MatplotlibFigureResult(figure, (panel,))
    try:
        spec = _spec()
        FigureSpecToMatplotlib.apply(spec, native, apply_margins=False)
        figure.canvas.draw()
        for orientation in ("horizontal", "vertical"):
            changed = replace(spec, legends=[replace(spec.legends[0], orientation=orientation)])
            FigureSpecToMatplotlib.apply(changed, native, apply_margins=False)
            figure.canvas.draw()
            output = native.native_outputs.colorbars[0]
            assert output.colorbar.orientation == orientation
            if automatic:
                assert axes.get_in_layout() is True
            assert len(figure.axes) == 2
            assert panel.heatmap_image is not None
            np.testing.assert_array_equal(
                np.asarray(panel.heatmap_image.get_array()).ravel(), [3.0, 5.0]
            )
    finally:
        plt.close(figure)


def test_foreign_automatic_layout_opt_out_rejects_before_structural_reapply() -> None:
    figure = plt.figure(layout="constrained")
    axes = figure.add_subplot()
    panel = MatplotlibTraceRenderer.render(
        [
            HeatmapTraceConfig(
                name="A", z=[[3.0, 5.0]], col_labels=["001", "NA"], row_labels=["row"]
            )
        ],
        axes,
    )
    native = MatplotlibFigureResult(figure, (panel,))
    try:
        FigureSpecToMatplotlib.apply(_spec(), native, apply_margins=False)
        figure.canvas.draw()
        axes.set_position((0.2, 0.2, 0.3, 0.3))
        assert axes.get_in_layout() is False
        before = axes.get_position(original=True).bounds
        with pytest.raises(ValueError, match="layout changed"):
            FigureSpecToMatplotlib.apply(
                _spec(orientation="horizontal"), native, apply_margins=False
            )
        np.testing.assert_array_equal(axes.get_position(original=True).bounds, before)
        assert axes.get_in_layout() is False
        assert len(figure.axes) == 2
        assert panel.heatmap_image is not None
        np.testing.assert_array_equal(
            np.asarray(panel.heatmap_image.get_array()).ravel(), [3.0, 5.0]
        )
    finally:
        plt.close(figure)


def test_initially_hidden_colorbar_allocates_only_when_explicitly_shown() -> None:
    shown = _spec()
    hidden = replace(shown, legends=[replace(shown.legends[0], visible=False)])
    native = _native(hidden)
    try:
        assert len(native.figure.axes) == 2
        assert native.native_outputs.colorbars == ()
        FigureSpecToMatplotlib.apply(shown, native)
        assert len(native.figure.axes) == 3
        assert len(native.native_outputs.colorbars) == 1
        _measurements(native)
    finally:
        plt.close(native.figure)


def test_initially_hidden_source_cannot_overwrite_a_foreign_colorbar_when_shown() -> None:
    shown = _spec()
    native = _native(replace(shown, legends=[replace(shown.legends[0], visible=False)]))
    try:
        image = native.panels[-1].heatmap_image
        assert image is not None
        foreign = native.figure.colorbar(image, ax=native.panels[-1].primary_axes)
        backlink = cast(_ColorbarBacklink, image)
        callback = backlink.colorbar_cid
        positions = _positions(native)
        title = native.panels[0].primary_axes.get_title()
        with pytest.raises(ValueError, match="ownership changed"):
            FigureSpecToMatplotlib.apply(replace(shown, title="Changed"), native)
        assert native.native_outputs.colorbars == ()
        assert image.colorbar is foreign and backlink.colorbar_cid == callback
        assert callback in image.callbacks.callbacks["changed"]
        assert native.panels[0].primary_axes.get_title() == title
        assert len(native.figure.axes) == 3
        np.testing.assert_array_equal(_positions(native), positions)
        _measurements(native)
    finally:
        plt.close(native.figure)


def test_native_export_copy_keeps_final_geometry_without_source_binding_context() -> None:
    spec = _spec()
    native = _native(spec)
    copied = None
    try:
        FigureSpecToMatplotlib.apply(_spec(orientation="horizontal"), native)
        FigureSpecToMatplotlib.apply(spec, native)
        native.figure.canvas.draw()
        copied = copy_matplotlib_figure(native.figure)
        assert len(copied.axes) == len(native.figure.axes) == 3
        for original, clone in zip(native.figure.axes, copied.axes, strict=True):
            assert original is not clone
            np.testing.assert_array_equal(
                original.get_position(original=True).bounds,
                clone.get_position(original=True).bounds,
            )
            assert original.get_title() == clone.get_title()
        for panel, clone in zip(native.panels, copied.axes[:2], strict=True):
            assert panel.heatmap_image is not None
            np.testing.assert_array_equal(
                np.asarray(panel.heatmap_image.get_array()),
                np.asarray(clone.collections[0].get_array()),
            )
        _measurements(native)
    finally:
        plt.close(native.figure)
        if copied is not None:
            plt.close(copied)
