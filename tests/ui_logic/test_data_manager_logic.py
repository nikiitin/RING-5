from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager
from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager


# Mock streamlit
@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st") as mock_st_seeds, patch(
        "src.web.pages.ui.data_managers.impl.outlier_remover.st"
    ) as mock_st_outlier:

        # Configure session state handling for mocks.
        mock_st_seeds.session_state = {}
        mock_st_outlier.session_state = {}

        # Side effect for columns
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            return [MagicMock()]

        mock_st_seeds.columns.side_effect = columns_side_effect
        mock_st_outlier.columns.side_effect = columns_side_effect

        yield (mock_st_seeds, mock_st_outlier)


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.state_manager = MagicMock()
    return api


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "benchmark": ["b1", "b1", "b2"],
            "random_seed": [1, 2, 1],
            "value": [10, 12, 5],
            "other": [1, 1, 1],
        }
    )


def test_seeds_reducer_render_no_random_seed(mock_streamlit, mock_api, sample_data):
    """Test Seeds Reducer warns if no random_seed column."""
    mock_st, _ = mock_streamlit

    # Manager Mock
    manager = SeedsReducerManager(mock_api)
    manager.get_data = MagicMock(return_value=sample_data.drop(columns=["random_seed"]))

    manager.render()

    mock_st.warning.assert_called()
    assert "No `random_seed` column" in mock_st.warning.call_args[0][0]


def test_seeds_reducer_apply(mock_streamlit, mock_api, sample_data):
    """Test Seeds Reducer apply logic."""
    mock_st, _ = mock_streamlit

    # Setup Manager
    manager = SeedsReducerManager(mock_api)
    manager.get_data = MagicMock(return_value=sample_data)
    manager.set_data = MagicMock()

    # Mock Interactions
    # Multiselects: Categorical (benchmark), Numeric (value)
    mock_st.multiselect.side_effect = [["benchmark"], ["value"]]

    # Apply Button -> True
    # Confirm Button -> False (for this pass)
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "apply_seeds"

    # Mock Computing Service via api facade
    result_df = pd.DataFrame({"benchmark": ["b1"], "value": [11], "value.sd": [1.4]})
    mock_api.compute.validate_seeds_reducer_inputs.return_value = []
    mock_api.compute.reduce_seeds.return_value = result_df

    manager.render()

    # Check processing called
    mock_api.compute.reduce_seeds.assert_called_once()

    # Check result stored via api
    mock_api.set_preview.assert_called_once_with("seeds_reduction", result_df)


def test_seeds_reducer_confirm(mock_streamlit, mock_api, sample_data):
    """Test Seeds Reducer confirm logic."""
    mock_st, _ = mock_streamlit

    # Setup Manager
    manager = SeedsReducerManager(mock_api)
    manager.get_data = MagicMock(return_value=sample_data)

    # Pre-load result
    result_df = pd.DataFrame({"benchmark": ["b1"]})

    # Mock Interactions
    # Confirm Button -> True
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "confirm_seeds"

    # Configure mock_api
    mock_api.has_preview.return_value = True
    mock_api.get_preview.return_value = result_df

    manager.render()

    # Check state updated via api orchestrator
    mock_api.state_manager.set_data.assert_called_with(result_df)
    mock_api.clear_preview.assert_called_once_with("seeds_reduction")
    mock_st.rerun.assert_called_once()


def test_outlier_remover_run(mock_streamlit, mock_api, sample_data):
    """Test Outlier Remover run flows."""
    _, mock_st = mock_streamlit

    manager = OutlierRemoverManager(mock_api)
    manager.get_data = MagicMock(return_value=sample_data)

    # Interaction:
    # Selectbox (col) -> "value"
    # Multiselect (group) -> ["benchmark"]
    mock_st.selectbox.return_value = "value"
    mock_st.multiselect.return_value = ["benchmark"]

    # Button: Apply -> True
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "apply_outlier"

    mock_api.compute.validate_outlier_inputs.return_value = []
    mock_api.compute.remove_outliers.return_value = sample_data

    manager.render()

    mock_api.compute.remove_outliers.assert_called_once()
    # Check result stored via api
    mock_api.set_preview.assert_called_once_with("outlier_removal", sample_data)
