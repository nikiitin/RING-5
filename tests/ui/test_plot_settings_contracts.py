"""Real settings widgets route current plot controls without aggregate UI paths."""

from __future__ import annotations

import copy
from typing import Any, Literal

import plotly.graph_objects as go
import pytest
from matplotlib.figure import Figure
from matplotlib.markers import MarkerStyle
from streamlit.testing.v1 import AppTest

from ring5 import Session
from scripts.generate_example_portfolio import build_example_data, build_example_plots
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.settings_pills import SETTINGS_SECTIONS

_APP = """
import copy
import streamlit as st
from src.web.pages.ui.plotting.settings_pills import render_settings_pills
plot = st.session_state["plot"]
advanced = st.toggle("Show advanced settings", key="advanced")
section = render_settings_pills(show_advanced=advanced)
saved = copy.deepcopy(plot.config)
original = copy.deepcopy(saved)
result = plot.render_settings_section(section, saved, plot.processed_data)
st.session_state["source_unchanged"] = saved == original
st.session_state["emitted"] = result
plot.config = {**saved, **result}
"""


@pytest.fixture(scope="module")
def example_cases() -> dict[str, BasePlot]:
    return {plot.plot_type: plot for plot in build_example_plots(build_example_data())}


def _app(example: BasePlot, section: str | None = None, **overrides: Any) -> AppTest:
    plot = PlotFactory.create_plot(example.plot_type, example.plot_id, example.name)
    plot.config = {**copy.deepcopy(example.config), **overrides}
    assert example.processed_data is not None
    plot.replace_processed_data(example.processed_data.copy(deep=True))
    app = AppTest.from_string(_APP)
    app.session_state["plot"] = plot
    app.run()
    assert not app.exception
    if section is not None:
        app.toggle(key="advanced").set_value(True).run()
        app.button_group(key="settings_nav").set_value(section).run()
        assert not app.exception
    return app


def _render(
    app: AppTest, engine: Literal["plotly", "matplotlib"]
) -> tuple[BasePlot, go.Figure | Figure]:
    plot = app.session_state["plot"]
    with Session() as session:
        figure = session.render(plot, engine=engine)
    assert plot.last_traces is not None and plot.last_traces.traces
    return plot, figure


@pytest.mark.parametrize("kind", PlotFactory.get_available_plot_types())
def test_every_family_navigates_every_real_settings_pill(
    kind: str, example_cases: dict[str, BasePlot]
) -> None:
    # [test->req~ring5.extension.settings-panel~1]
    app = _app(example_cases[kind])
    assert len(app.button_group(key="settings_nav").options) == 4
    app.toggle(key="advanced").set_value(True).run()
    assert len(app.button_group(key="settings_nav").options) == 8
    for section in SETTINGS_SECTIONS:
        app.button_group(key="settings_nav").set_value(section.key).run()
        assert not app.exception, (kind, section.key)
        assert app.session_state["source_unchanged"], (kind, section.key)
        emitted = app.session_state["emitted"]
        assert isinstance(emitted, dict)
        required = {
            "layout": {"width", "height"},
            "typography": {"title_font_size"},
            "legends": {"legend_x"},
            "axes": {"xaxis_tickangle"},
            "data_labels": {"show_values"},
            "colors": {"color_palette", "series_styles"},
            "advanced": {"download_format", "show_error_bars"},
        }
        assert required.get(section.key, set()).issubset(emitted), (kind, section.key)
        if section.key == "axes":
            has_numbered_widget = any(
                widget.key
                == f"plot.{app.session_state['plot'].plot_id}.widgets.appearance.numbered_modes"
                for widget in app.button_group
            )
            assert has_numbered_widget is (kind == "grouped_stacked_bar")
            assert ("numbered_xaxis_modes" in emitted) is (kind == "grouped_stacked_bar")


