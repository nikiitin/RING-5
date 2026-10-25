"""Actual facade and AppTest regressions for retained previews and report downloads."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

_PREPROCESSOR_APP = """
import pandas as pd
import streamlit as st
from src.core.application_api import ApplicationAPI
from src.web.components.data_managers.preprocessor import PreprocessorManager
if "api" not in st.session_state:
    api = ApplicationAPI()
    api.add_dataset("A", pd.DataFrame({"x": [1.0], "y": [2.0]}))
    api.add_dataset("B", pd.DataFrame({"x": [100.0], "y": [200.0]}), select=False)
    st.session_state["api"] = api
api = st.session_state["api"]
if st.button("Switch source", key="switch"):
    api.select_dataset("B")
if st.button("Revise source", key="revise"):
    api.update_selected_dataset(
        pd.DataFrame({"x": [99.0], "y": [100.0]}), operation="Revise source")
PreprocessorManager(api).render()
"""


def _preview() -> AppTest:
    app = AppTest.from_string(_PREPROCESSOR_APP).run()
    assert not app.exception
    app.selectbox(key="manager.preprocessor.src2").select("y").run()
    operators = app.selectbox(key="manager.preprocessor.op").options
    summation = next(option for option in operators if option.lower() in {"sum", "add"})
    app.selectbox(key="manager.preprocessor.op").select(summation).run()
    app.text_input(key="manager.preprocessor.name").set_value("sum").run()
    app.button(key="manager.preprocessor.preview").click().run()
    assert not app.exception
    assert app.session_state["api"].has_preview("preprocessor")
    assert app.session_state["api"].get_preview("preprocessor")["sum"].tolist() == [3.0]
    return app


@pytest.mark.parametrize("change", ["switch", "revise", "parameters"])
def test_manager_previews_cannot_replace_changed_sources_or_use_changed_parameters(
    change: str,
) -> None:
    app = _preview()
    api = app.session_state["api"]
    try:
        if change == "parameters":
            app.text_input(key="manager.preprocessor.name").set_value("another").run()
        else:
            app.button(key=change).click().run()
        assert not app.exception
        assert not api.has_preview("preprocessor")
        assert not any(button.key == "manager.preprocessor.confirm" for button in app.button)
        assert "sum" not in api.state_manager.get_data()
        if change == "switch":
            pd.testing.assert_frame_equal(
                api.get_dataset("B"), pd.DataFrame({"x": [100.0], "y": [200.0]})
            )
        elif change == "revise":
            assert api.get_dataset("A")["x"].tolist() == [99.0]
    finally:
        api.close()


def test_manager_confirmation_uses_the_preview_configuration_for_history() -> None:
    app = _preview()
    api = app.session_state["api"]
    try:
        app.button(key="manager.preprocessor.confirm").click().run()
        assert not app.exception
        assert api.get_dataset("A")["sum"].tolist() == [3.0]
        assert api.get_dataset("B")["x"].tolist() == [100.0]
        assert not api.has_preview("preprocessor")
        record = api.get_manager_history()[-1]
        assert record["source_columns"] == ["x", "y"]
        assert record["dest_columns"] == ["sum"]
    finally:
        api.close()


_REPORT_APP = """
from unittest.mock import patch
import pandas as pd
import streamlit as st
from src.core.application_api import ApplicationAPI
from src.web.components.report_composer import ReportComposer
from src.web.pages.ui.plotting.plot_factory import PlotFactory
if "api" not in st.session_state:
    api = ApplicationAPI()
    data = pd.DataFrame({"label": ["A"], "value": [1.0]})
    api.add_dataset("active", data)
    plot = PlotFactory.create_plot("bar", 1, "Bars")
    plot.config = {**plot.config, "x": "label", "y": "value"}
    plot.replace_source_data(data)
    plot.replace_processed_data(data)
    api.state_manager.add_plot(plot)
    st.session_state["api"] = api
    st.session_state["held_data"] = []
api = st.session_state["api"]
plot = api.state_manager.get_plots()[0]
if st.button("Change plot", key="plot_change"):
    plot.config = {**plot.config, "title": "Updated title"}
