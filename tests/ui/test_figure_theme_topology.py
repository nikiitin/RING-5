"""Conditional theme feedback keeps the live chart at one stable Streamlit delta path."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, cast

from streamlit.testing.v1 import AppTest

from src.core.services.visualization.figure_theme_service import FigureThemeService

_SCRIPT = """
import plotly.graph_objects as go
import streamlit as st

from src.web.components.plotting.interactive_plot import interactive_plotly_chart
from src.web.components.plotting.settings.theme_presets_settings import (
    ThemePresetsSettingsComponent,
)

saved = st.session_state.setdefault("saved_theme_config", {
    "x": "phase", "y": "ipc", "title": "Theme topology",
})
result = ThemePresetsSettingsComponent(7, "bar").render(saved)
st.session_state["last_theme_result"] = dict(result)
if result:
    result.pop("_ring5_request_refresh", None)
    st.session_state["saved_theme_config"] = {**saved, **result}
saved = st.session_state["saved_theme_config"]
st.text_input("Unrelated pending note", key="pending_theme_note")
figure = go.Figure(
    data=[go.Bar(x=["a"], y=[2])],
    layout={"title": saved["title"],
            "paper_bgcolor": saved.get("paper_bgcolor", "#ffffff"),
            "plot_bgcolor": saved.get("plot_bgcolor", "#ffffff")},
)
interactive_plotly_chart(figure, key="theme-topology-chart")
"""


def _chart_position(app: AppTest) -> tuple[int, str]:
    """Read the real custom component's main-block delta index and widget identity."""
    charts = app.get("component_instance")
    assert len(charts) == 1
    chart = cast(Any, charts[0])
    assert chart.proto.component_name.endswith("interactive_plotly")
    position = next(index for index, node in app.main.children.items() if node is chart)
    return position, str(chart.proto.id)


def _assert_retained(
    app: AppTest,
    position: tuple[int, str],
    saved: dict[str, Any],
) -> None:
    """Keep the chart, saved configuration and unrelated draft intact."""
    assert not app.exception
    assert _chart_position(app) == position
    assert app.session_state["saved_theme_config"] == saved
    assert app.session_state["last_theme_result"] == {}
    assert app.text_input(key="pending_theme_note").value == "Pending independent note"


def test_upload_review_rejection_and_clear_keep_the_custom_chart_delta_path() -> None:
    """Removing imported feedback and Apply controls cannot relocate a retained iframe."""
    app = AppTest.from_string(_SCRIPT, default_timeout=15).run()
    assert not app.exception
    app.selectbox[0].select("dark").run()
    next(button for button in app.button if button.label == "Apply theme").click().run()
    app.run()
    assert not app.exception
    app.text_input(key="pending_theme_note").set_value("Pending independent note").run()
    position = _chart_position(app)
    saved = deepcopy(app.session_state["saved_theme_config"])
    assert saved["paper_bgcolor"] == "#161a24"
    assert saved["plot_bgcolor"] == "#202633"
    assert (saved["x"], saved["y"]) == ("phase", "ipc")
    theme = FigureThemeService.dumps(FigureThemeService.get("paper"))

    app.file_uploader[0].set_value(("review.ring5-theme.json", theme, "application/json")).run()
    _assert_retained(app, position, saved)
    assert any("Imported Publication paper" in notice.value for notice in app.success)
    assert any(button.label == "Apply imported theme" for button in app.button)

    invalid = json.loads(theme)
    invalid["config"]["x"] = "other_source"
    app.file_uploader[0].set_value(
        (
            "rejected.ring5-theme.json",
            json.dumps(invalid).encode(),
            "application/json",
        )
    ).run()
    _assert_retained(app, position, saved)
    assert [notice.value for notice in app.error] == [
        "Figure themes cannot contain data or unsupported keys: x"
    ]
    assert not any(button.label == "Apply imported theme" for button in app.button)

    app.file_uploader[0].set_value(None).run()
    _assert_retained(app, position, saved)
    assert not app.error
    assert not app.success
    assert not any(button.label == "Apply imported theme" for button in app.button)


def test_apply_feedback_and_new_active_theme_keep_the_custom_chart_delta_path() -> None:
    """Transient Apply feedback and persistent active-theme information have stable slots."""
    app = AppTest.from_string(_SCRIPT, default_timeout=15).run()
    assert not app.exception
    app.text_input(key="pending_theme_note").set_value("Pending independent note").run()
    position = _chart_position(app)
    app.selectbox[0].select("dark").run()
    assert _chart_position(app) == position
    next(button for button in app.button if button.label == "Apply theme").click().run()
    assert not app.exception
    assert _chart_position(app) == position
    assert [notice.value for notice in app.success] == [
        "Applied Dark background. Data mappings and filters were kept."
    ]
    saved = deepcopy(app.session_state["saved_theme_config"])
    assert saved["figure_theme_id"] == "dark"
    assert saved["paper_bgcolor"] == "#161a24"
    assert (saved["x"], saved["y"]) == ("phase", "ipc")

    app.run()
    _assert_retained(app, position, saved)
    assert not app.success
    assert any("Active theme: Dark background." in notice.value for notice in app.info)
