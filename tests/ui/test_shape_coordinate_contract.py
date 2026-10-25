"""Shape coordinates retain explicit numeric or literal intent through real editing."""

from copy import deepcopy
import math
from typing import Any

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.web.components.plotting.settings.shapes_settings import _decode_coordinate
from src.web.pages.ui.plotting.plot_service import PlotService
from tests.ui.helpers import create_app_with_data, get_api, navigate_to


def _shape() -> dict[str, Any]:
    return {
        "type": "line",
        "x0": "001",
        "y0": 2.0,
        "x1": "002",
        "y1": 4.0,
        "line": {"color": "#000000", "width": 2},
    }


def _app(shapes: list[dict[str, Any]]) -> tuple[AppTest, Any, Any]:
    app = create_app_with_data(
        pd.DataFrame({"kind": ["001", "002", "003"], "metric": [3.0, 5.0, 7.0]})
    )
    api = get_api(app)
    plot = PlotService.create_plot("Measured", "bar", api.state_manager)
    plot.replace_processed_data(api.state_manager.get_data())
    plot.config = {"x": "kind", "y": "metric", "shapes": deepcopy(shapes)}
    navigate_to(app, "Manage Plots")
    return app, api, plot


def _advanced(app: AppTest, plot: Any) -> None:
    app.toggle(key=f"plot.{plot.plot_id}.widgets.show_advanced").set_value(True).run()
    app.pills(key="settings_nav").set_value("advanced").run()
    assert not app.exception


def _row(plot: Any, field: str, index: int = 0) -> str:
    return f"plot.{plot.plot_id}.widgets.appearance.shape_rows.edit_{field}_{index}"


def _add(plot: Any, field: str) -> str:
    return f"plot.{plot.plot_id}.widgets.appearance.s_{field}"


def _measurements(plot: Any) -> None:
    assert list(plot.last_generated_fig.data[0].y) == [3.0, 5.0, 7.0]


def test_untouched_literal_coordinates_and_explicit_text_numeric_edits_reach_native() -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    original = _shape()
    app, api, plot = _app([original])
    try:
        before = deepcopy(plot.config["shapes"])
        assert plot.last_generated_fig.layout.shapes[0].x0 == "001"
        _advanced(app, plot)
        app.run()
        assert not app.exception
        assert plot.config["shapes"] == before
        assert app.checkbox(key=_row(plot, "x0") + ".text_mode").value is True
        assert app.checkbox(key=_row(plot, "y0") + ".text_mode").value is False
        assert plot.last_generated_fig.layout.shapes[0].x0 == "001"
        assert plot.last_generated_fig.layout.shapes[0].x1 == "002"

        app.text_input(key=_row(plot, "x0")).set_value("003").run()
        app.text_input(key=_row(plot, "y0")).set_value("12.5").run()
        assert not app.exception
        assert plot.config["shapes"][0]["x0"] == "003"
        assert type(plot.config["shapes"][0]["y0"]) is float
        assert plot.config["shapes"][0]["y0"] == 12.5
        native = plot.last_generated_fig.layout.shapes[0]
        assert native.x0 == "003"
        assert native.y0 == 12.5
        assert original == _shape()
        _measurements(plot)
    finally:
        api.close()


def test_add_numeric_looking_literal_coordinates_has_one_explicit_kind() -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    app, api, plot = _app([])
    try:
        _advanced(app, plot)
        for field, text in (("x0", "001"), ("x1", "003")):
            app.text_input(key=_add(plot, field)).set_value(text).run()
            app.checkbox(key=_add(plot, field) + ".text_mode").check().run()
        app.text_input(key=_add(plot, "y0")).set_value("2.5").run()
        app.button(key=f"plot.{plot.plot_id}.widgets.appearance.add_shape").click().run()
        assert not app.exception
        shape = plot.config["shapes"][0]
        assert (shape["x0"], shape["x1"], shape["y0"]) == ("001", "003", 2.5)
        assert type(shape["y0"]) is float
        native = plot.last_generated_fig.layout.shapes[0]
        assert (native.x0, native.x1, native.y0) == ("001", "003", 2.5)
        _measurements(plot)
    finally:
        api.close()


