"""Native engines consume scientific traces and typed preparation metadata."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
import pytest

import ring5

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


def test_matplotlib_render_does_not_invoke_plotly_builder(monkeypatch):
    """A matplotlib render must not build or style a Plotly figure."""
    import src.web.pages.ui.plotting.styles.applicator as appl
    import src.web.rendering.trace_to_plotly as ttp

    def _boom(*_a, **_k):
        raise AssertionError("Plotly builder invoked during a matplotlib render")

    monkeypatch.setattr(ttp, "traces_to_plotly", _boom)
    monkeypatch.setattr(appl.StyleApplicator, "apply_styles", _boom)

    sess = ring5.Session()
    plot = sess.create_plot(
        "grouped_stacked_bar",
        data=ring5.Table(_grouped_stacked_df()),
        config=_grouped_stacked_config(),
    )
    fig = sess.render(plot, engine="matplotlib")

    assert fig is not None
    assert len(fig.axes) >= 1
    assert plot.last_generated_fig is fig
    assert plot.last_figure_spec is fig._ring5_spec
    # The engine-agnostic traces are still recorded (the matplotlib path needs them).
    assert plot.last_traces is not None


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