@pytest.mark.parametrize("kind", ["stacked_bar", "grouped_stacked_bar"])
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_bar_totals_survive_value_label_toggles_and_render_real_values(
    kind: str, engine: Literal["plotly", "matplotlib"], example_cases: dict[str, BasePlot]
) -> None:
    # [test->req~ring5.figure.stack-totals~1]
    app = _app(
        example_cases[kind],
        "data_labels",
        show_values=True,
        show_totals=True,
        net_total_format=".1f",
        total_font_size=17,
        total_font_color="#123456",
    )
    plot = app.session_state["plot"]
    checkbox = app.checkbox(key=f"plot.{plot.plot_id}.widgets.appearance.theme_show_totals")
    assert checkbox.value
    app.checkbox(key=f"plot.{plot.plot_id}.widgets.appearance.theme_show_val").uncheck().run()
    assert app.session_state["plot"].config["show_totals"]
    assert app.checkbox(key=f"plot.{plot.plot_id}.widgets.appearance.theme_show_totals").value
    app.text_input(key=f"plot.{plot.plot_id}.widgets.appearance.theme_total_format").set_value(
        ".0f"
    ).run()
    app.selectbox(key=f"plot.{plot.plot_id}.widgets.appearance.total_position").select(
        "Inside"
    ).run()
    app.selectbox(key=f"plot.{plot.plot_id}.widgets.appearance.total_anchor").select("Middle").run()
    app.number_input(key=f"plot.{plot.plot_id}.widgets.appearance.total_rotation").set_value(
        45
    ).run()
    assert not app.exception
    plot, figure = _render(app, engine)
    assert plot.last_traces is not None
    numeric_totals = [
        a for a in plot.last_traces.layout_annotations if a.get("font", {}).get("size") == 17
    ]
    assert numeric_totals
    assert all(a["font"]["color"] == "#123456" for a in numeric_totals)
    assert all(a["yanchor"] == "middle" and a["textangle"] == 45 for a in numeric_totals)
    assert all(
        float(a["text"]) == pytest.approx(float(a["y"]) * 2, abs=0.5) for a in numeric_totals
    )
    if isinstance(figure, go.Figure):
        assert any(a.font.size == 17 for a in figure.layout.annotations)
    else:
        assert any(text.get_fontsize() == 17 for axis in figure.axes for text in axis.texts)


def test_group_layout_controls_change_existing_geometry(example_cases: dict[str, BasePlot]) -> None:
    # [test->req~ring5.figure.alternate-category-shading~1]
    app = _app(example_cases["grouped_bar"], "layout")
    plot = app.session_state["plot"]
    app.checkbox(key=f"plot.{plot.plot_id}.widgets.appearance.show_separators").check().run()
    app.checkbox(key=f"plot.{plot.plot_id}.widgets.appearance.shade_alternate").check().run()
    app.checkbox(key=f"plot.{plot.plot_id}.widgets.appearance.isolate_last_group").check().run()
    app.number_input(key=f"plot.{plot.plot_id}.widgets.appearance.isolation_gap").set_value(
        1.5
    ).run()
    assert not app.exception
    for engine in ("plotly", "matplotlib"):
        plot, figure = _render(app, engine)
        assert plot.last_traces is not None
        assert plot.last_traces.separator_lines and plot.last_traces.shaded_regions
        if isinstance(figure, go.Figure):
            assert figure.layout.shapes
        else:
            assert figure.axes[0].patches or figure.axes[0].lines