def test_unfinished_add_inputs_do_not_block_existing_rows_or_publish_invalid_shape() -> None:
    app, api, plot = _app([_shape()])
    try:
        _advanced(app, plot)
        app.text_input(key=_add(plot, "x0")).set_value("unfinished number").run()
        app.text_input(key=_row(plot, "y0")).set_value("14.25").run()
        assert not app.exception
        assert plot.config["shapes"][0]["y0"] == 14.25
        app.button(key=f"plot.{plot.plot_id}.widgets.appearance.add_shape").click().run()
        assert not app.exception
        assert any("Cannot add shape" in error.value for error in app.error)
        assert len(plot.config["shapes"]) == 1
        assert plot.config["shapes"][0]["y0"] == 14.25
        _measurements(plot)
    finally:
        api.close()


def test_manual_refresh_preserves_intentional_kind_changes_across_sections() -> None:
    # [test->req~ring5.plots.refresh-cache~1]
    app, api, plot = _app([_shape()])
    try:
        _advanced(app, plot)
        app.toggle(key=f"plot.{plot.plot_id}.widgets.auto_refresh").set_value(False).run()
        app.checkbox(key=_row(plot, "x0") + ".text_mode").uncheck().run()
        app.pills(key="settings_nav").set_value("layout").run()
        app.pills(key="settings_nav").set_value("advanced").run()
        assert plot.config["shapes"][0]["x0"] == "001"
        assert plot.last_generated_fig.layout.shapes[0].x0 == "001"
        assert app.checkbox(key=_row(plot, "x0") + ".text_mode").value is False
        app.button(key=f"plot.{plot.plot_id}.widgets.refresh").click().run()
        assert not app.exception
        assert type(plot.config["shapes"][0]["x0"]) is float
        assert plot.config["shapes"][0]["x0"] == 1.0
        assert plot.last_generated_fig.layout.shapes[0].x0 == 1.0

        app.checkbox(key=_row(plot, "x0") + ".text_mode").check().run()
        app.text_input(key=_row(plot, "x0")).set_value("003").run()
        app.pills(key="settings_nav").set_value("layout").run()
        app.pills(key="settings_nav").set_value("advanced").run()
        assert plot.config["shapes"][0]["x0"] == 1.0
        app.button(key=f"plot.{plot.plot_id}.widgets.refresh").click().run()
        assert not app.exception
        refreshed = api.state_manager.get_plots()[0]
        assert refreshed.config["shapes"][0]["x0"] == "003"
        assert refreshed.last_generated_fig.layout.shapes[0].x0 == "003"
        _measurements(refreshed)
    finally:
        api.close()


@pytest.mark.parametrize("text", ["nan", "1e-400"])
def test_invalid_number_edit_is_visible_and_preserves_the_published_native_shape(text: str) -> None:
    app, api, plot = _app([_shape()])
    try:
        _advanced(app, plot)
        app.text_input(key=_row(plot, "y0")).set_value(text).run()
        assert app.exception
        assert any(
            "finite" in error.message or "too small" in error.message for error in app.exception
        )
        assert plot.config["shapes"][0]["y0"] == 2.0
        assert plot.last_generated_fig.layout.shapes[0].y0 == 2.0
        app.text_input(key=_row(plot, "y0")).set_value("3.5").run()
        assert not app.exception
        assert plot.config["shapes"][0]["y0"] == 3.5
        assert plot.last_generated_fig.layout.shapes[0].y0 == 3.5
        _measurements(plot)
    finally:
        api.close()


@pytest.mark.parametrize(
    "shape",
    [
        {"type": "line", "x0": 0.0, "x1": 1.0},
        {"type": "path", "path": "M 0,0 L 1,1", "line": {"color": "#123456"}},
        {"x0": "001", "x1": "002", "y0": None, "y1": None},
        {
            "type": None,
            "x0": None,
            "y0": None,
            "x1": None,
            "y1": None,
            "xref": "paper",
            "yref": "paper",
        },
        {},
    ],
)
def test_native_partial_path_and_default_shapes_roundtrip_without_invented_fields(
    shape: dict[str, Any],
) -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    original = deepcopy(shape)
    app, api, plot = _app([shape])
    try:
        before = deepcopy(plot.config["shapes"])
        native_before = [item.to_plotly_json() for item in plot.last_generated_fig.layout.shapes]
        _advanced(app, plot)
        app.run()
        assert not app.exception
        assert plot.config["shapes"] == before
        assert [
            item.to_plotly_json() for item in plot.last_generated_fig.layout.shapes
        ] == native_before
        keys = {widget.key for widget in app.text_input}
        for field in ("x0", "y0", "x1", "y1"):
            assert (_row(plot, field) in keys) is (field in shape and shape[field] is not None)
        assert shape == original
        _measurements(plot)
    finally:
        api.close()


