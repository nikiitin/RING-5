"""Annotation metadata keeps native coordinates and explicit pixel translations."""

from dataclasses import replace
from copy import deepcopy
from typing import Any, Literal, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.path import Path

import ring5
from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.rendering.config_builder import _extract_annotations
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.trace_to_plotly import traces_to_plotly


@pytest.mark.parametrize("xref", ["data", "paper"])
@pytest.mark.parametrize("yref", ["data", "paper"])
@pytest.mark.parametrize("shift", [(13.0, -7.0), (-9.0, 11.0), (0.0, 0.0)])
@pytest.mark.parametrize("arrow", [False, True])
def test_pixel_shifts_translate_complete_native_annotation_at_export_dpi(
    xref: Literal["data", "paper"],
    yref: Literal["data", "paper"],
    shift: tuple[float, float],
    arrow: bool,
) -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    plain = AnnotationConfig(
        text="Measured\nvalue",
        x=0.3 if xref == "paper" else 2.0,
        y=0.4 if yref == "paper" else 3.0,
        xref=xref,
        yref=yref,
        show_arrow=arrow,
        arrow_head=2,
        font_family="DejaVu Sans Mono",
        align="right",
    )
    shifted = replace(plain, x_shift_pixels=shift[0], y_shift_pixels=shift[1])
    native = traces_to_plotly(TraceBuildResult(annotations=[shifted]))
    assert native.layout.annotations[0].xshift == (shift[0] or None)
    assert native.layout.annotations[0].yshift == (shift[1] or None)
    assert native.layout.annotations[0].font.family == plain.font_family
    assert native.layout.annotations[0].align == "right"
    assert native.layout.annotations[0].x == plain.x
    assert native.layout.annotations[0].y == plain.y

    figure, axis = plt.subplots(dpi=96)
    try:
        axis.set_xlim(0, 10)
        axis.set_ylim(0, 10)
        FigureSpecToMatplotlib._apply_annotations(FigureConfig(annotations=[plain, shifted]), axis)
        baseline, translated = (cast(Any, text) for text in axis.texts)
        assert baseline.xy == translated.xy == (plain.x, plain.y)
        assert translated.get_fontfamily() == [plain.font_family]
        assert translated._get_multialignment() == "right"
        for dpi in (96, 192):
            figure.set_dpi(dpi)
            figure.canvas.draw()
            expected = np.asarray(shift) * dpi / 96
            renderer = cast(Any, figure.canvas).get_renderer()
            base_box = baseline.get_window_extent(renderer)
            shifted_box = translated.get_window_extent(renderer)
            np.testing.assert_allclose(
                np.array(shifted_box.bounds[:2]) - base_box.bounds[:2], expected, atol=1e-9
            )
            if arrow:
                base_arrow = baseline.arrow_patch
                shifted_arrow = translated.arrow_patch
                assert base_arrow is not None and shifted_arrow is not None
                base_path = base_arrow.get_path()
                shifted_path = shifted_arrow.get_path()
                # CLOSEPOLY's dummy vertex is not drawn and remains at the origin.
                drawn = base_path.codes != Path.CLOSEPOLY
                start = base_arrow.get_transform().transform(base_path.vertices[drawn])
                end = shifted_arrow.get_transform().transform(shifted_path.vertices[drawn])
                np.testing.assert_allclose(
                    end - start, np.broadcast_to(expected, end.shape), atol=1e-9
                )
    finally:
        plt.close(figure)


def test_typed_annotations_preserve_native_metadata_and_serialization() -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    direct = AnnotationConfig(
        text="Measured",
        x=2,
        y=3,
        yref="paper",
        x_shift_pixels=-12,
        y_shift_pixels=7,
        show_arrow=True,
        arrow_head=3,
        arrow_color="red",
        font_family="monospace",
        font_size=12,
        font_color="blue",
        font_bold=True,
        align="right",
    )
    native = traces_to_plotly(TraceBuildResult(annotations=[direct]))
    original = deepcopy(native.to_plotly_json())
    extracted = _extract_annotations(native.layout)[0]
    assert direct == extracted
    assert direct.x_shift_pixels == -12 and direct.y_shift_pixels == 7
    assert direct.font_family == "monospace" and direct.font_bold
    assert direct.arrow_head == 3 and direct.arrow_color == "red"
    assert direct.align == "right"
    config = FigureConfig(annotations=[direct])
    assert FigureConfig.from_dict(config.to_dict()) == config
    assert native.to_plotly_json() == original


def test_annotation_inherits_figure_family_without_mutating_the_spec() -> None:
    annotation = AnnotationConfig(text="Measured", x=0.5, y=0.5, xref="paper", yref="paper")
    config = FigureConfig(font_family="DejaVu Serif", annotations=[annotation])
    original = config.to_dict()
    figure, axis = plt.subplots()
    try:
        FigureSpecToMatplotlib._apply_annotations(config, axis)
        assert axis.texts[0].get_fontfamily() == ["DejaVu Serif"]
        assert config.to_dict() == original
    finally:
        plt.close(figure)


@pytest.mark.parametrize("offset", [-13, 0, 13])
def test_public_stack_totals_preserve_pixel_offset_and_raw_categories(offset: int) -> None:
    # [test->req~ring5.figure.stack-totals~1]
    frame = pd.DataFrame({"category": ["a", "b"], "left": [1.0, 2.0], "right": [3.0, 4.0]})
    with ring5.Session() as session:
        plot = session.create_plot(
            "stacked_bar",
            data=frame,
            config={
                "x": "category",
                "y_columns": ["left", "right"],
                "show_totals": True,
                "net_total_format": ".0f",
                "total_offset": offset,
                "xaxis_order": ["b"],
                "xaxis_labels": {"a": "Alpha", "b": "Beta"},
            },
        )
        interactive = cast(Any, session.render(plot, engine="plotly"))
        assert [
            (ann.x, ann.y, ann.text, ann.yshift or 0) for ann in interactive.layout.annotations
        ] == [
            ("a", 4, "4", offset),
            ("b", 6, "6", offset),
        ]
        static = cast(Any, session.render(plot, engine="matplotlib"))
        axis = static.axes[0]
        static.canvas.draw()
        assert [text.get_text() for text in axis.get_xticklabels()] == ["Beta", "Alpha"]
        for annotation, x, y in zip(axis.texts, [1.0, 0.0], [4.0, 6.0], strict=True):
            assert annotation.xy == (x, y)
            anchor = annotation.xycoords.transform(annotation.xy)
            np.testing.assert_allclose(anchor - axis.transData.transform((x, y)), (0, offset))
        assert [ann.y_shift_pixels for ann in static._ring5_spec.annotations] == [offset, offset]
