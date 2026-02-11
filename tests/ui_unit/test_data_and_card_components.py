from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.components.card_components import CardComponents
from src.web.pages.ui.components.data_components import DataComponents
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit():
    # We need to patch st in both modules where it is used
    with (
        patch("src.web.pages.ui.components.data_components.st") as mock_st_data,
        patch("src.web.pages.ui.components.card_components.st") as mock_st_card,
    ):

        # Unify mocks for easier assertion
        mock_st = MagicMock()
        mock_st_data.markdown = mock_st.markdown
        mock_st_data.dataframe = mock_st.dataframe
        mock_st_data.metric = mock_st.metric
        mock_st_data.expander = mock_st.expander
        mock_st_data.download_button = mock_st.download_button
        mock_st_data.columns = mock_st.columns

        mock_st_card.expander = mock_st.expander
        mock_st_card.button = mock_st.button
        mock_st_card.columns = mock_st.columns

        # Mock columns to return list of mocks
        mock_st.columns.side_effect = columns_side_effect

        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()

        yield mock_st


def test_show_data_preview(mock_streamlit):
    df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})

    DataComponents.show_data_preview(df, "Test Preview", rows=2)

    mock_streamlit.markdown.assert_called_with("### Test Preview")
    mock_streamlit.dataframe.assert_called()
    # Check if metrics were called (4 columns)
    assert mock_streamlit.metric.call_count == 4


def test_show_column_details(mock_streamlit):
    df = pd.DataFrame({"A": [1, 2], "B": ["x", None]})

    DataComponents.show_column_details(df)

    # Should create a dataframe for details
    mock_streamlit.dataframe.assert_called()
    # Expander used
    mock_streamlit.expander.assert_called_with("Column Details")


def test_file_info_card(mock_streamlit):
    # Setup
    info = {"name": "test.csv", "size": 1024, "modified": 1678886400.0}

    # Mock buttons to return True sequence
    mock_streamlit.button.side_effect = [True, False, False]  # Load clicked

    load, preview, delete = CardComponents.file_info_card(info, 0)

    assert load is True
    assert preview is False
    assert delete is False

    mock_streamlit.expander.assert_called()
    assert "test.csv" in mock_streamlit.expander.call_args[0][0]


def test_config_info_card(mock_streamlit):
    info = {"name": "conf1", "description": "desc", "modified": 1678886400.0}

    # Mock buttons: Load, Delete
    mock_streamlit.button.side_effect = [False, True]  # Delete clicked

    load, delete = CardComponents.config_info_card(info, 1)

    assert load is False
    assert delete is True

    mock_streamlit.expander.assert_called()


def test_download_buttons(mock_streamlit):
    df = pd.DataFrame({"A": [1, 2]})

    # Mock NamedTemporaryFile
    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
        import os
        import tempfile

        mock_tmp.return_value.name = os.path.join(tempfile.gettempdir(), "test.xlsx")

        # Mock pandas to_excel to avoid openpyxl/fs logic.
        with patch("pandas.DataFrame.to_excel") as mock_to_excel:

            # Mock open to return bytes
            from unittest.mock import mock_open

            with patch("builtins.open", mock_open(read_data=b"dummy_excel_data")):

                DataComponents.download_buttons(df, "test_prefix")

                # Validate to_excel and download_button calls.
                assert mock_to_excel.called
                assert mock_streamlit.download_button.call_count == 3

                # Verify Excel button specifically.
                _, kwargs = mock_streamlit.download_button.call_args
                assert kwargs["file_name"] == "test_prefix.xlsx"
                assert kwargs["data"] == b"dummy_excel_data"
