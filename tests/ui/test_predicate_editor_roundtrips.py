"""Current predicate widgets preserve saved scientific operands and row selection."""

from __future__ import annotations

from textwrap import dedent
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest


def _app(config: dict[str, Any], values: str = "[1, 2, 3]", *, execute: bool = True) -> AppTest:
    execution = (
        """
from src.core.services.shapers.impl.selector_algorithms.condition_selector import ConditionSelector
st.session_state["rows"] = ConditionSelector(st.session_state["config"])(frame).index.tolist()
"""
        if execute
        else ""
    )
    return AppTest.from_string(dedent(f"""
import pandas as pd
import streamlit as st
from src.web.components.shapers.selector_transformer_configs import ConditionSelectorConfig
frame = pd.DataFrame({{"x": {values}}})
st.session_state.setdefault("config", {config!r})
result = ConditionSelectorConfig.render(frame, st.session_state["config"], "p7_", 3)
st.session_state["config"] = {{"type": "conditionSelector", **result}}
{execution}
""")).run()


@pytest.mark.parametrize(
    "operand,rows",
    [
        ({"mode": "greater_than", "threshold": 2}, [2]),
        ({"mode": "less_than", "threshold": 2}, [0]),
        ({"mode": "greater_or_equal", "threshold": 2}, [1, 2]),
        ({"mode": "less_or_equal", "threshold": 2}, [0, 1]),
        ({"mode": "equals", "value": 2}, [1]),
        ({"mode": "not_equals", "value": 2}, [0, 2]),
        ({"mode": "range", "range": [0, 2]}, [0, 1]),
        ({"mode": "in", "values": [2]}, [1]),
        ({"mode": "in", "values": []}, []),
        ({"mode": "in", "values": [4, 2]}, [1]),
        ({"mode": "contains", "value": "2"}, [1]),
    ],
)
def test_every_current_numeric_mode_round_trips_without_editing(
    operand: dict[str, Any], rows: list[int]
) -> None:
    config = {"type": "conditionSelector", "column": "x", **operand}
    app = _app(config)
    for _ in range(2):
        assert not app.exception
        assert not app.error
        assert app.session_state["config"] == config
        assert app.session_state["rows"] == rows
        app.run()


@pytest.mark.parametrize(
    "values,operand,rows",
    [
        ('["beta", "\'beta\'", "other"]', {"mode": "equals", "value": "'beta'"}, [1]),
        ('["a[0]", "a0"]', {"mode": "contains", "value": "["}, [0]),
        ("pd.Categorical([1, 2, 3])", {"mode": "in", "values": [2]}, [1]),
        ("pd.Categorical([1, 2, 3])", {"mode": "equals", "value": 2}, [1]),
        ('pd.Series([1, "1", True], dtype=object)', {"mode": "in", "values": ["1"]}, [1]),
        ('pd.Series([1, "1", True], dtype=object)', {"mode": "in", "values": [1]}, [0, 2]),
        ("[True, False, True]", {"mode": "equals", "value": False}, [1]),
        ('pd.Series(["a", None], dtype=object)', {"mode": "in", "values": [None]}, [1]),
    ],
)
def test_literal_and_membership_types_survive_actual_widgets(
    values: str, operand: dict[str, Any], rows: list[int]
) -> None:
    config = {"type": "conditionSelector", "column": "x", **operand}
    app = _app(config, values)
    assert not app.exception
    assert not app.error
    assert app.session_state["config"] == config
    assert app.session_state["rows"] == rows
    app.run()
    assert not app.exception
    assert app.session_state["config"] == config


def test_switching_mode_emits_only_the_new_operand() -> None:
    app = _app({"column": "x", "mode": "greater_or_equal", "threshold": 2})
    app.selectbox(key="p7_filter_mode_3").set_value("not_equals").run()
    assert not app.exception
    assert "threshold" not in app.session_state["config"]
    app.number_input(key="p7_filter_value_not_equals_3").set_value(2).run()
    assert app.session_state["config"] == {
        "type": "conditionSelector",
        "column": "x",
        "mode": "not_equals",
        "value": 2,
    }
    assert app.session_state["rows"] == [0, 2]


