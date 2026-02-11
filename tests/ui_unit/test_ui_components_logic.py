from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

from src.web.pages.ui.components.data_source_components import DataSourceComponents
from src.web.pages.ui.components.upload_components import UploadComponents
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit():
    with (
        patch("src.web.pages.ui.components.data_source_components.st") as mock_st_ds,
        patch("src.web.pages.ui.components.upload_components.st") as mock_st_up,
    ):

        mock_st_ds.session_state = {}
        mock_st_up.session_state = {}

        mock_st_ds.columns.side_effect = columns_side_effect
        mock_st_up.columns.side_effect = columns_side_effect

        yield (mock_st_ds, mock_st_up)


@pytest.fixture
def mock_card_components():
    with patch("src.web.pages.ui.components.data_source_components.CardComponents") as mock_card:
        yield mock_card


def test_render_csv_pool_load(mock_streamlit, mock_api, mock_card_components):
    """Test loading a CSV file from the pool."""
    mock_st, _ = mock_streamlit

    pool = [{"name": "test.csv", "path": "/path/test.csv", "size": 100}]
    mock_api.load_csv_pool.return_value = pool

    # load_clicked=True
    mock_card_components.file_info_card.return_value = (True, False, False)

    df = pd.DataFrame({"col": [1, 2]})
    mock_api.load_csv_file.return_value = df

    with patch("pathlib.Path.exists", return_value=True):
        DataSourceComponents.render_csv_pool(mock_api)

    mock_api.load_csv_file.assert_called_with("/path/test.csv")
    mock_api.state_manager.set_data.assert_called_with(df)
    mock_st.success.assert_called()


def test_execute_parser(mock_streamlit, mock_api):
    """Test the async parsing workflow."""
    mock_st, _ = mock_streamlit

    # Mock the async workflow
    mock_future = MagicMock()
    mock_future.result.return_value = {"data": "test"}

    from src.core.models import ParseBatchResult

    mock_api.submit_parse_async.return_value = ParseBatchResult(
        futures=[mock_future], var_names=["test_var"]
    )

    csv_path = "/tmp/out.csv"
    mock_api.finalize_parsing.return_value = csv_path
    mock_api.load_csv_file.return_value = MagicMock()
    mock_api.add_to_csv_pool.return_value = csv_path

    with patch("pathlib.Path.exists", return_value=True):
        # Test async submission
        batch = mock_api.submit_parse_async("/stats", "*.txt", [], "/tmp")
        results = [f.result() for f in batch.futures]
        final_csv = mock_api.finalize_parsing("/tmp", results, var_names=batch.var_names)

        assert final_csv == csv_path
        mock_api.submit_parse_async.assert_called()


def test_render_file_upload(mock_streamlit, mock_api):
    """Test file upload handling."""
    _, mock_st = mock_streamlit

    uploaded_file = MagicMock()
    uploaded_file.name = "upload.csv"
    uploaded_file.getbuffer.return_value = b"data"

    # Mock CSV file loading
    df = pd.DataFrame({"col": [1, 2]})
    mock_api.state_manager.get_data.return_value = df
    mock_st.file_uploader.return_value = uploaded_file

    mock_api.state_manager.get_temp_dir.return_value = "/tmp"

    m_open = mock_open()
    with patch("builtins.open", m_open):
        with patch("src.web.pages.ui.components.upload_components.Path") as mock_path:
            mock_path.return_value.__truediv__.return_value = "/tmp/upload.csv"

            # API now uses load_data instead of load_csv_file
            UploadComponents.render_file_upload_tab(mock_api)

            m_open.assert_called()
            mock_api.load_data.assert_called_with("/tmp/upload.csv")


def test_render_paste_data(mock_streamlit, mock_api):
    """Test pasting CSV data."""
    _, mock_st = mock_streamlit

    csv_content = "A,B\n1,2"
    mock_st.text_area.return_value = csv_content
    mock_st.button.return_value = True

    UploadComponents.render_paste_data_tab(mock_api)

    mock_api.state_manager.set_data.assert_called()
    args = mock_api.state_manager.set_data.call_args
    df = args[0][0]
    assert len(df) == 1
    assert "A" in df.columns
