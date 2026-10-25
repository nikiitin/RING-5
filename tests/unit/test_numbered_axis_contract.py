"""One numbered-axis representation across public specs and rendering."""

from itertools import combinations
from typing import Literal

import pandas as pd
import pytest

import ring5
from src.core.common.numbered_axis import NUMBERED_AXIS_MODES, numbered_axis_modes
from src.web.pages.ui.plotting.plot_factory import PlotFactory

pytestmark = pytest.mark.public_api


def test_absent_and_empty_modes_are_distinct_and_read_without_mutation() -> None:
    assert numbered_axis_modes({}) is None
    config = {"numbered_xaxis_modes": []}
    assert numbered_axis_modes(config) == []
    modes = ["Labels", "Number legend"]
    result = numbered_axis_modes({"numbered_xaxis_modes": modes})
    assert result == modes and result is not modes
    assert "numbered_xaxis_modes" not in ring5.FigureSpec().to_config()
    assert ring5.FigureSpec(numbered_xaxis_modes=[]).to_config()["numbered_xaxis_modes"] == []


@pytest.mark.parametrize(
    "modes",
    [
        None,
        True,
        False,
        "Numbers",
        ("Numbers",),
        {},
        ["unknown"],
        [True],
        [[]],
        ["Numbers", "Numbers"],
    ],
)
def test_mode_inputs_are_exact_unique_allowed_lists(modes: object) -> None:
    with pytest.raises(ValueError, match="numbered_xaxis_modes"):
        numbered_axis_modes({"numbered_xaxis_modes": modes})
    with pytest.raises(ValueError, match="numbered_xaxis_modes"):
        ring5.FigureSpec(extra={"numbered_xaxis_modes": modes}).to_config()
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="numbered_xaxis_modes"):
            session.create_plot(
                "bar",
                data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [1]})),
                config={"x": "x", "y": "y", "numbered_xaxis_modes": modes},
            )
        assert not session.plots


@pytest.mark.parametrize(
    "key",
    [
        "numbered_xaxis",
        "show_numbered_ticks",
        "show_numbered_legend",
        "numbered_legend_size",
        "numbered_legend_bgcolor",
        "numbered_legend_x",
        "numbered_legend_y",
        "numbered_legend_columns",
    ],
)
def test_retired_keys_are_rejected_before_public_plot_registration(key: str) -> None:
    config = {"x": "x", "y": "y", key: False, "numbered_xaxis_modes": []}
    with pytest.raises(ValueError, match="Unsupported numbered-axis keys"):
        numbered_axis_modes(config)
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match=key):
            session.create_plot(
                "bar", data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [1]})), config=config
            )
        assert not session.plots
    plot = PlotFactory.create_plot("bar", 1, "Restored")
    payload = plot.to_dict()
    payload["config"] = config
    with pytest.raises(ValueError, match=key):
        PlotFactory.from_dict(payload)


def test_public_spec_uses_current_modes_and_routes_number_legend_to_free_tier() -> None:
    with pytest.raises(ValueError, match="unique"):
        ring5.FigureSpec(numbered_xaxis_modes=["Labels", "Labels"])
    with pytest.raises(ValueError, match="numbered_xaxis_modes"):
        ring5.FigureSpec(numbered_xaxis_modes=["unknown"])
    spec = ring5.FigureSpec(
        x="x",
        y_columns=["a"],
        numbered_xaxis_modes=["Number legend"],
        number_legend=ring5.LegendOpts(font_size=19),
        dual_axis=ring5.DualAxisOpts(
            columns=["b"], unified_legend=False, legend=ring5.LegendOpts(font_size=11)
        ),
    )
    config = spec.to_config()
    assert config["dual_legend_font_size"] == 11
    assert config["legend3_font_size"] == 19
    assert ring5.FigureSpec(numbered_xaxis_modes=["Labels"]).numbered_xaxis_modes == ("Labels",)


@pytest.mark.parametrize(
    "kind",
    [kind for kind in PlotFactory.get_available_plot_types() if kind != "grouped_stacked_bar"],
)
@pytest.mark.parametrize("typed", [False, True])
def test_unsupported_builtin_numbering_is_rejected_before_registration(
    kind: str, typed: bool
) -> None:
    config = ring5.FigureSpec(x="x", y_columns=["y"], numbered_xaxis_modes=["Numbers"])
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="only by grouped_stacked_bar"):
            session.create_plot(
                kind,
                data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [1]})),
                config=config if typed else config.to_config(),
            )
        assert not session.plots


@pytest.mark.parametrize("extra", [{}, {"numbered_xaxis_modes": []}])
def test_ordinary_plot_accepts_unspecified_or_empty_numbering(extra: dict[str, object]) -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [1]})),
            config={"x": "x", "y": "y", **extra},
        )
        assert plot.config == {"x": "x", "y": "y", **extra}


def test_registered_custom_plot_keeps_its_numbering_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor = PlotFactory._plot_classes["bar"]
    monkeypatch.setitem(PlotFactory._plot_classes, "custom_numbering", constructor)
    plot = PlotFactory.create_plot("custom_numbering", 1, "Custom")
    payload = plot.to_dict()
    payload["plot_type"] = "custom_numbering"
    payload["config"] = {"numbered_xaxis_modes": ["Numbers"]}
    restored = PlotFactory.from_dict(payload)
    assert restored.config == payload["config"]


_MODE_SUBSETS = [
    list(items) for count in range(4) for items in combinations(NUMBERED_AXIS_MODES, count)
]


@pytest.mark.parametrize("modes", _MODE_SUBSETS)
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_every_mode_subset_keeps_measurements_and_numbering_consistent(
    modes: list[str], engine: Literal["plotly", "matplotlib"]
) -> None:
    # [test->req~ring5.figure.numbered-xaxis~1]
    data = pd.DataFrame(
        {"x": ["A", "A"], "group": ["base", "tuned"], "a": [1.0, 2.0], "b": [3.0, 4.0]}
    )
    original = data.copy(deep=True)
    with ring5.Session() as session:
        plot = session.create_plot(
            "grouped_stacked_bar",
            data=ring5.Table(data),
            config={
                "x": "x",
                "group": "group",
                "y_columns": ["a", "b"],
                "numbered_xaxis_modes": modes,
            },
        )
        session.render(plot, engine=engine)
    assert plot.last_traces is not None
    assert [trace.y for trace in plot.last_traces.traces] == [[1.0, 2.0], [3.0, 4.0]]
    if "Numbers" in modes and "Labels" in modes:
        expected = ["1. base", "2. tuned"]
    elif "Numbers" in modes:
        expected = ["1", "2"]
    elif not modes or "Labels" in modes:
        expected = ["base", "tuned"]
    else:
        expected = ["", ""]
    assert plot.last_traces.custom_x_ticks is not None
    assert plot.last_traces.custom_x_ticks["text"] == expected
    legends = [
        a for a in plot.last_traces.layout_annotations if str(a.get("text", "")).startswith("1.")
    ]
    assert bool(legends) == ("Number legend" in modes)
    pd.testing.assert_frame_equal(data, original)