def test_integer_bound_can_be_changed_to_a_fraction_without_rounding() -> None:
    app = _app({"column": "x", "mode": "greater_or_equal", "threshold": 2})
    app.number_input(key="p7_filter_threshold_greater_or_equal_3").set_value(2.5).run()
    assert not app.exception
    assert app.session_state["config"]["threshold"] == 2.5
    assert app.session_state["rows"] == [2]


def test_literal_quotes_remain_editable_without_interpretation() -> None:
    app = _app(
        {"column": "x", "mode": "equals", "value": "'beta'"}, '["beta", "\'beta\'", \'"beta"\']'
    )
    app.text_input(key="p7_filter_value_equals_3").set_value('"beta"').run()
    assert not app.exception
    assert app.session_state["config"]["value"] == '"beta"'
    assert app.session_state["rows"] == [2]


def test_membership_widgets_keep_typed_selection_when_observed_values_reorder() -> None:
    app = AppTest.from_string(dedent("""
        import pandas as pd
        import streamlit as st
        from src.web.components.shapers.selector_transformer_configs import ConditionSelectorConfig
        reverse = st.checkbox("Reverse rows", key="reverse")
        values = [1, "1", 2]
        if reverse:
            values.reverse()
        frame = pd.DataFrame({"x": pd.Series(values, dtype=object)})
        st.session_state.setdefault("config", {"column": "x", "mode": "in", "values": [1]})
        st.session_state["config"] = ConditionSelectorConfig.render(
            frame, st.session_state["config"], "p7_", 3
        )
    """)).run()
    assert not app.exception
    app.checkbox(key="reverse").check().run()
    assert not app.exception
    assert app.session_state["config"]["values"] == [1]
    assert type(app.session_state["config"]["values"][0]) is int


def test_predicate_widgets_are_isolated_by_plot_owner() -> None:
    app = AppTest.from_string(dedent("""
        import pandas as pd
        import streamlit as st
        from src.web.components.shapers.selector_transformer_configs import ConditionSelectorConfig
        frame = pd.DataFrame({"x": [1, 2, 3]})
        for owner, bound in [(7, 2), (8, 3)]:
            key = f"config{owner}"
            st.session_state.setdefault(key, {"column": "x", "mode": "greater_or_equal",
                                             "threshold": bound})
            st.session_state[key] = ConditionSelectorConfig.render(
                frame, st.session_state[key], f"p{owner}_", 3
            )
    """)).run()
    assert not app.exception
    app.number_input(key="p7_filter_threshold_greater_or_equal_3").set_value(1).run()
    assert not app.exception
    assert app.session_state["config7"]["threshold"] == 1
    assert app.session_state["config8"]["threshold"] == 3


@pytest.mark.parametrize(
    "config,values",
    [
        ({"column": "x", "mode": "greater_or_equal", "threshold": 2}, '["a", "b"]'),
        ({"column": "x", "mode": "equals", "value": 2**63}, "[1, 2, 3]"),
        ({"column": "x", "mode": "range", "range": [2, 1]}, "[1, 2, 3]"),
        ({"column": "x", "mode": "in", "values": [2], "value": 1}, "[1, 2, 3]"),
        ({"column": "x", "mode": "legacy", "condition": ">", "value": 1}, "[1, 2, 3]"),
        ({"column": "x", "condition": ">", "value": 1}, "[1, 2, 3]"),
        ({"column": "x", "range": [0, 2]}, "[1, 2, 3]"),
        ({"column": "missing", "mode": "equals", "value": 1}, "[1, 2, 3]"),
    ],
)
def test_unrepresentable_predicate_is_visible_and_preserved(
    config: dict[str, Any], values: str
) -> None:
    saved = {"type": "conditionSelector", **config}
    app = _app(saved, values, execute=False)
    assert not app.exception
    assert app.error
    assert "unchanged" in app.error[0].value
    assert app.session_state["config"] == saved
