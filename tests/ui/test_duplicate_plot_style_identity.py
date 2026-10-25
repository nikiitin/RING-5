"""A duplicated strategy owns the destination's actual Colors series controls."""

from copy import deepcopy
from typing import Any, override

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

import ring5
from src.web.pages.ui.plotting.plot_service import PlotService
from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI
from src.web.state.ui_state_manager import WidgetKeyBuilder


class _CustomBarStyle(BarStyleUI):
    def __init__(self, plot_id: int) -> None:
        super().__init__(plot_id, "bar")
        self.custom_state: dict[str, Any] = {"preference": ["kept"], "rendered_ids": []}

    @override
    def _render_specific_series_visuals(
        self, current_style: dict[str, Any], key_suffix: str, key_prefix: str = ""
    ) -> None:
        super()._render_specific_series_visuals(current_style, key_suffix, key_prefix)
        current_style["custom_marker"] = st.toggle(
            "Custom marker", value=True, key=f"{key_prefix}custom_{self.plot_id}_{key_suffix}"
        )
        self.custom_state["rendered_ids"].append(self.plot_id)


_APP = """
from copy import deepcopy
import streamlit as st
plot = st.session_state["plot"]
st.session_state["emitted"] = plot.render_settings_section(
    "colors", deepcopy(plot.config), plot.processed_data
)
"""


def test_duplicate_colors_use_the_new_strategy_instance_id_and_preserve_source_custom_state() -> (
    None
):
    # [test->req~ring5.plots.duplicate~1]
    with ring5.Session() as session:
        source = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]})),
            config={
                "x": "x",
                "y": "y",
                "y_columns": ["y"],
                "series_styles": {"y": {"pattern": "/"}},
            },
        )
        custom = _CustomBarStyle(source.plot_id)
        source._style_ui = custom
        original_state = deepcopy(custom.custom_state)
        duplicate = PlotService.duplicate_plot(source, session.api.state_manager)
        assert type(duplicate._style_ui) is _CustomBarStyle
        assert duplicate._style_ui is not custom
        assert duplicate._style_ui.plot_id == duplicate.plot_id != source.plot_id
        app = AppTest.from_string(_APP)
        app.session_state["plot"] = duplicate
        app.run()
        assert not app.exception
        controls = [
            widget
            for widget in [*app.selectbox, *app.toggle]
            if widget.label in ("Pattern", "Custom marker")
        ]
        assert {widget.label for widget in controls} == {"Pattern", "Custom marker"}
        assert all(
            widget.key.startswith(
                WidgetKeyBuilder.plot_key(duplicate.plot_id, "widgets.appearance.series") + "."
            )
            for widget in controls
        )
        assert all(not widget.key.startswith(f"plot.{source.plot_id}.") for widget in controls)
        cloned_style = duplicate._style_ui
        assert cloned_style.custom_state == {
            "preference": ["kept"],
            "rendered_ids": [duplicate.plot_id],
        }
        assert custom.custom_state == original_state
        assert custom.plot_id == source.plot_id
        assert app.session_state["emitted"]["series_styles"]["y"]["custom_marker"] is True
        assert source.config["series_styles"] == {"y": {"pattern": "/"}}
