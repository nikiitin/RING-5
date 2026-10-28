"""Native engines consume scientific traces and typed preparation metadata."""

from __future__ import annotations

from typing import Any, cast

from matplotlib.figure import Figure as MplFigure
from matplotlib.patches import Rectangle
import pandas as pd
import pytest

import ring5
from src.web.rendering.figure_preparation import PreparedFigure

pytestmark = pytest.mark.public_api


def _grouped_stacked_config() -> dict:
    return {
        "x": "benchmark",
        "group": "policy",
        "y_columns": ["R1", "R2"],
        "y": "R1",
        "xaxis_order": ["a", "b"],
        "group_order": ["p1", "p2"],
        "barmode": "stack",
        "category_groups": {"a": "S", "b": "S"},
        "numbered_xaxis_modes": ["Number legend"],
        "legend2_ncols": 2,
        "legend2_x": 0.6,
        "title": "",
    }


def _grouped_stacked_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["a", "a", "b", "b"],
            "policy": ["p1", "p2", "p1", "p2"],
            "R1": [1.0, 2.0, 3.0, 4.0],
            "R2": [0.5, 0.5, 0.5, 0.5],
        }
    )


def test_matplotlib_render_does_not_invoke_plotly_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matplotlib render must not build or style a Plotly figure."""
    import src.web.rendering.plot_renderer as renderer
    import src.web.rendering.plotly_figure_builder as plotly_builder

    def _boom(*_a: Any, **_k: Any) -> None:
        raise AssertionError("Plotly builder invoked during a matplotlib render")

    monkeypatch.setattr(renderer, "build_plotly_figure", _boom)
    monkeypatch.setattr(plotly_builder, "traces_to_plotly", _boom)

    with ring5.Session() as session:
        plot = session.create_plot(
            "grouped_stacked_bar",
            data=ring5.Table(_grouped_stacked_df()),
            config=_grouped_stacked_config(),
        )
        fig = session.render(plot, engine="matplotlib")
        assert isinstance(fig, MplFigure)
        assert len(fig.axes) >= 1
        assert plot.render_artifact.figure is fig
        prepared = plot.render_artifact.preparation
        assert isinstance(prepared, PreparedFigure)
        assert plot.render_artifact.preparation is prepared
        assert prepared.trace_result is not None
        assert plot.render_artifact.engine == "matplotlib"
        assert [cast(Rectangle, bar).get_height() for bar in fig.axes[0].patches] == [
            1.0,
            2.0,
            3.0,
            4.0,
            0.5,
            0.5,
            0.5,
            0.5,
        ]


def test_prepared_group_metadata_survives_both_native_engines() -> None:
    """Preserve actual values, annotation roles and native labels independently."""
    from src.web.rendering.figure_preparation import prepare_figure

    config = _grouped_stacked_config()
    data = _grouped_stacked_df()
    with ring5.Session() as session:
        plot = session.create_plot("grouped_stacked_bar", data=ring5.Table(data), config=config)
        prepared = prepare_figure(data, config, plot.plot_type, plot.create_traces)
        assert [trace.y for trace in prepared.trace_result.traces] == [
            [1.0, 2.0, 3.0, 4.0],
            [0.5, 0.5, 0.5, 0.5],
        ]
        assert prepared.spec.barmode == "stack"
        assert prepared.spec.axes.x.tick_values == [0.0, 1.0, 2.0, 3.0]
        assert not prepared.spec.axes.x.show_tick_labels
        assert [ann.text for ann in prepared.spec.annotations[:3]] == [
            "<b>a</b>",
            "<b>b</b>",
            "<b>S</b>",
        ]
        assert all(
            ann.annotation_type == "group_label" and ann.font_bold
            for ann in prepared.spec.annotations[:3]
        )
        numbered = prepared.spec.annotations[-1]
        assert numbered.annotation_type == "boxed" and numbered.legend_role == "secondary"
        assert numbered.font_family == "monospace"
        assert "1. p1" in numbered.text and "2. p2" in numbered.text

        interactive = cast(Any, session.render(plot, engine="plotly"))
        assert [ann.text for ann in interactive.layout.annotations] == [
            ann.text for ann in prepared.spec.annotations
        ]
        assert interactive.layout.annotations[-1].font.family == "monospace"
        static = cast(Any, session.render(plot, engine="matplotlib"))
        text = static.axes[0].texts
        assert [artist.get_text() for artist in text[:3]] == ["a", "b", "S"]
        assert all(artist.get_fontweight() == "bold" for artist in text[:3])
        assert text[-1].get_fontfamily() == ["monospace"]
        assert "1. p1" in text[-1].get_text() and "2. p2" in text[-1].get_text()
