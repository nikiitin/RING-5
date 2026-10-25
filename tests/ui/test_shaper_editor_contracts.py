"""Current shaper editors retain typed operands and runnable behavior on rerun."""

from __future__ import annotations

import json
from textwrap import dedent

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


def _editor(kind: str, values: dict, saved: dict) -> AppTest:
    app = AppTest.from_string(dedent(f"""
        import streamlit as st
        import pandas as pd
        from src.web.pages.ui.shaper_config import configure_shaper
        from src.core.services.shapers.pipeline_service import PipelineService
        frame = pd.DataFrame({values!r})
        saved = {saved!r}
        st.session_state['before'] = PipelineService.process_pipeline(frame, [saved])
        configured = configure_shaper(
            {kind!r}, frame, 1, saved, owner_id=1, display_names={{}})
        st.session_state['configured'] = configured
        st.session_state['after'] = PipelineService.process_pipeline(frame, [configured])
    """)).run()
    assert not app.exception
    return app


def _unchanged(app: AppTest) -> None:
    assert not app.exception
    pd.testing.assert_frame_equal(app.session_state["before"], app.session_state["after"])


def test_mapping_editor_retains_json_scalar_values_and_typed_edits() -> None:
    saved = {
        "type": "deriveColumn",
        "op": "map",
        "dest": "value",
        "sources": ["key"],
        "mapping": {"a": 2.5, "b": False, "c": None},
    }
    app = _editor("deriveColumn", {"key": ["a", "b", "c"]}, saved)
    _unchanged(app)
    assert [type(value) for value in app.session_state["configured"]["mapping"].values()] == [
        float,
        bool,
        type(None),
    ]
    app.run()
    _unchanged(app)
    app.text_area(key="p1_dc_map_1").set_value(json.dumps({"a": 7, "b": True, "c": None})).run()
    assert not app.exception
    mapping = app.session_state["configured"]["mapping"]
    assert type(mapping["a"]) is int and mapping["a"] == 7
    assert mapping["b"] is True and mapping["c"] is None
    assert app.session_state["after"]["value"].tolist() == [7, True, None]
    app.text_area(key="p1_dc_map_1").set_value("[" * 2_000 + "]" * 2_000).run()
    assert not app.exception
    assert app.error
    _unchanged(app)


@pytest.mark.parametrize(
    "pattern,groups", [(r"cpu(\d+)", [0]), (r"cpu\d+", [0]), (r"cpu(\d+)", [1])]
)
def test_whole_match_filter_survives_independently_of_output_groups(pattern, groups) -> None:
    saved = {
        "type": "pivotLonger",
        "id_vars": ["id"],
        "value_vars": ["cpu0", "cpu1"],
        "var_name": "metric",
        "value_name": "value",
        "extract_pattern": pattern,
        "extract_group_indices": groups,
        "selection_filters": {"0": ["cpu0"]},
    }
    app = _editor("pivotLonger", {"id": ["x"], "cpu0": [1.0], "cpu1": [2.0]}, saved)
    _unchanged(app)
    assert app.session_state["configured"]["selection_filters"] == {"0": ["cpu0"]}
    assert len(app.session_state["after"]) == 1
    app.run()
    _unchanged(app)


def test_omitted_normalizer_variables_retain_constructor_default() -> None:
    saved = {
        "type": "normalize",
        "normalizeVars": ["v"],
        "normalizerColumn": "policy",
        "normalizerValue": "base",
        "groupBy": ["bench"],
    }
    app = _editor(
        "normalize", {"bench": ["a", "a"], "policy": ["base", "other"], "v": [2.0, 6.0]}, saved
    )
    _unchanged(app)
    assert "normalizerVars" not in app.session_state["configured"]
    assert app.multiselect(key="p1_normalizer_vars_1").value == ["v"]
    app.run()
    _unchanged(app)


def test_numeric_saved_baseline_column_and_value_remain_selected() -> None:
    saved = {
        "type": "normalize",
        "normalizeVars": ["v"],
        "normalizerVars": ["v"],
        "normalizerColumn": "policy",
        "normalizerValue": 0,
        "groupBy": ["bench"],
    }
    app = _editor("normalize", {"bench": ["a", "a"], "policy": [0, 1], "v": [2.0, 6.0]}, saved)
    _unchanged(app)
    config = app.session_state["configured"]
    assert config["normalizerColumn"] == "policy"
    assert type(config["normalizerValue"]) is int and config["normalizerValue"] == 0
    app.run()
    _unchanged(app)
