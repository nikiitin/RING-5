from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

from src.web.ui.components.data_source_components import DataSourceComponents
from src.web.ui.components.upload_components import UploadComponents


@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.components.data_source_components.st") as mock_st_ds, patch(
        "src.web.ui.components.upload_components.st"
    ) as mock_st_up:

        mock_st_ds.session_state = {}
        mock_st_up.session_state = {}

        # Columns mock
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st_ds.columns.side_effect = columns_side_effect
        mock_st_up.columns.side_effect = columns_side_effect

        yield (mock_st_ds, mock_st_up)


@pytest.fixture
def mock_facade():
    return MagicMock()


@pytest.fixture
def mock_state_manager():
    with patch("src.web.ui.components.data_source_components.StateManager") as mock_sm_ds, patch(
        "src.web.ui.components.upload_components.StateManager"
    ) as mock_sm_up:
        yield (mock_sm_ds, mock_sm_up)


@pytest.fixture
def mock_card_components():
    with patch("src.web.ui.components.data_source_components.CardComponents") as mock_card:
        yield mock_card


def test_render_csv_pool_load(
    mock_streamlit, mock_facade, mock_state_manager, mock_card_components
):
    """Test loading a CSV file from the pool."""
    mock_st, _ = mock_streamlit
    mock_sm, _ = mock_state_manager

    # Setup pool data
    pool = [{"name": "test.csv", "path": "/path/test.csv", "size": 100}]
    mock_facade.load_csv_pool.return_value = pool

    # Mock UI Interactions
    # file_info_card returns (load_clicked, preview_clicked, delete_clicked)
    mock_card_components.file_info_card.return_value = (True, False, False)

    # Mock Load
    df = pd.DataFrame({"col": [1, 2]})
    mock_facade.load_csv_file.return_value = df

    with patch("pathlib.Path.exists", return_value=True):
        DataSourceComponents.render_csv_pool(mock_facade)

    mock_facade.load_csv_file.assert_called_with("/path/test.csv")
    mock_sm.set_data.assert_called_with(df)
    mock_st.success.assert_called()


def test_execute_parser(mock_streamlit, mock_facade, mock_state_manager):
    """Test executing the parser."""
    mock_st, _ = mock_streamlit
    mock_sm, _ = mock_state_manager

    mock_facade.find_stats_files.return_value = ["file1"]
    mock_sm.get_temp_dir.return_value = "/tmp"
    mock_sm.get_parse_variables.return_value = []

    # Mock efficient parsing success
    csv_path = "/tmp/out.csv"
    mock_facade.parse_gem5_stats.return_value = csv_path

    with patch("pathlib.Path.exists", return_value=True):
        DataSourceComponents.execute_parser(mock_facade, "/stats", "*.txt")

    mock_facade.parse_gem5_stats.assert_called()
    mock_facade.add_to_csv_pool.assert_called_with(csv_path)
    mock_st.success.assert_called()


def test_render_file_upload(mock_streamlit, mock_facade, mock_state_manager):
    """Test file upload handling."""
    _, mock_st = mock_streamlit
    _, mock_sm = mock_state_manager

    # Mock UploadedFile
    uploaded_file = MagicMock()
    uploaded_file.name = "upload.csv"
    uploaded_file.getbuffer.return_value = b"data"
    mock_st.file_uploader.return_value = uploaded_file

    mock_sm.get_temp_dir.return_value = "/tmp"

    # Mock file write
    m_open = mock_open()
    with patch("builtins.open", m_open):
        with patch("src.web.ui.components.upload_components.Path") as mock_path:
            mock_path.return_value.__truediv__.return_value = "/tmp/upload.csv"

            df = pd.DataFrame({"col": [1]})
            mock_facade.load_csv_file.return_value = df

            UploadComponents.render_file_upload_tab(mock_facade)

            m_open.assert_called()  # Should write
            mock_facade.load_csv_file.assert_called_with("/tmp/upload.csv")
            mock_sm.set_data.assert_called_with(df)


def test_render_paste_data(mock_streamlit, mock_state_manager):
    """Test pasting CSV data."""
    _, mock_st = mock_streamlit
    _, mock_sm = mock_state_manager

    csv_content = "A,B\n1,2"
    mock_st.text_area.return_value = csv_content
    mock_st.button.return_value = True

    UploadComponents.render_paste_data_tab()

    mock_sm.set_data.assert_called()
    # verify dataframe in set_data
    args = mock_sm.set_data.call_args
    df = args[0][0]
    assert len(df) == 1
    assert "A" in df.columns
