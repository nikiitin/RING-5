from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.ui.data_managers.outlier_remover import OutlierRemoverManager
from src.web.ui.data_managers.seeds_reducer import SeedsReducerManager


# Mock streamlit
@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.data_managers.seeds_reducer.st") as mock_st_seeds, patch(
        "src.web.ui.data_managers.outlier_remover.st"
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
def sample_data():
    return pd.DataFrame(
        {
            "benchmark": ["b1", "b1", "b2"],
            "random_seed": [1, 2, 1],
            "value": [10, 12, 5],
            "other": [1, 1, 1],
        }
    )


def test_seeds_reducer_render_no_random_seed(mock_streamlit, sample_data):
    """Test Seeds Reducer warns if no random_seed column."""
    mock_st, _ = mock_streamlit

    # Manager Mock
    manager = SeedsReducerManager()
    manager.get_data = MagicMock(return_value=sample_data.drop(columns=["random_seed"]))

    manager.render()

    mock_st.warning.assert_called()
    assert "No `random_seed` column" in mock_st.warning.call_args[0][0]


def test_seeds_reducer_apply(mock_streamlit, sample_data):
    """Test Seeds Reducer apply logic."""
    mock_st, _ = mock_streamlit

    # Setup Manager
    manager = SeedsReducerManager()
    manager.get_data = MagicMock(return_value=sample_data)
    manager.set_data = MagicMock()

    # Mock Interactions
    # Multiselects: Categorical (benchmark), Numeric (value)
    mock_st.multiselect.side_effect = [["benchmark"], ["value"]]

    # Apply Button -> True
    # Confirm Button -> False (for this pass)
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "apply_seeds"

    # Mock Processing Service
    with patch(
        "src.web.services.data_processing_service.DataProcessingService.reduce_seeds"
    ) as mock_reduce:
        mock_reduce.return_value = pd.DataFrame(
            {"benchmark": ["b1"], "value": [11], "value.sd": [1.4]}
        )

        manager.render()

        # Check processing called
        mock_reduce.assert_called_once()

        # Check result stored in session state
        assert "seeds_result" in mock_st.session_state


def test_seeds_reducer_confirm(mock_streamlit, sample_data):
    """Test Seeds Reducer confirm logic."""
    mock_st, _ = mock_streamlit

    # Setup Manager
    manager = SeedsReducerManager()
    manager.get_data = MagicMock(return_value=sample_data)
    manager.set_data = MagicMock()

    # Pre-load session state with result
    result_df = pd.DataFrame({"benchmark": ["b1"]})
    mock_st.session_state["seeds_result"] = result_df

    # Mock Interactions
    # Apply Button -> False
    # Confirm Button -> True
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "confirm_seeds"

    manager.render()

    # Check set_data called
    manager.set_data.assert_called_once_with(result_df)
    assert "seeds_result" not in mock_st.session_state
    mock_st.rerun.assert_called_once()


def test_outlier_remover_run(mock_streamlit, sample_data):
    """Test Outlier Remover run flows."""
    _, mock_st = mock_streamlit

    manager = OutlierRemoverManager()
    manager.get_data = MagicMock(return_value=sample_data)

    # Interaction:
    # Selectbox (col) -> "value"
    # Multiselect (group) -> ["benchmark"]
    mock_st.selectbox.return_value = "value"
    mock_st.multiselect.return_value = ["benchmark"]

    # Button: Apply -> True
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "apply_outlier"

    with patch(
        "src.web.services.data_processing_service.DataProcessingService.remove_outliers"
    ) as mock_remove:
        mock_remove.return_value = sample_data

        manager.render()

        mock_remove.assert_called_once()
        assert "outlier_result" in mock_st.session_state
