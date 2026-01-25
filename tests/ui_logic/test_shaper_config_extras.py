from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.ui.shaper_config import configure_shaper


@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.shaper_config.st") as mock_st:
        # Mock columns
        mock_st.columns.side_effect = lambda n: (
            [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        )
        # Mock session_state
        mock_st.session_state = {}
        yield mock_st


def test_configure_normalize_ui(mock_streamlit):
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"], "C": [10, 20]})

    # Mock inputs logic order:
    # multiselects: normalizer_vars, normalize_vars, group_by
    mock_streamlit.multiselect.side_effect = [
        ["A"],  # normalizer_vars
        ["C"],  # normalize_vars
        ["B"],  # group_by
    ]
    # selectboxes: normalizer_column, normalizer_value
    mock_streamlit.selectbox.side_effect = [
        "B",  # normalizer_column
        "x",  # normalizer_value
    ]
    mock_streamlit.checkbox.return_value = True  # normalize_sd

    config = configure_shaper("normalize", df, "test_id", {}, owner_id="plot1")

    assert config["type"] == "normalize"
    assert config["normalizerVars"] == ["A"]
    assert config["normalizeVars"] == ["C"]
    assert config["normalizerColumn"] == "B"
    assert config["normalizerValue"] == "x"
    assert config["groupBy"] == ["B"]
    assert config["normalizeSd"] is True


def test_configure_sort_ui(mock_streamlit):
    df = pd.DataFrame({"A": ["a", "b", "c"]})

    mock_streamlit.selectbox.return_value = "A"  # sort_column

    config = configure_shaper("sort", df, "test_id", {}, owner_id="plot1")

    # Session state initialization check
    key = "pplot1_sort_order_list_test_id"
    # Sort before comparing because pd.unique order might vary or depend on input
    assert sorted(mock_streamlit.session_state[key]) == ["a", "b", "c"]

    assert config["type"] == "sort"
    assert sorted(config["order_dict"]["A"]) == ["a", "b", "c"]


def test_configure_transformer_ui(mock_streamlit):
    df = pd.DataFrame({"A": [1, 2, 3]})

    mock_streamlit.selectbox.return_value = "A"  # target_col
    mock_streamlit.radio.return_value = "Factor (String/Categorical)"  # target_type_str
    mock_streamlit.multiselect.return_value = ["1", "2", "3"]  # order_list

    config = configure_shaper("transformer", df, "test_id", {}, owner_id="plot1")

    assert config["type"] == "transformer"
    assert config["target_type"] == "factor"
    assert config["column"] == "A"
    assert config["order"] == ["1", "2", "3"]


def test_configure_filter_ui_numeric(mock_streamlit):
    df = pd.DataFrame({"A": [10, 20, 30]})

    # Setup side effects for selectboxes (Column, Mode)
    mock_streamlit.selectbox.side_effect = ["A", "range"]
    mock_streamlit.slider.return_value = (10.0, 20.0)

    config = configure_shaper("conditionSelector", df, "test_id", {}, owner_id="plot1")

    assert config["type"] == "conditionSelector"
    assert config["mode"] == "range"
    assert config["range"] == [10.0, 20.0]


def test_configure_filter_ui_categorical(mock_streamlit):
    df = pd.DataFrame({"B": ["x", "y", "z"]})

    mock_streamlit.selectbox.return_value = "B"
    mock_streamlit.multiselect.return_value = ["x", "z"]

    config = configure_shaper("conditionSelector", df, "test_id", {}, owner_id="plot1")

    assert config["type"] == "conditionSelector"
    assert config["column"] == "B"
    assert config["values"] == ["x", "z"]
