"""Real settings widgets preserve saved color values and explicit hatch intent."""

from copy import deepcopy
from typing import Any, Literal

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5
from src.core.common.plot_payload import BAR_HATCH_PATTERNS
from src.core.services.visualization.palette_service import resolve_palette
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from tests.ui.test_plot_settings_contracts import _app, _render


def _example(**config: Any) -> BasePlot:
    plot = PlotFactory.create_plot("bar", plot_id=41, name="Measured")
    plot.processed_data = pd.DataFrame(
        {"x": ["a", "b", "a", "b"], "series": ["A", "A", "B", "B"], "y": [2.0, 5.0, 7.0, 11.0]}
    )
    plot.config = {"x": "x", "y": "y", "color": "series", **config}
    return plot


_COLORS: dict[str, Any] = {
    "color_palette": ["rgba(10,20,30,0.35)", "hsl(240 100% 50% / 0.25)"],
    "plot_bgcolor": "rgba(50,60,70,0.4)",
    "paper_bgcolor": "#aabbcc88",
    "grid_color": "rgba(120,130,140,0.5)",
    "axis_color": "navy",
    "series_styles": {"A": {"color": "hsl(120 100% 50% / 0.6)", "use_color": True}},
}


def _assert_saved_colors(plot: BasePlot) -> None:
    for key in ("color_palette", "plot_bgcolor", "paper_bgcolor", "grid_color", "axis_color"):
        assert plot.config[key] == _COLORS[key]
    assert plot.config["series_styles"]["A"]["color"] == _COLORS["series_styles"]["A"]["color"]
    assert "pattern" not in plot.config["series_styles"]["A"]


def test_untouched_custom_palette_css_and_alpha_survive_reruns_and_navigation() -> None:
    # [test->req~ring5.figure.colors~1]
    source = _example(**deepcopy(_COLORS))
    original = deepcopy(source.config)
    app = _app(source, "colors")
    plot = app.session_state["plot"]
    _assert_saved_colors(plot)
    app.run()
    assert not app.exception and app.session_state["source_unchanged"]
    _assert_saved_colors(plot)
    app.button_group(key="settings_nav").set_value("typography").run()
    app.button_group(key="settings_nav").set_value("colors").run()
    assert not app.exception
    _assert_saved_colors(plot)
    assert source.config == original


