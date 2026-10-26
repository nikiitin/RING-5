"""Actual legend widgets emit one labels map without changing raw series styles."""

from collections.abc import Iterator
from copy import deepcopy
from typing import Any

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from ring5 import Session, Table

_APP = """
import copy
import streamlit as st
from src.web.components.plotting.settings.legend_settings import LegendSettingsComponent
plot = st.session_state["plot"]
saved = plot.config
before = copy.deepcopy(saved)
result = LegendSettingsComponent(plot.plot_id, plot.plot_type).render(
    saved, plot.processed_data,
)
st.session_state["source_unchanged"] = saved == before
st.session_state["emitted"] = result
plot.config = {**saved, **result}
"""


@pytest.fixture
def session() -> Iterator[Session]:
    with Session() as owner:
        yield owner


def _app(session: Session, kind: str, config: dict[str, Any]) -> AppTest:
    frame = pd.DataFrame(
        {
            "x": ["one", "two"],
            "group": ["A", "B"],
            "A": [3.0, 5.0],
            "B": [7.0, 9.0],
            "R": [11.0, 13.0],
        }
    )
    plot = session.create_plot(kind, data=Table(frame), config=config)
    app = AppTest.from_string(_APP)
    app.session_state["plot"] = plot
    app.run()
    assert not app.exception
    assert app.session_state["source_unchanged"]
    return app


def _rename(app: AppTest, original: str, display: str) -> None:
    widgets = [widget for widget in app.text_input if widget.label == original]
    assert len(widgets) == 1
    widgets[0].set_value(display).run()
    assert not app.exception
    assert app.session_state["source_unchanged"]


@pytest.mark.parametrize(
    "kind,extra",
    [
        ("bar", {"y_columns": ["A", "B"]}),
        ("stacked_bar", {"y_columns": ["A", "B"]}),
        ("grouped_stacked_bar", {"y_columns": ["A", "B"]}),
        ("grouped_bar", {"group": "group"}),
        ("bar", {"color": "group"}),
    ],
)
def test_real_series_and_category_rename_share_canonical_labels(
    session: Session, kind: str, extra: dict[str, Any]
) -> None:
    styles = {
        "A": {"color": "#ff0000", "use_color": True, "pattern": "/"},
        "B": {"color": "#0000ff", "use_color": True, "pattern": ""},
        "inactive": {"symbol": "diamond"},
    }
    app = _app(
        session,
        kind,
        {
            "x": "x",
            "y": "A",
            "legend_labels": {"A": "Existing", "inactive": "Unselected"},
            "series_styles": deepcopy(styles),
            **extra,
        },
    )
    assert next(widget for widget in app.text_input if widget.label == "A").value == "Existing"
    _rename(app, "A", "Same")
    _rename(app, "B", "Same")
    plot = app.session_state["plot"]
    assert plot.config["legend_labels"] == {"A": "Same", "B": "Same", "inactive": "Unselected"}
    assert plot.config["series_styles"] == styles
    assert all("name" not in style for style in plot.config["series_styles"].values())
    app.run()
    _rename(app, "A", "")
    assert plot.config["legend_labels"] == {"B": "Same", "inactive": "Unselected"}
    assert plot.config["series_styles"] == styles


def test_real_reorder_preserves_raw_identity_and_value_keyed_rename_widgets(
    session: Session,
) -> None:
    app = _app(
        session,
        "stacked_bar",
        {"x": "x", "y_columns": ["A", "B"], "legend_labels": {"A": "Alpha", "B": "Beta"}},
    )
    app.button(key="plot.0.widgets.appearance.legend_items_up_1").click().run()
    assert not app.exception
    plot = app.session_state["plot"]
    assert plot.config["y_columns"] == ["B", "A"]
    assert plot.config["legend_labels"] == {"A": "Alpha", "B": "Beta"}
    assert [widget.value for widget in app.text_input if widget.label in ("A", "B")] == [
        "Beta",
        "Alpha",
    ]
    _rename(app, "A", "Changed")
    assert plot.config["legend_labels"] == {"A": "Changed", "B": "Beta"}


def test_real_separate_and_unified_legends_preserve_one_map_across_navigation(
    session: Session,
) -> None:
    styles = {"A": {"color": "red", "use_color": True}, "R": {"color": "blue", "use_color": True}}
    app = _app(
        session,
        "grouped_stacked_bar",
        {
            "x": "x",
            "y_columns": ["A"],
            "dual_axis": True,
            "y_columns_right": ["R"],
            "unified_legend": False,
            "series_styles": deepcopy(styles),
            "legend_labels": {"inactive": "Retained"},
        },
    )
    _rename(app, "A", "Left")
    app.button_group(key="plot.0.widgets.appearance.legend_nav").set_value("secondary").run()
    _rename(app, "R", "Right")
    app.button_group(key="plot.0.widgets.appearance.legend_nav").set_value("primary").run()
    assert next(widget for widget in app.text_input if widget.label == "A").value == "Left"
    app.checkbox(key="plot.0.widgets.appearance.unified_legend").check().run()
    assert not app.exception
    assert {
        widget.label: widget.value for widget in app.text_input if widget.label in ("A", "R")
    } == {"A": "Left", "R": "Right"}
    _rename(app, "R", "Updated")
    plot = app.session_state["plot"]
    assert plot.config["legend_labels"] == {"A": "Left", "R": "Updated", "inactive": "Retained"}
    assert plot.config["legend_order"] == ["A", "R"]
    assert plot.config["series_styles"] == styles
