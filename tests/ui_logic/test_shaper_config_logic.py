from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.shaper_config import configure_shaper


# Mock streamlit
@pytest.fixture
def mock_streamlit():
    with (
        patch("src.web.pages.ui.shaper_config.st") as mock_st,
        patch("src.web.pages.ui.components.shapers.normalize_config.st", mock_st),
        patch("src.web.pages.ui.components.shapers.mean_config.st", mock_st),
        patch("src.web.pages.ui.components.shapers.selector_transformer_configs.st", mock_st),
    ):

        # Mock session state as a dict
        mock_st.session_state = {}

        # Side effect for columns
        def columns_side_effect(spec, gap="small", vertical_alignment="top"):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect
        yield mock_st


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "dataset": ["A", "A", "B", "B"],
            "metric": [10, 20, 30, 40],
            "category": ["X", "Y", "X", "Y"],
        }
    )


def test_configure_column_selector(mock_streamlit, sample_data):
    """Test Column Selector configuration UI."""
    # Setup mock return values
    mock_streamlit.multiselect.return_value = ["metric"]

    config = configure_shaper("columnSelector", sample_data, 1, {})

    assert config["type"] == "columnSelector"
    assert config["columns"] == ["metric"]

    # Verify existing config usage
    existing = {"columns": ["dataset"]}
    configure_shaper("columnSelector", sample_data, 1, existing)
    # Check default was passed correctly
    kwargs = mock_streamlit.multiselect.call_args[1]
    assert kwargs["default"] == ["dataset"]


def test_configure_filter_numeric(mock_streamlit, sample_data):
    """Test Numeric Filter configuration UI."""
    # Filter on 'metric'
    mock_streamlit.selectbox.side_effect = ["metric", "greater_than"]
    mock_streamlit.number_input.return_value = 15.0

    config = configure_shaper("conditionSelector", sample_data, 1, {})

    assert config["type"] == "conditionSelector"
    assert config["column"] == "metric"
    assert config["mode"] == "greater_than"
    assert config["threshold"] == 15.0


def test_configure_filter_categorical(mock_streamlit, sample_data):
    """Test Categorical Filter configuration UI."""
    # Filter on 'dataset'
    mock_streamlit.selectbox.side_effect = ["dataset"]
    # Selectbox is first call (Select Column)

    mock_streamlit.multiselect.return_value = ["A"]

    config = configure_shaper("conditionSelector", sample_data, 1, {})

    assert config["type"] == "conditionSelector"
    assert config["column"] == "dataset"
    assert config["values"] == ["A"]


def test_configure_mean(mock_streamlit, sample_data):
    """Test Mean Calculator configuration UI."""
    # col1: algo, col2: vars, col3: group
    # Calls: selectbox(algo), multiselect(vars), multiselect(group), selectbox(replace)

    mock_streamlit.selectbox.side_effect = [
        "arithmean",  # Mean type
        "category",  # Replacing column
    ]
    mock_streamlit.multiselect.side_effect = [["metric"], ["dataset"]]  # Variables  # Group by

    config = configure_shaper("mean", sample_data, 1, {})

    assert config["type"] == "mean"
    assert config["meanAlgorithm"] == "arithmean"
    assert config["meanVars"] == ["metric"]
    assert config["groupingColumns"] == ["dataset"]
    assert config["replacingColumn"] == "category"
