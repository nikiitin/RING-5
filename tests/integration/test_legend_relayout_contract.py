"""Native Plotly legend events retain canonical configuration through public replay."""

from pathlib import Path
from typing import Any, Literal, cast

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import ring5
from src.core.common.plot_payload import validate_plot_config_keys
from src.web.rendering.relayout import update_config_from_relayout


@pytest.mark.parametrize("tier", ["legend", "legend2", "legend3"])
@pytest.mark.parametrize("anchor_first", [False, True])
def test_explicit_wire_anchors_win_over_drag_defaults_in_any_payload_order(
    tier: str, anchor_first: bool
) -> None:
    positions: list[tuple[str, Any]] = [(f"{tier}.x", 0.3), (f"{tier}.y", 0.7)]
    anchors: list[tuple[str, Any]] = [(f"{tier}.xanchor", "right"), (f"{tier}.yanchor", "bottom")]
    wire = dict(anchors + positions if anchor_first else positions + anchors)
    original = {"plugin": {"label": "retained"}, "range_x": [0.0, 2.0]}
    updated, changed = update_config_from_relayout(original, wire)
    assert changed
    assert updated[f"{tier}_anchor_x"] == "right"
    assert updated[f"{tier}_anchor_y"] == "bottom"
    assert updated[f"{tier}_x"] == 0.3
    assert updated[f"{tier}_y"] == 0.7
    validate_plot_config_keys(updated)
    assert original == {"plugin": {"label": "retained"}, "range_x": [0.0, 2.0]}
    again, changed = update_config_from_relayout(updated, wire)
    assert not changed
    assert again == updated


@pytest.mark.parametrize("tier", ["legend", "legend2", "legend3"])
def test_unchanged_position_preserves_anchor_and_unknown_events_do_not_change_config(
    tier: str,
) -> None:
    config = {f"{tier}_x": 0.3, f"{tier}_anchor_x": "right", "plugin_setting": "retained"}
    unchanged, changed = update_config_from_relayout(
        config,
        {
            f"{tier}.x": 0.3,
            f"{tier}.unknown": "ignored",
            "some_other_key": 42,
            "some.other.xanchor": "left",
        },
    )
    assert not changed
    assert unchanged == config


def _assert_native(figure: Any, engine: str, tier: str, explicit: bool) -> None:
    anchor_x, anchor_y = ("right", "bottom") if explicit else ("left", "top")
    if engine == "plotly":
        if tier == "legend3":
            number = next(ann for ann in figure.layout.annotations if ann.text.startswith("1."))
            assert (number.x, number.y, number.xanchor, number.yanchor) == (
                0.3,
                0.7,
                anchor_x,
                anchor_y,
            )
        else:
            legend = getattr(figure.layout, tier)
            assert (legend.x, legend.y, legend.xanchor, legend.yanchor) == (
                0.3,
                0.7,
                anchor_x,
                anchor_y,
            )
        bars = [trace for trace in figure.data if trace.type == "bar"]
        assert [list(trace.y) for trace in bars] == [[3.0, 4.0], [5.0, 6.0]]
    else:
        left = figure.axes[0]
        if tier == "legend3":
            number = next(text for text in left.texts if text.get_text().startswith("1."))
            assert number.xy == (0.3, 0.7)
            assert number.get_horizontalalignment() == anchor_x
            assert number.get_verticalalignment() == anchor_y
        else:
            target = left if tier == "legend" else left._ring5_twin
            legend = target.get_legend()
            assert legend is not None
            assert legend._loc == (4 if explicit else 2)
            expected = target.transAxes.transform((0.3, 0.7))
            assert legend.get_bbox_to_anchor().bounds[:2] == pytest.approx(expected)
        assert [bar.get_height() for bar in left.patches] == [3.0, 4.0]
        assert [bar.get_height() for bar in left._ring5_twin.patches] == [5.0, 6.0]


@pytest.mark.public_api
@pytest.mark.parametrize("tier", ["legend", "legend2", "legend3"])
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("route", ["direct", "portfolio", "recipe"])
@pytest.mark.parametrize("explicit", [False, True])
def test_real_legend_wire_events_rerender_and_replay_with_canonical_owned_config(
    tier: str,
    engine: Literal["plotly", "matplotlib"],
    route: str,
    explicit: bool,
    tmp_path: Path,
    portfolios_dir: Path,
) -> None:
    # [test->req~ring5.figure.interactive-editing~1]
    source = tmp_path / "source.csv"
    pd.DataFrame(
        {"x": ["a", "b"], "group": ["G", "G"], "left": [3.0, 4.0], "right": [5.0, 6.0]}
    ).to_csv(source, index=False)
    config = {
        "x": "x",
        "group": "group",
        "y_columns": ["left"],
        "y_columns_right": ["right"],
        "dual_axis": True,
        "unified_legend": False,
        "numbered_xaxis_modes": ["Number legend"],
        "plugin_setting": {"label": "retained"},
    }
    with ring5.Session() as session:
        data = session.load(str(source))
        plot = session.create_plot("grouped_stacked_bar", data=data, config=config, name="Measured")
        previous = session.render(plot, engine="plotly")
        wire: dict[str, Any] = {f"{tier}.x": 0.3, f"{tier}.y": 0.7}
        if explicit:
            wire.update({f"{tier}.xanchor": "right", f"{tier}.yanchor": "bottom"})
        assert plot.update_from_relayout(wire)
        assert plot.last_generated_fig is None
        assert cast(Any, previous).data
        assert plot.config[f"{tier}_anchor_x"] == ("right" if explicit else "left")
        assert plot.config[f"{tier}_anchor_y"] == ("bottom" if explicit else "top")
        assert plot.config["plugin_setting"] == {"label": "retained"}
        validate_plot_config_keys(plot.config)
        if route == "portfolio":
            session.save_portfolio("Dragged")
            report = session.load_portfolio("Dragged")
            assert report.plots_restored == 1
            plot = session.plots[0]
        elif route == "recipe":
            recipe = session.capture_analysis_recipe("Dragged")
            payload = session.export_analysis_recipe(recipe)
            from src.core.services.data_services.analysis_recipe_service import (
                AnalysisRecipeService,
            )

            restored = AnalysisRecipeService.loads(payload)
            assert restored.plots[0].config == recipe.plots[0].config
            materialized = session.materialize_analysis_recipe(restored)
            session.run_analysis_recipe(materialized)
            plot = session.plots[0]
        figure = session.render(plot, engine=engine)
        try:
            _assert_native(figure, engine, tier, explicit)
            assert not plot.update_from_relayout(wire)
        finally:
            if engine == "matplotlib":
                plt.close(cast(Any, figure))