def test_numbered_axes_widget_has_three_modes_and_empty_is_current_off(
    example_cases: dict[str, BasePlot],
) -> None:
    # [test->req~ring5.figure.numbered-xaxis~1]
    app = _app(example_cases["grouped_stacked_bar"], "axes")
    plot = app.session_state["plot"]
    modes = app.button_group(key=f"plot.{plot.plot_id}.widgets.appearance.numbered_modes")
    assert len(modes.options) == 3
    modes.set_value(["Labels", "Numbers", "Number legend"]).run()
    assert app.session_state["emitted"]["numbered_xaxis_modes"] == [
        "Labels",
        "Numbers",
        "Number legend",
    ]
    assert not {"numbered_xaxis", "show_numbered_ticks", "show_numbered_legend"}.intersection(
        app.session_state["emitted"]
    )
    app.button_group(key=f"plot.{plot.plot_id}.widgets.appearance.numbered_modes").set_value(
        []
    ).run()
    assert not app.exception
    assert app.session_state["emitted"]["numbered_xaxis_modes"] == []


@pytest.mark.parametrize("kind", ["bar", "line", "scatter"])
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_live_colors_preserve_type_specific_patterns_and_markers(
    kind: str, engine: Literal["plotly", "matplotlib"], example_cases: dict[str, BasePlot]
) -> None:
    # [test->req~ring5.figure.series-styling~1]
    app = _app(example_cases[kind], "colors")
    label = "Pattern" if kind == "bar" else "Marker Symbol"
    selector = next(widget for widget in app.selectbox if widget.label == label)
    selector.select("x" if kind == "bar" else "triangle-up").run()
    assert not app.exception and app.session_state["source_unchanged"]
    plot, figure = _render(app, engine)
    styles = plot.config["series_styles"]
    assert any(
        style.get("pattern" if kind == "bar" else "symbol")
        == ("x" if kind == "bar" else "triangle-up")
        for style in styles.values()
    )
    if isinstance(figure, go.Figure):
        if kind == "bar":
            assert any(trace.marker.pattern.shape == "x" for trace in figure.data)
        else:
            assert any(trace.marker.symbol == "triangle-up" for trace in figure.data)
    elif kind == "bar":
        assert any(patch.get_hatch() == "x" for axis in figure.axes for patch in axis.patches)
    elif kind == "line":
        assert any(line.get_marker() == "^" for axis in figure.axes for line in axis.lines)
    else:
        marker = MarkerStyle("^")
        expected = marker.get_path().transformed(marker.get_transform()).vertices.tolist()
        assert any(
            path.vertices.tolist() == expected
            for axis in figure.axes
            for collection in axis.collections
            for path in collection.get_paths()
        )


