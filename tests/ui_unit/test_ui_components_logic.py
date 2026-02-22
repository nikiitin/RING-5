from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.components.data_source_components import DataSourceComponents
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit() -> None:
    with (patch("src.web.pages.ui.components.data_source_components.st") as mock_st_ds,):

        mock_st_ds.session_state = {}

        mock_st_ds.columns.side_effect = columns_side_effect

        # Fragment passthrough — execute the decorated function directly
        mock_st_ds.fragment.side_effect = lambda func: func

        yield mock_st_ds


@pytest.fixture
def mock_card_components() -> None:
    with patch("src.web.pages.ui.components.data_source_components.CardComponents") as mock_card:
        yield mock_card


def test_render_csv_pool_load(
    mock_streamlit: Any, mock_api: Any, mock_card_components: Any
) -> None:
    """Test loading a CSV file from the pool."""
    mock_st = mock_streamlit

    pool = [{"name": "test.csv", "path": "/path/test.csv", "size": 100}]
    mock_api.load_csv_pool.return_value = pool
    mock_api.state_manager.get_csv_pool.return_value = []

    # load_clicked=True
    mock_card_components.file_info_card.return_value = (True, False, False)

    df = pd.DataFrame({"col": [1, 2]})
    mock_api.load_csv_file.return_value = df

    with patch("pathlib.Path.exists", return_value=True):
        DataSourceComponents.render_csv_pool(mock_api)

    mock_api.load_csv_file.assert_called_with("/path/test.csv")
    mock_api.state_manager.set_data.assert_called_with(df)
    mock_st.success.assert_called()


def test_execute_parser(mock_streamlit: Any, mock_api: Any) -> None:
    """Test the async parsing workflow."""

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