@pytest.mark.parametrize("auto_refresh", [False, True])
def test_deleting_the_invalid_row_skips_its_decoder_and_retains_manual_refresh_contract(
    auto_refresh: bool,
) -> None:
    # [test->req~ring5.figure.shapes-annotations~1]
    app, api, plot = _app([_shape()])
    try:
        _advanced(app, plot)
        app.toggle(key=f"plot.{plot.plot_id}.widgets.auto_refresh").set_value(auto_refresh).run()
        app.text_input(key=_row(plot, "y0")).set_value("nan").run()
        assert app.exception
        app.button(
            key=f"plot.{plot.plot_id}.widgets.appearance.shape_rows.del_shape_0"
        ).click().run()
        assert not app.exception
        if not auto_refresh:
            assert len(plot.config["shapes"]) == 1
            app.button(key=f"plot.{plot.plot_id}.widgets.refresh").click().run()
        assert not app.exception
        assert plot.config["shapes"] == []
        assert not plot.last_generated_fig.layout.shapes
        _measurements(plot)
    finally:
        api.close()


def test_deleting_invalid_partial_row_preserves_retained_row_types_and_extra_fields() -> None:
    retained = {**_shape(), "xref": "x", "yref": "y"}
    app, api, plot = _app([{"type": "line", "x0": 0.0, "x1": 1.0}, retained])
    try:
        _advanced(app, plot)
        app.text_input(key=_row(plot, "x0")).set_value("nan").run()
        assert app.exception
        app.button(
            key=f"plot.{plot.plot_id}.widgets.appearance.shape_rows.del_shape_0"
        ).click().run()
        app.run()
        assert not app.exception
        assert plot.config["shapes"] == [retained]
        assert app.checkbox(key=_row(plot, "x0") + ".text_mode").value is True
        assert plot.last_generated_fig.layout.shapes[0].x0 == "001"
        _measurements(plot)
    finally:
        api.close()


def test_delete_still_rejects_invalid_coordinates_in_a_retained_row() -> None:
    app, api, plot = _app([_shape(), _shape()])
    try:
        _advanced(app, plot)
        app.text_input(key=_row(plot, "y0", 1)).set_value("nan").run()
        assert app.exception
        app.button(
            key=f"plot.{plot.plot_id}.widgets.appearance.shape_rows.del_shape_0"
        ).click().run()
        assert any("Shape 2 y0" in error.message for error in app.exception)
        assert len(plot.config["shapes"]) == 2
        app.text_input(key=_row(plot, "y0", 1)).set_value("14.25").run()
        app.button(
            key=f"plot.{plot.plot_id}.widgets.appearance.shape_rows.del_shape_0"
        ).click().run()
        assert not app.exception
        assert len(plot.config["shapes"]) == 1
        assert plot.config["shapes"][0]["y0"] == 14.25
        assert plot.last_generated_fig.layout.shapes[0].y0 == 14.25
        _measurements(plot)
    finally:
        api.close()


@pytest.mark.parametrize("text", ["001", "003", "nan", "inf", "", "1e-400"])
def test_literal_coordinates_never_infer_numeric_or_missing_meaning(text: str) -> None:
    assert _decode_coordinate(text, True, 0.0) == text


@pytest.mark.parametrize(
    "number", [9007199254740993, 1.25, -0.0, float.fromhex("0x1.fffffffffffffp1023")]
)
def test_untouched_numeric_coordinates_keep_their_exact_original_value(number: float) -> None:
    result = _decode_coordinate(str(number), False, number)
    assert result is number
    if number == 0:
        assert math.copysign(1, result) == math.copysign(1, number)


@pytest.mark.parametrize(
    "text", ["", "unfinished", "nan", "inf", "-inf", "1e309", "1e-400", "-1e-400"]
)
def test_invalid_nonfinite_and_underflowing_number_coordinates_are_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        _decode_coordinate(text, False, 0.0)


@pytest.mark.parametrize("text", ["12.5", "3", "5e-324", "-2e-320"])
def test_explicit_numbers_retain_fractional_and_representable_subnormal_values(text: str) -> None:
    assert _decode_coordinate(text, False, 0.0) == float(text)