if st.button("Change pipeline", key="pipeline_change"):
    plot.pipeline = [{"id": 0, "type": "sort",
                      "config": {"type": "sort", "order_dict": {"label": ["A"]}}}]
if st.button("Change table", key="data_change"):
    api.update_selected_dataset(
        pd.DataFrame({"label": ["A"], "value": [7.0]}), operation="Revise table")
original_get_data = api.state_manager.get_data
# Retain every defensive copy so object-id reuse cannot hide the original bug.
def retained_get_data():
    frame = original_get_data()
    st.session_state["held_data"].append(frame)
    return frame
def render_payload(*args, **kwargs):
    if st.session_state.get("change_while_rendering", False):
        plot.config = {**plot.config, "title": "Changed during rendering"}
    return b"<html>ready</html>"
with patch.object(api.state_manager, "get_data", side_effect=retained_get_data), \\
     patch("src.web.components.report_composer.render_report", side_effect=render_payload):
    ReportComposer(api).render()
"""


@pytest.mark.parametrize("change", ["plot_change", "pipeline_change", "data_change"])
def test_report_download_survives_unchanged_reruns_and_invalidates_all_report_inputs(
    change: str,
) -> None:
    app = AppTest.from_string(_REPORT_APP).run()
    api = app.session_state["api"]
    try:
        assert not app.exception
        app.button(key="report.composer.build").click().run()
        assert not app.exception
        assert len(app.get("download_button")) == 1
        app.run()
        assert not app.exception
        assert len(app.get("download_button")) == 1
        app.button(key=change).click().run()
        assert not app.exception
        assert len(app.get("download_button")) == 0
        assert any("settings changed" in message.value.lower() for message in app.info)
    finally:
        api.close()


@pytest.mark.parametrize("change", ["revise_portfolio", "replace_snapshot"])
def test_prepared_bundle_tracks_saved_portfolio_and_snapshot_replacements(
    change: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core.services.data_services.path_service import PathService

    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "workspace"))
    PathService.reset_caches()
    app = AppTest.from_string(dedent("""
        import pandas as pd
        import streamlit as st
        from src.core.application_api import ApplicationAPI
        from src.web.pages.portfolio import _render_bundle_download
        if "api" not in st.session_state:
            api = ApplicationAPI()
            data = pd.DataFrame({"value": [1.0]})
            api.add_dataset("active", data)
            api.data_services.save_portfolio("analysis", data, [], {}, 0)
            api.save_dataset_snapshot("exact")
            st.session_state["api"] = api
            st.session_state["portfolio_bundle_snapshot.analysis"] = "exact"
        api = st.session_state["api"]
        if st.button("Revise portfolio", key="revise_portfolio"):
            revised = pd.DataFrame({"value": [2.0]})
            api.data_services.save_portfolio("analysis", revised, [], {}, 0)
        if st.button("Replace snapshot", key="replace_snapshot"):
            api.update_selected_dataset(
                pd.DataFrame({"value": [3.0]}), operation="Replace snapshot")
            api.save_dataset_snapshot("exact", overwrite=True)
        _render_bundle_download(api, "analysis")
    """)).run()
    api = app.session_state["api"]
    try:
        assert not app.exception
        app.button(key="portfolio_bundle_prepare.analysis").click().run()
        assert not app.exception
        assert len(app.get("download_button")) == 1
        app.run()
        assert len(app.get("download_button")) == 1
        app.button(key=change).click().run()
        assert not app.exception
        assert len(app.get("download_button")) == 0
    finally:
        api.close()
        PathService.reset_caches()


def test_report_refuses_an_artifact_when_inputs_change_during_rendering() -> None:
    app = AppTest.from_string(_REPORT_APP).run()
    api = app.session_state["api"]
    try:
        app.session_state["change_while_rendering"] = True
        app.button(key="report.composer.build").click().run()
        assert not app.exception
        assert len(app.get("download_button")) == 0
        assert "report.composer.bytes" not in app.session_state
        assert any("changed while rendering" in message.value for message in app.warning)
    finally:
        api.close()
