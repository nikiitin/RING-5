"""Engine isolation: the matplotlib render path must be independent of Plotly.

Two guarantees are pinned here:

1. A matplotlib render never invokes the Plotly builder (``traces_to_plotly`` /
   ``StyleApplicator.apply_styles``) — they are sabotaged and the render still succeeds.
2. The Plotly-free spec enrichment (``enrich_from_traces``) produces the *same*
   ``FigureConfig`` data (barmode, x tick vals/labels, annotations) that the old
   plotly-round-trip enrichment (``enrich_from_plotly``) produced — so moving the
   matplotlib path off Plotly cannot change a rendered figure.
"""

from __future__ import annotations

import pandas as pd

import ring5


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
        "grouped_stacked_bar", data=_grouped_stacked_df(), config=_grouped_stacked_config()
    )
    fig = sess.render(plot, engine="matplotlib")

    assert fig is not None
    assert len(fig.axes) >= 1
    # The Plotly figure must not have been cached as a side effect.
    assert plot.last_generated_fig is None
    # The engine-agnostic traces are still recorded (the matplotlib path needs them).
    assert plot.last_traces is not None


def test_enrich_from_traces_matches_enrich_from_plotly():
    """The Plotly-free enrichment yields the same spec as the plotly round-trip."""
    from src.core.services.visualization.config_resolver import resolve_config
    from src.web.rendering.config_builder import (
        ConfigSpecBuilder,
        PlotlyFigureSpecBuilder,
        enrich_from_traces,
    )
    from src.web.rendering.trace_to_plotly import traces_to_plotly

    config = _grouped_stacked_config()
    df = _grouped_stacked_df()

    sess = ring5.Session()
    plot = sess.create_plot("grouped_stacked_bar", data=df, config=config)
    result = plot.create_traces(df, config)

    # Direct (Plotly-free) path.
    spec_direct = resolve_config(
        _enrich_traces(ConfigSpecBuilder, config, result, enrich_from_traces)
    )

    # Plotly round-trip path (what the web app / old headless path used).
    plotly_fig = plot.apply_common_layout(traces_to_plotly(result), config)
    spec_plotly = ConfigSpecBuilder.from_config(config, "grouped_stacked_bar")
    PlotlyFigureSpecBuilder.enrich_from_plotly(spec_plotly, plotly_fig)
    spec_plotly = resolve_config(spec_plotly)

    assert spec_direct.barmode == spec_plotly.barmode
    assert spec_direct.axes.x.tick_values == spec_plotly.axes.x.tick_values
    assert spec_direct.axes.x.tick_text == spec_plotly.axes.x.tick_text
    assert spec_direct.annotations == spec_plotly.annotations


def _enrich_traces(builder, config, result, enrich):
    spec = builder.from_config(config, "grouped_stacked_bar")
    enrich(spec, result)
    return spec
