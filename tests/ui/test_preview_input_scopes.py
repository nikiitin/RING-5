"""Named-comparison widgets display only results of their current reviewed inputs."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

_SCRIPT = """
import streamlit as st
import pandas as pd
from src.core.application_api import ApplicationAPI
from src.web.components.data_managers.dataset_workspace import DatasetWorkspaceManager
if "api" not in st.session_state:
    api = ApplicationAPI()
    for name, value in [("baseline", 10.0), ("candidate", 20.0), ("other", 30.0)]:
        api.add_dataset(name, pd.DataFrame({"key": ["a", "b"], "suite": ["one", "two"],
                                           "v": [value, value + 1], "w": [value * 2, value * 3]}),
                        select=name == "baseline")
    st.session_state["api"] = api
api = st.session_state["api"]
DatasetWorkspaceManager(api)._render_compare([info.name for info in api.list_datasets()])
"""
_KEY = "workspace_dataset_comparison"


@pytest.fixture
def app() -> Any:
    current = AppTest.from_string(_SCRIPT).run()
    try:
        assert not current.exception
        current.multiselect(key="manager.workspace.compare_keys").set_value(["key"]).run()
        current.multiselect(key="manager.workspace.compare_metrics").set_value(["v"]).run()
        current.button(key="manager.workspace.compare_apply").click().run()
        assert not current.exception
        assert len(current.dataframe) == 1
        assert current.dataframe[0].value["candidate_value"].tolist() == [20.0, 21.0]
        yield current
    finally:
        current.session_state["api"].close(wait=True)


@pytest.mark.parametrize(
    ("kind", "key", "value"),
    [
        ("selectbox", "compare_left", "other"),
        ("selectbox", "compare_right", "other"),
        ("multiselect", "compare_keys", ["suite"]),
        ("multiselect", "compare_metrics", ["w"]),
        ("selectbox", "compare_direction", "Lower is better"),
        ("number_input", "compare_threshold", 7.0),
    ],
)
def test_changed_comparison_controls_hide_stale_results_until_recomputed(
    app: Any, kind: str, key: str, value: Any
) -> None:
    # [test->req~ring5.data.preview-confirm~1]
    control = getattr(app, kind)(key=f"manager.workspace.{key}")
    control.set_value(value).run()
    assert not app.exception
    assert len(app.dataframe) == 0
    assert not app.session_state["api"].has_preview(_KEY)
    assert any("sources or settings changed" in info.value for info in app.info)
    app.button(key="manager.workspace.compare_apply").click().run()
    assert not app.exception
    assert len(app.dataframe) == 1
    assert app.session_state["api"].has_preview(_KEY)


@pytest.mark.parametrize("name", ["baseline", "candidate"])
def test_replaced_named_source_hides_old_values_and_recomputation_uses_new_rows(
    app: Any, name: str
) -> None:
    api = app.session_state["api"]
    updated = api.get_dataset(name)
    updated["v"] = [70.0, 71.0]
    api.add_dataset(name, updated, replace=True, select=False)
    app.run()
    assert not app.exception
    assert len(app.dataframe) == 0
    assert not api.has_preview(_KEY)
    app.button(key="manager.workspace.compare_apply").click().run()
    assert not app.exception
    column = "baseline_value" if name == "baseline" else "candidate_value"
    assert app.dataframe[0].value[column].tolist() == [70.0, 71.0]


def test_unrelated_dataset_edits_and_active_selection_keep_current_named_result(app: Any) -> None:
    api = app.session_state["api"]
    before = app.dataframe[0].value.copy(deep=True)
    other = api.get_dataset("other")
    other["v"] = [99.0, 100.0]
    api.add_dataset("other", other, replace=True)
    app.run()
    assert not app.exception
    assert len(app.dataframe) == 1
    pd.testing.assert_frame_equal(app.dataframe[0].value, before)
    assert api.has_preview(_KEY)
