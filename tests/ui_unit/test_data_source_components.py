from collections.abc import Generator
from typing import Any
from unittest.mock import ANY, MagicMock, patch

import pytest

from src.core.models import ParserPlaygroundBatchResult, ScanResult
from src.web.components.data_source.data_source_components import DataSourceComponents
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with patch("src.web.components.data_source.data_source_components.st") as mock_st:
        mock_st.columns.side_effect = columns_side_effect
        mock_st.session_state = {}

        # Execute fragmented functions synchronously.
        mock_st.fragment.side_effect = lambda func: func
        mock_st.container.return_value.__enter__.return_value = MagicMock()
        mock_st.spinner.return_value.__enter__.return_value = MagicMock()

        yield mock_st


@pytest.fixture
def mock_api() -> Any:
    api = MagicMock()
    api.state_manager = MagicMock()

    import tempfile

    api.state_manager.get_temp_dir.return_value = tempfile.gettempdir()
    api.state_manager.get_parse_variables.return_value = []
    api.state_manager.get_scanned_variables.return_value = []
    api.state_manager.get_stats_path.return_value = "/path"
    api.state_manager.get_stats_pattern.return_value = "stats.txt"
    api.state_manager.get_parser_strategy.return_value = "simple"

    return api


@pytest.fixture
def mock_card_components() -> Generator[None, None, None]:
    with patch("src.web.components.data_source.data_source_components.CardComponents") as mock_card:
        yield mock_card


def test_render_csv_pool_empty(mock_streamlit: Any, mock_api: Any) -> None:

    mock_api.load_csv_pool.return_value = []
    mock_api.state_manager.get_csv_pool.return_value = []

    DataSourceComponents.render_csv_pool(mock_api)

    mock_streamlit.warning.assert_called_with(ANY)
    mock_api.state_manager.set_csv_pool.assert_called_with([])


def test_render_csv_pool_with_files(
    mock_streamlit: Any, mock_api: Any, mock_card_components: Any
) -> None:

    csv_info = {"name": "test.csv", "path": "/path/to/test.csv"}
    mock_api.load_csv_pool.return_value = [csv_info]
    mock_api.state_manager.get_csv_pool.return_value = []

    with patch("pathlib.Path.exists", return_value=True):
        mock_card_components.file_info_card.return_value = (True, False, False)

        with patch.object(DataSourceComponents, "render_import_preview") as render_preview:
            DataSourceComponents.render_csv_pool(mock_api)

        render_preview.assert_called_once_with(mock_api, "/path/to/test.csv")
        mock_api.load_csv_file.assert_not_called()


def test_render_csv_pool_delete(
    mock_streamlit: Any, mock_api: Any, mock_card_components: Any
) -> None:

    csv_info = {"name": "del.csv", "path": "/del.csv"}
    mock_api.load_csv_pool.return_value = [csv_info]
    mock_api.state_manager.get_csv_pool.return_value = []

    with patch("pathlib.Path.exists", return_value=True):
        mock_card_components.file_info_card.return_value = (False, False, True)
        mock_api.delete_from_csv_pool.return_value = True

        DataSourceComponents.render_csv_pool(mock_api)

        mock_api.delete_from_csv_pool.assert_called_with("/del.csv")
        mock_streamlit.rerun.assert_called()


def test_render_parser_config(mock_streamlit: Any, mock_api: Any) -> None:
    mock_streamlit.button.side_effect = lambda label, **k: "Quick Scan" in label
    mock_api.state_manager.get_simulator.return_value = "gem5"
    mock_api.state_manager.get_parser_strategy.return_value = "simple"
    mock_api.state_manager.get_scanned_variables.return_value = []

    mock_future = MagicMock()
    mock_future.result.return_value = {}
    mock_api.submit_scan_async.return_value = [mock_future]
    mock_api.finalize_scan.return_value = ScanResult(variables=[])

    # Yield the mock futures immediately.
    with patch(
        "src.web.components.data_source.data_source_components.as_completed",
        side_effect=lambda fs: fs,
    ):
        DataSourceComponents.render_parser_config(mock_api)

    mock_api.submit_scan_async.assert_called()
    mock_streamlit.rerun.assert_called()


def test_render_parser_config_submits_the_bounded_playground(
    mock_streamlit: Any,
    mock_api: Any,
    tmp_path: Any,
) -> None:
    # [test->req~ring5.ingestion.parser-playground~1]
    mock_streamlit.button.side_effect = lambda label, **kwargs: "Test configuration" in label
    mock_streamlit.pills.return_value = "gem5"
    mock_streamlit.text_input.side_effect = ["/allowed/stats", "custom*.txt"]
    mock_streamlit.segmented_control.return_value = "simple"
    mock_api.state_manager.get_simulator.return_value = "gem5"
    mock_api.state_manager.get_stats_path.return_value = "/allowed/stats"
    mock_api.state_manager.get_stats_pattern.return_value = "custom*.txt"
    mock_api.state_manager.get_temp_dir.return_value = str(tmp_path)
    variables = [{"name": "simTicks", "type": "scalar"}]
    mock_api.state_manager.get_parse_variables.return_value = variables
    batch = ParserPlaygroundBatchResult(
        futures=[],
        var_names=["simTicks"],
        output_dir=str(tmp_path / "parser_playground"),
        strategy_type="simple",
        matched_file_count=1,
        sampled_files=("/allowed/stats/run/stats.txt",),
    )
    mock_api.submit_parser_playground_async.return_value = batch

    with (
        patch(
            "src.web.components.data_source.data_source_components.validate_web_stats_path",
            return_value=tmp_path / "stats",
        ),
        patch.object(DataSourceComponents, "_show_parser_playground_dialog") as show_dialog,
        patch(
            "src.web.components.data_source.data_source_components.VariableEditor.render",
            return_value=variables,
        ),
    ):
        DataSourceComponents.render_parser_config(mock_api)

    mock_api.submit_parser_playground_async.assert_called_once_with(
        str(tmp_path / "stats"),
        "custom*.txt",
        [{"name": "simTicks", "type": "scalar"}],
        str(tmp_path / "parser_playground"),
        scanned_vars=[],
        strategy_type="simple",
    )
    show_dialog.assert_called_once_with(mock_api, batch)
