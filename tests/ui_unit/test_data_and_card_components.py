from collections.abc import Generator
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.data_models import CsvPoolEntry
from src.web.components.common.card_components import CardComponents
from src.web.components.common.data_components import DataComponents
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit() -> Generator[MagicMock, None, None]:
    # We need to patch st in both modules where it is used
    with (
        patch("src.web.components.common.data_components.st") as mock_st_data,
        patch("src.web.components.common.card_components.st") as mock_st_card,
    ):

        # Unify mocks for easier assertion
        mock_st = MagicMock()
        mock_st_data.markdown = mock_st.markdown
        mock_st_data.dataframe = mock_st.dataframe
        mock_st_data.metric = mock_st.metric
        mock_st_data.expander = mock_st.expander
        mock_st_data.columns = mock_st.columns

        mock_st_card.expander = mock_st.expander
        mock_st_card.button = mock_st.button
        mock_st_card.columns = mock_st.columns

        # Mock columns to return list of mocks
        mock_st.columns.side_effect = columns_side_effect

        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()

        yield mock_st


def test_show_data_preview(mock_streamlit: Any) -> None:

    df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})

    DataComponents.show_data_preview(df, "Test Preview", rows=2)

    mock_streamlit.markdown.assert_called_with("### Test Preview")
    mock_streamlit.dataframe.assert_called()
    # Check if metrics were called (4 columns)
    assert mock_streamlit.metric.call_count == 4


def test_show_column_details(mock_streamlit: Any) -> None:

    df = pd.DataFrame({"A": [1, 2], "B": ["x", None]})

    DataComponents.show_column_details(df)

    # Should create a dataframe for details
    mock_streamlit.dataframe.assert_called()
    # Expander used
    mock_streamlit.expander.assert_called_with("Column Details")


def test_file_info_card(mock_streamlit: Any) -> None:

    # Setup
    info = cast(CsvPoolEntry, {"name": "test.csv", "size": 1024, "modified": 1678886400.0})

    # Mock buttons to return True sequence
    mock_streamlit.button.side_effect = [True, False, False]  # Load clicked

    load, preview, delete = CardComponents.file_info_card(info, 0)

    assert load is True
    assert preview is False
    assert delete is False

    mock_streamlit.expander.assert_called()
    assert "test.csv" in mock_streamlit.expander.call_args[0][0]
