from collections.abc import Generator
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.data_models import ShaperStepConfig
from src.web.pages.ui.shaper_config import configure_shaper


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with (
        patch("src.web.pages.ui.shaper_config.st") as mock_st,
        patch("src.web.components.shapers.normalize_config.st", mock_st),
        patch("src.web.components.shapers.mean_config.st", mock_st),
        patch("src.web.components.shapers.selector_transformer_configs.st", mock_st),
    ):

        # Mock columns
        mock_st.columns.side_effect = lambda n: (
            [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        )
        # Mock session_state
        mock_st.session_state = {}
        yield mock_st


def test_configure_normalize_ui(mock_streamlit: Any) -> None:

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

    config = configure_shaper("normalize", df, 1, cast(ShaperStepConfig, {}), owner_id=1)

    assert config.get("type") == "normalize"
    assert config.get("normalizerVars") == ["A"]
    assert config.get("normalizeVars") == ["C"]
    assert config.get("normalizerColumn") == "B"
    assert config.get("normalizerValue") == "x"
    assert config.get("groupBy") == ["B"]
    assert config.get("normalizeSd") is True


def test_configure_transformer_ui(mock_streamlit: Any) -> None:

    df = pd.DataFrame({"A": [1, 2, 3]})

    mock_streamlit.selectbox.return_value = "A"  # target_col
    mock_streamlit.segmented_control.return_value = "Factor (String/Categorical)"  # target_type_str
    mock_streamlit.multiselect.return_value = ["1", "2", "3"]  # order_list

    config = configure_shaper("transformer", df, 1, cast(ShaperStepConfig, {}), owner_id=1)

    assert config.get("type") == "transformer"
    assert config.get("target_type") == "factor"
    assert config.get("column") == "A"
    assert config.get("order") == ["1", "2", "3"]


def test_configure_filter_ui_numeric(mock_streamlit: Any) -> None:

    df = pd.DataFrame({"A": [10, 20, 30]})

    # Setup side effects for selectboxes (Column, Mode)
    mock_streamlit.selectbox.side_effect = ["A", "range"]
    mock_streamlit.slider.return_value = (10.0, 20.0)

    config = configure_shaper("conditionSelector", df, 1, cast(ShaperStepConfig, {}), owner_id=1)

    assert config.get("type") == "conditionSelector"
    assert config.get("mode") == "range"
    assert config.get("range") == [10.0, 20.0]


def test_configure_filter_ui_categorical(mock_streamlit: Any) -> None:

    df = pd.DataFrame({"B": ["x", "y", "z"]})

    mock_streamlit.selectbox.return_value = "B"
    mock_streamlit.multiselect.return_value = ["x", "z"]

    config = configure_shaper("conditionSelector", df, 1, cast(ShaperStepConfig, {}), owner_id=1)

    assert config.get("type") == "conditionSelector"
    assert config.get("column") == "B"
    assert config.get("values") == ["x", "z"]
