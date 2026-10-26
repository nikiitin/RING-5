from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest

from src.web.components.data_source.data_source_components import DataSourceComponents
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit() -> Generator[Any, None, None]:
    with (patch("src.web.components.data_source.data_source_components.st") as mock_st_ds,):

        mock_st_ds.session_state = {}

        mock_st_ds.columns.side_effect = columns_side_effect

        # Fragment passthrough — execute the decorated function directly
        mock_st_ds.fragment.side_effect = lambda func: func

        yield mock_st_ds


@pytest.fixture
def mock_card_components() -> Generator[Any, None, None]:
    with patch("src.web.components.data_source.data_source_components.CardComponents") as mock_card:
        yield mock_card


def test_render_csv_pool_load(
    mock_streamlit: Any, mock_api: Any, mock_card_components: Any
) -> None:
    """Test loading a CSV file from the pool."""
    pool = [{"name": "test.csv", "path": "/path/test.csv", "size": 100}]
    mock_api.data_services.load_csv_pool.return_value = pool
    mock_api.state_manager.get_csv_pool.return_value = []

    # load_clicked=True
    mock_card_components.file_info_card.return_value = (True, False, False)

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_file", return_value=True),
        patch.object(DataSourceComponents, "render_import_preview") as render_preview,
    ):
        DataSourceComponents.render_csv_pool(mock_api)

    render_preview.assert_called_once_with(mock_api, "/path/test.csv")
    mock_api.data_services.load_csv_file.assert_not_called()
