"""Public figure-theme apply, customize, import, export, and rendering contract."""

from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.figure
import pandas as pd
import plotly.graph_objects as go
import pytest
from typing import cast

import ring5

pytestmark = pytest.mark.public_api


def test_public_theme_round_trip_preserves_data_and_renders_dark_bars_in_both_engines() -> None:
    # [test->req~ring5.figure.theme-presets~1]
    data = pd.DataFrame(
        {
            "phase": ["warmup", "steady", "warmup", "steady"],
            "variant": ["baseline", "baseline", "candidate", "candidate"],
            "ipc": [1.0, 1.1, 1.2, 1.4],
        }
    )
    with ring5.Session() as session:
        themes = session.available_figure_themes()
        custom = session.customize_figure_theme(
            "dark",
            {"title_font_size": 24},
            name="Dark review",
        )
        payload = session.export_figure_theme(custom)
        imported = session.import_figure_theme(payload)
        reexported = session.export_figure_theme(imported)
        config = session.apply_figure_theme(
            {"x": "phase", "y": "ipc", "color": "variant"},
            imported,
            "bar",
        )
        plot = session.create_plot("bar", data=data, config=config)
        plotly_figure = session.render(plot, engine="plotly")
        matplotlib_figure = session.render(plot, engine="matplotlib")

    assert [theme.identifier for theme in themes] == [
        "paper",
        "presentation",
        "dashboard",
        "dark",
    ]
    assert isinstance(imported, ring5.FigureTheme)
    assert payload == reexported
    assert config["x"] == "phase"
    assert config["color"] == "variant"
    assert config["title_font_size"] == 24
    assert config["figure_theme_context"] == "dark"
    assert isinstance(plotly_figure, go.Figure)
    assert plotly_figure.layout.plot_bgcolor == "#202633"
    bars = [cast(go.Bar, trace) for trace in plotly_figure.data]
    assert all(isinstance(trace, go.Bar) for trace in bars)
    assert [trace.marker.pattern.shape for trace in bars] == ["/", "\\"]
    assert isinstance(matplotlib_figure, matplotlib.figure.Figure)
    assert mcolors.to_hex(matplotlib_figure.axes[0].get_facecolor()) == "#202633"
    assert {
        patch.get_hatch()
        for container in matplotlib_figure.axes[0].containers
        for patch in container
    } == {"/", "\\"}


def test_public_theme_errors_are_typed_and_do_not_accept_data_bindings() -> None:
    # [test->req~ring5.figure.theme-presets~1]
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="Unknown figure theme"):
            session.apply_figure_theme({}, "missing", "line")
        with pytest.raises(ring5.DataValidationError, match="cannot contain data"):
            session.customize_figure_theme("paper", {"x": "private"}, name="Bad")
        with pytest.raises(ring5.DataValidationError, match="UTF-8 JSON"):
            session.import_figure_theme("not-json")
        with pytest.raises(ring5.DataValidationError, match="FigureTheme instance"):
            session.export_figure_theme({})  # type: ignore[arg-type]
