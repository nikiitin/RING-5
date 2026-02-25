from collections.abc import Generator
from typing import Any, cast
from unittest.mock import patch

import pandas as pd
import pytest
from pandas import DataFrame

from src.core.models.data_models import ShaperStepConfig
from src.web.pages.ui.shaper_config import configure_shaper
from tests.conftest import columns_side_effect


# Mock streamlit
@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with (
        patch("src.web.pages.ui.shaper_config.st") as mock_st,
        patch("src.web.components.shapers.normalize_config.st", mock_st),
        patch("src.web.components.shapers.mean_config.st", mock_st),
        patch("src.web.components.shapers.selector_transformer_configs.st", mock_st),
    ):

        # Mock session state as a dict
        mock_st.session_state = {}

        mock_st.columns.side_effect = columns_side_effect
        yield mock_st


@pytest.fixture
def sample_data() -> DataFrame:
    return pd.DataFrame(
        {
            "dataset": ["A", "A", "B", "B"],
            "metric": [10, 20, 30, 40],
            "category": ["X", "Y", "X", "Y"],
        }
    )


def test_configure_column_selector(mock_streamlit: Any, sample_data: Any) -> None:
    """Test Column Selector configuration UI."""
    # Setup mock return values
    mock_streamlit.multiselect.return_value = ["metric"]

    config = configure_shaper("columnSelector", sample_data, 1, {})

    assert config.get("type") == "columnSelector"
    assert config.get("columns") == ["metric"]

    # Verify existing config usage
    existing = cast(ShaperStepConfig, {"columns": ["dataset"]})
    configure_shaper("columnSelector", sample_data, 1, existing)
    # Check default was passed correctly
    kwargs = mock_streamlit.multiselect.call_args[1]
    assert kwargs["default"] == ["dataset"]


def test_configure_filter_numeric(mock_streamlit: Any, sample_data: Any) -> None:
    """Test Numeric Filter configuration UI."""
    # Filter on 'metric'
    mock_streamlit.selectbox.side_effect = ["metric", "greater_than"]
    mock_streamlit.number_input.return_value = 15.0

    config = configure_shaper("conditionSelector", sample_data, 1, {})

    assert config.get("type") == "conditionSelector"
    assert config.get("column") == "metric"
    assert config.get("mode") == "greater_than"
    assert config.get("threshold") == 15.0


def test_configure_filter_categorical(mock_streamlit: Any, sample_data: Any) -> None:
    """Test Categorical Filter configuration UI."""
    # Filter on 'dataset'
    mock_streamlit.selectbox.side_effect = ["dataset"]
    # Selectbox is first call (Select Column)

    mock_streamlit.multiselect.return_value = ["A"]

    config = configure_shaper("conditionSelector", sample_data, 1, {})

    assert config.get("type") == "conditionSelector"
    assert config.get("column") == "dataset"
    assert config.get("values") == ["A"]


def test_configure_mean(mock_streamlit: Any, sample_data: Any) -> None:
    """Test Mean Calculator configuration UI."""
    # col1: algo, col2: vars, col3: group
    # Calls: selectbox(algo), multiselect(vars), multiselect(group), selectbox(replace)

    mock_streamlit.selectbox.side_effect = [
        "arithmean",  # Mean type
        "category",  # Replacing column
    ]
    mock_streamlit.multiselect.side_effect = [["metric"], ["dataset"]]  # Variables  # Group by

    config = configure_shaper("mean", sample_data, 1, {})

    assert config.get("type") == "mean"
    assert config.get("meanAlgorithm") == "arithmean"
    assert config.get("meanVars") == ["metric"]
    assert config.get("groupingColumns") == ["dataset"]
    assert config.get("replacingColumn") == "category"