@pytest.mark.parametrize("palette", [["#123456", "rgba(10,20,30,0.5)"], resolve_palette("wong")])
def test_custom_palette_remains_a_sequence_until_a_named_palette_is_selected(
    palette: list[str],
) -> None:
    # [test->req~ring5.figure.colors~1]
    app = _app(_example(color_palette=palette), "colors")
    plot = app.session_state["plot"]
    assert plot.config["color_palette"] == palette
    assert type(plot.config["color_palette"]) is list
    selector = next(widget for widget in app.selectbox if widget.label == "Palette")
    index = next(i for i, label in enumerate(selector.options) if label.lower().endswith("wong"))
    selector.select_index(index).run()
    assert not app.exception
    selected_palette = app.session_state["plot"].config["color_palette"]
    assert isinstance(selected_palette, str) and selected_palette == "wong"


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_transparency_toggle_preserves_underlying_css_and_roundtrips_native_backgrounds(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    # [test->req~ring5.figure.colors~1]
    app = _app(_example(**deepcopy(_COLORS)), "colors")
    plot = app.session_state["plot"]
    key = f"plot.{plot.plot_id}.widgets.appearance.theme_trans_bg"
    app.checkbox(key=key).set_value(True).run()
    assert not app.exception
    _assert_saved_colors(plot)
    _, native = _render(app, engine)
    try:
        if isinstance(native, go.Figure):
            assert native.layout.plot_bgcolor == native.layout.paper_bgcolor == "rgba(0,0,0,0)"
        else:
            assert native.axes[0].get_facecolor()[-1] == native.get_facecolor()[-1] == 0
    finally:
        if isinstance(native, Figure):
            plt.close(native)
    app.run()
    app.button_group(key="settings_nav").set_value("layout").run()
    app.button_group(key="settings_nav").set_value("colors").run()
    app.checkbox(key=key).set_value(False).run()
    assert not app.exception
    _assert_saved_colors(plot)
    _, native = _render(app, engine)
    try:
        if isinstance(native, go.Figure):
            assert native.layout.plot_bgcolor == _COLORS["plot_bgcolor"]
            assert native.layout.paper_bgcolor == _COLORS["paper_bgcolor"]
        else:
            assert native.axes[0].get_facecolor() == pytest.approx(
                (50 / 255, 60 / 255, 70 / 255, 0.4)
            )
            assert native.get_facecolor() == pytest.approx(to_rgba("#aabbcc88"))
    finally:
        if isinstance(native, Figure):
            plt.close(native)


def test_explicit_picker_edit_changes_only_the_selected_color() -> None:
    # [test->req~ring5.figure.colors~1]
    app = _app(_example(**deepcopy(_COLORS)), "colors")
    plot = app.session_state["plot"]
    app.color_picker(key=f"plot.{plot.plot_id}.widgets.appearance.theme_bg_plot").set_value(
        "#abcdef"
    ).run()
    assert not app.exception
    assert plot.config["plot_bgcolor"] == "#abcdef"
    assert plot.config["paper_bgcolor"] == _COLORS["paper_bgcolor"]
    assert plot.config["color_palette"] == _COLORS["color_palette"]


def test_unprojectable_css_is_visible_editable_and_never_repaired_to_a_picker_color() -> None:
    # [test->req~ring5.figure.colors~1]
    app = _app(_example(plot_bgcolor="var(--surface)"), "colors")
    plot = app.session_state["plot"]
    assert plot.config["plot_bgcolor"] == "var(--surface)"
    field = app.text_input(key=f"plot.{plot.plot_id}.widgets.appearance.theme_bg_plot.literal")
    assert field.value == "var(--surface)"
    field.set_value("hwb(120 10% 20%)").run()
    assert not app.exception
    assert plot.config["plot_bgcolor"] == "hwb(120 10% 20%)"
    _, native = _render(app, "plotly")
    assert isinstance(native, go.Figure)
    assert native.layout.plot_bgcolor == "hwb(120 10% 20%)"
    with ring5.Session() as session, pytest.raises(ring5.RenderError, match="static RGB"):
        session.render(plot, engine="matplotlib")


def test_unavailable_named_palette_is_preserved_until_explicit_replacement() -> None:
    # [test->req~ring5.figure.colors~1]
    app = _app(_example(color_palette="unavailable_palette"), "colors")
    plot = app.session_state["plot"]
    assert plot.config["color_palette"] == "unavailable_palette"
    app.run()
    assert not app.exception
    assert plot.config["color_palette"] == "unavailable_palette"
    assert any("no available preview" in widget.value for widget in app.warning)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("pattern", BAR_HATCH_PATTERNS)
def test_every_current_pattern_is_selected_as_an_actual_widget_value_and_renders(
    engine: Literal["plotly", "matplotlib"], pattern: str
) -> None:
    # [test->req~ring5.figure.series-styling~1]
    app = _app(_example(), "colors")
    selector = next(widget for widget in app.selectbox if widget.label == "Pattern")
    selector.select_index(1 + BAR_HATCH_PATTERNS.index(pattern)).run()
    assert not app.exception
    plot, native = _render(app, engine)
    try:
        assert plot.config["series_styles"]["A"]["pattern"] == pattern
        if isinstance(native, go.Figure):
            assert isinstance(native.data[0], go.Bar)
            style = native.data[0].marker.pattern
            if pattern in ("o", "O", "*"):
                assert style.path and style.shape is None and style.solidity is None
            else:
                assert style.shape == pattern and style.path is None
            assert list(native.data[0].y) == [2.0, 5.0]
        else:
            assert native.axes[0].patches[0].get_hatch() == pattern
            heights = []
            for patch in native.axes[0].patches:
                assert isinstance(patch, Rectangle)
                heights.append(patch.get_height())
            assert heights == [2.0, 5.0, 7.0, 11.0]
            legend = native.axes[0].get_legend()
            assert legend is not None
            swatch = legend.legend_handles[0]
            assert isinstance(swatch, Rectangle) and swatch.get_hatch() == pattern
    finally:
        if isinstance(native, Figure):
            plt.close(native)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_default_preserves_theme_hatching_and_solid_is_explicit(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    app = _app(_example(accessibility_mode=True, color_palette="ring5_accessible"), "colors")
    plot = app.session_state["plot"]
    assert "pattern" not in plot.config["series_styles"]["A"]
    _, first = _render(app, engine)
    try:
        if isinstance(first, go.Figure):
            assert isinstance(first.data[0], go.Bar)
            assert first.data[0].marker.pattern.shape
        else:
            assert first.axes[0].patches[0].get_hatch()
    finally:
        if isinstance(first, Figure):
            plt.close(first)
    selector = next(widget for widget in app.selectbox if widget.label == "Pattern")
    selector.select_index(1).run()
    assert not app.exception
    assert plot.config["series_styles"]["A"]["pattern"] == ""
    _, solid = _render(app, engine)
    try:
        if isinstance(solid, go.Figure):
            assert isinstance(solid.data[0], go.Bar)
            assert solid.data[0].marker.pattern.shape == ""
        else:
            assert solid.axes[0].patches[0].get_hatch() == ""
    finally:
        if isinstance(solid, Figure):
            plt.close(solid)
    selector = next(widget for widget in app.selectbox if widget.label == "Pattern")
    selector.select_index(0).run()
    assert not app.exception
    assert "pattern" not in plot.config["series_styles"]["A"]


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_immutable_numpy_text_colors_survive_real_widgets_and_native_rendering(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    palette = [np.str_("rgba(10,20,30,0.35)"), np.str_("#123456")]
    background = np.str_("hsl(240 100% 50% / 0.25)")
    app = _app(_example(color_palette=palette, plot_bgcolor=background), "colors")
    app.run()
    assert not app.exception
    plot = app.session_state["plot"]
    assert plot.config["color_palette"] == palette
    assert all(type(color) is np.str_ for color in plot.config["color_palette"])
    assert type(plot.config["plot_bgcolor"]) is np.str_
    assert plot.config["plot_bgcolor"] == background
    _, native = _render(app, engine)
    try:
        if isinstance(native, go.Figure):
            assert native.layout.plot_bgcolor == background
            assert isinstance(native.data[0], go.Bar)
            assert list(native.data[0].y) == [2.0, 5.0]
        else:
            assert native.axes[0].get_facecolor() == pytest.approx((0, 0, 1, 0.25))
            assert all(isinstance(patch, Rectangle) for patch in native.axes[0].patches)
            bars = native.axes[0].containers[0]
            assert [patch.get_height() for patch in bars] == [2.0, 5.0]
    finally:
        if isinstance(native, Figure):
            plt.close(native)


def test_immutable_numpy_text_palette_name_remains_unchanged_when_opened() -> None:
    palette = np.str_("viridis_8")
    app = _app(_example(color_palette=palette), "colors")
    app.run()
    assert not app.exception
    selected = app.session_state["plot"].config["color_palette"]
    assert type(selected) is np.str_ and selected == palette


def test_swatch_markup_uses_projected_rgba_and_preserves_unsupported_literals_as_text() -> None:
    # [test->req~ring5.figure.colors~1]
    unsafe = "red;position:fixed;inset:0"
    unresolved = "var(--saved-surface)"
    palette = [unsafe, "rgba(10,20,30,0.5)", unresolved]
    app = _app(_example(color_palette=palette), "colors")
    assert not app.exception
    app.run()
    assert not app.exception
    assert app.session_state["plot"].config["color_palette"] == palette
    markup = " ".join(widget.value for widget in app.markdown if "<span style=" in widget.value)
    assert "background:#0a141e80;" in markup
    assert unsafe not in markup and "position:fixed" not in markup and unresolved not in markup
    literal_values = [widget.value for widget in app.text]
    assert f"Saved palette color (no swatch preview): {unsafe}" in literal_values
    assert f"Saved palette color (no swatch preview): {unresolved}" in literal_values
