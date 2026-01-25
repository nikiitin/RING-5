from unittest.mock import ANY, MagicMock, patch

import pytest

from src.web.ui.components.data_source_components import DataSourceComponents


@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.components.data_source_components.st") as mock_st:
        # Columns mock
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]

        mock_st.columns.side_effect = columns_side_effect

        # Containers
        mock_st.container.return_value.__enter__.return_value = MagicMock()
        mock_st.spinner.return_value.__enter__.return_value = MagicMock()

        yield mock_st


@pytest.fixture
def mock_facade():
    return MagicMock()


@pytest.fixture
def mock_card_components():
    with patch("src.web.ui.components.data_source_components.CardComponents") as mock_card:
        yield mock_card


@pytest.fixture
def mock_state_manager():
    with patch("src.web.ui.components.data_source_components.StateManager") as mock_sm:
        import tempfile

        mock_sm.get_temp_dir.return_value = tempfile.gettempdir()
        mock_sm.get_parse_variables.return_value = []
        yield mock_sm


def test_render_csv_pool_empty(mock_streamlit, mock_facade, mock_state_manager):
    mock_facade.load_csv_pool.return_value = []

    DataSourceComponents.render_csv_pool(mock_facade)

    mock_streamlit.warning.assert_called_with(ANY)
    mock_state_manager.set_csv_pool.assert_called_with([])


def test_render_csv_pool_with_files(
    mock_streamlit, mock_facade, mock_card_components, mock_state_manager
):
    csv_info = {"name": "test.csv", "path": "/path/to/test.csv"}
    mock_facade.load_csv_pool.return_value = [csv_info]

    with patch("pathlib.Path.exists", return_value=True):
        mock_card_components.file_info_card.return_value = (True, False, False)

        mock_data = MagicMock()
        mock_data.__len__.return_value = 10
        mock_facade.load_csv_file.return_value = mock_data

        DataSourceComponents.render_csv_pool(mock_facade)

        mock_facade.load_csv_file.assert_called_with("/path/to/test.csv")
        mock_state_manager.set_data.assert_called_with(mock_data)
        mock_streamlit.success.assert_called()


def test_render_csv_pool_delete(mock_streamlit, mock_facade, mock_card_components):
    csv_info = {"name": "del.csv", "path": "/del.csv"}
    mock_facade.load_csv_pool.return_value = [csv_info]

    with patch("pathlib.Path.exists", return_value=True):
        mock_card_components.file_info_card.return_value = (False, False, True)
        mock_facade.delete_from_csv_pool.return_value = True

        DataSourceComponents.render_csv_pool(mock_facade)

        mock_facade.delete_from_csv_pool.assert_called_with("/del.csv")
        mock_streamlit.rerun.assert_called()


def test_render_parser_config(mock_streamlit, mock_facade, mock_state_manager):
    mock_streamlit.button.side_effect = lambda label, **k: "Scan" in label

    mock_facade.scan_stats_variables_with_grouping.return_value = [{"name": "var1"}]

    DataSourceComponents.render_parser_config(mock_facade)

    mock_facade.scan_stats_variables_with_grouping.assert_called()
    mock_state_manager.set_scanned_variables.assert_called()
    mock_streamlit.rerun.assert_called()


def test_execute_parser_success(mock_streamlit, mock_facade, mock_state_manager):
    stats_path = "/stats"
    pattern = "*.txt"

    mock_facade.find_stats_files.return_value = ["/stats/1.txt"]

    generated_csv = "/output.csv"
    mock_facade.parse_gem5_stats.return_value = generated_csv

    with patch("pathlib.Path.exists", return_value=True):
        DataSourceComponents.execute_parser(mock_facade, stats_path, pattern)

        mock_facade.parse_gem5_stats.assert_called_with(
            stats_path=stats_path,
            stats_pattern=pattern,
            variables=ANY,
            output_dir=ANY,
            progress_callback=ANY,
        )
        mock_facade.add_to_csv_pool.assert_called_with(generated_csv)
        mock_state_manager.set_data.assert_called()


def test_execute_parser_no_files(mock_streamlit, mock_facade):
    mock_facade.find_stats_files.return_value = []

    with patch("pathlib.Path.exists", return_value=True):
        DataSourceComponents.execute_parser(mock_facade, "/p", "*.txt")

    mock_streamlit.warning.assert_called_with("No files found matching pattern")
    mock_facade.parse_gem5_stats.assert_not_called()