def test_right_axis_fonts_trace_controls_and_legend_tiers_use_active_pills(
    example_cases: dict[str, BasePlot],
) -> None:
    # [test->req~ring5.figure.dual-axis-controls~1]
    app = _app(
        example_cases["grouped_stacked_bar"],
        "typography",
        dual_axis=True,
        y_columns_right=["l2_miss_rate"],
        right_axis_type="dots",
        numbered_xaxis_modes=["Numbers", "Number legend"],
        yaxis_title_font_size=7,
        yaxis_tickfont_size=7,
        yaxis2_title_font_size=-1,
        yaxis2_tickfont_size=-1,
        ylabel_right="Right measurement",
    )
    plot = app.session_state["plot"]
    inherited = next(
        widget for widget in app.number_input if widget.label == "Right Y-Axis Title Font Size"
    )
    assert inherited.value == 7
    assert plot.config["yaxis2_title_font_size"] == -1
    for engine in ("plotly", "matplotlib"):
        _, figure = _render(app, engine)
        if isinstance(figure, go.Figure):
            assert figure.layout.yaxis2.tickfont.size == 7
            right_title = next(
                annotation
                for annotation in figure.layout.annotations
                if annotation.text == "Right measurement"
            )
            assert right_title.font.size == 7
        else:
            assert figure.axes[1].yaxis.label.get_fontsize() == 7
            assert all(label.get_fontsize() == 7 for label in figure.axes[1].get_yticklabels())
    app.checkbox(
        key=f"plot.{plot.plot_id}.widgets.appearance.inherit_yaxis2_title_font_size"
    ).uncheck().run()
    assert app.session_state["plot"].config["yaxis2_title_font_size"] == 7
    app.number_input(key=f"plot.{plot.plot_id}.widgets.appearance.y2_title_sz").set_value(23).run()
    app.button_group(key="settings_nav").set_value("axes").run()
    app.button_group(key=f"plot.{plot.plot_id}.widgets.appearance.axis_nav").set_value(
        "y_right"
    ).run()
    app.selectbox(key=f"plot.{plot.plot_id}.widgets.appearance.right_dot_sym").select(
        "diamond"
    ).run()
    app.number_input(key=f"plot.{plot.plot_id}.widgets.appearance.right_dot_size").set_value(
        13
    ).run()
    app.number_input(key=f"plot.{plot.plot_id}.widgets.appearance.right_line_w").set_value(4).run()
    app.button_group(key="settings_nav").set_value("legends").run()
    app.checkbox(key=f"plot.{plot.plot_id}.widgets.appearance.unified_legend").uncheck().run()
    assert (
        len(app.button_group(key=f"plot.{plot.plot_id}.widgets.appearance.legend_nav").options) == 3
    )
    app.button_group(key=f"plot.{plot.plot_id}.widgets.appearance.legend_nav").set_value(
        "tertiary"
    ).run()
    assert "legend3_font_size" in app.session_state["emitted"]
    assert not app.exception
    for engine in ("plotly", "matplotlib"):
        plot, figure = _render(app, engine)
        assert plot.last_traces is not None
        right = [trace for trace in plot.last_traces.traces if trace.yaxis == "y2"]
        assert right and all(
            trace.marker_symbol == "diamond" and trace.marker_size == 13 and trace.line_width == 4
            for trace in right
        )
        if isinstance(figure, go.Figure):
            assert any(
                trace.yaxis == "y2" and trace.marker.symbol == "diamond" for trace in figure.data
            )
            assert figure.layout.yaxis2.tickfont.size == 7
            right_title = next(
                annotation
                for annotation in figure.layout.annotations
                if annotation.text == "Right measurement"
            )
            assert right_title.font.size == 23
            number_legend = next(
                annotation for annotation in figure.layout.annotations if "1. " in annotation.text
            )
            assert number_legend.font.size == plot.config.get("legend_font_size", 12)
        else:
            assert len(figure.axes) == 2
            assert figure.axes[1].get_ylabel() == "Right measurement"
            assert figure.axes[1].yaxis.label.get_fontsize() == 23
            assert all(label.get_fontsize() == 7 for label in figure.axes[1].get_yticklabels())


def test_major_label_fonts_and_placement_have_separate_owners(
    example_cases: dict[str, BasePlot],
) -> None:
    app = _app(example_cases["grouped_stacked_bar"], "typography")
    plot = app.session_state["plot"]
    app.number_input(key=f"plot.{plot.plot_id}.widgets.appearance.major_label_size").set_value(
        21
    ).run()
    app.color_picker(key=f"plot.{plot.plot_id}.widgets.appearance.major_label_color").set_value(
        "#123456"
    ).run()
    assert "major_label_offset" not in app.session_state["emitted"]
    app.button_group(key="settings_nav").set_value("axes").run()
    app.button_group(key=f"plot.{plot.plot_id}.widgets.appearance.axis_nav").set_value(
        "group"
    ).run()
    app.number_input(key=f"plot.{plot.plot_id}.widgets.appearance.grp_lbl_dist").set_value(
        -0.3
    ).run()
    assert "major_label_size" not in app.session_state["emitted"]
    assert not app.exception
    for engine in ("plotly", "matplotlib"):
        plot, figure = _render(app, engine)
        assert plot.last_traces is not None
        labels = [
            annotation
            for annotation in plot.last_traces.layout_annotations
            if annotation.get("font", {}).get("size") == 21
        ]
        assert labels and all(annotation["font"]["color"] == "#123456" for annotation in labels)
        assert any(annotation["y"] == pytest.approx(-0.3) for annotation in labels)
