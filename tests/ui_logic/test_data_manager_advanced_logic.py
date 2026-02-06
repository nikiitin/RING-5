from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.data_managers.mixer import MixerManager
from src.web.pages.ui.data_managers.preprocessor import PreprocessorManager


@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.data_managers.mixer.st") as mock_st_mixer, patch(
        "src.web.pages.ui.data_managers.preprocessor.st"
    ) as mock_st_prep:

        mock_st_mixer.session_state = {}
        mock_st_prep.session_state = {}

        # Columns side effect
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            return [MagicMock()]

        mock_st_mixer.columns.side_effect = columns_side_effect
        mock_st_prep.columns.side_effect = columns_side_effect

        yield (mock_st_mixer, mock_st_prep)


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.state_manager = MagicMock()

    # Mock get_column_info to return realistic metadata
    def get_column_info(df):
        if df is None:
            return {"numeric_columns": [], "categorical_columns": [], "columns": []}
        import numpy as np

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
        return {
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "columns": df.columns.tolist(),
        }

    api.get_column_info.side_effect = get_column_info
    return api


@pytest.fixture
def sample_data():
    return pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6], "S": ["x", "y", "z"]})


def test_mixer_render_numeric_op(mock_streamlit, mock_api, sample_data):
    """Test Mixer numeric operation workflow."""
    mock_st, _ = mock_streamlit

    manager = MixerManager(mock_api)
    manager.get_data = MagicMock(return_value=sample_data)
    manager.set_data = MagicMock()

    # Interaction parameters.
    mock_st.radio.return_value = "Numerical Operations"
    mock_st.multiselect.return_value = ["A", "B"]
    mock_st.selectbox.return_value = "Sum"
    mock_st.text_input.return_value = "merged"
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "mixer_preview"

    with patch("src.web.pages.ui.data_managers.mixer.MixerService.merge_columns") as mock_merge:
        result_df = pd.DataFrame({"A": [1], "B": [4], "merged": [5]})
        mock_merge.return_value = result_df

        manager.render()

        mock_merge.assert_called()
        # Check result stored via api
        mock_api.set_preview.assert_called_once_with("mixer", result_df)
        mock_st.success.assert_called()


def test_mixer_confirm(mock_streamlit, mock_api, sample_data):
    """Test Mixer confirm workflow."""
    mock_st, _ = mock_streamlit

    manager = MixerManager(mock_api)
    manager.get_data = MagicMock(return_value=sample_data)

    # Pre-populate result
    result_df = pd.DataFrame({"merged": [1]})

    # Simulation: Confirm clicked
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "confirm_mixer"

    # Configure mock_api
    mock_api.has_preview.return_value = True
    mock_api.get_preview.return_value = result_df

    manager.render()

    # Check state updated via api orchestrator
    mock_api.state_manager.set_data.assert_called_with(result_df)
    mock_api.clear_preview.assert_called_once_with("mixer")


def test_preprocessor_render_op(mock_streamlit, mock_api, sample_data):
    """Test Preprocessor operation workflow."""
    _, mock_st = mock_streamlit

    manager = PreprocessorManager(mock_api)
    manager.get_data = MagicMock(return_value=sample_data)

    # Interaction parameters.
    mock_st.selectbox.side_effect = ["A", "Divide", "B"]
    mock_st.text_input.return_value = "new_col"
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "preview_preproc"

    with patch("src.core.services.arithmetic_service.ArithmeticService.apply_operation") as mock_op:
        with patch(
            "src.core.services.arithmetic_service.ArithmeticService.list_operators"
        ) as mock_list:
            mock_list.return_value = ["Divide"]
            result_df = pd.DataFrame({"A": [1], "B": [4], "new_col": [0.25]})
            mock_op.return_value = result_df

            manager.render()

            mock_op.assert_called()

            # Check result stored via api
            mock_api.set_preview.assert_called_once_with("preprocessor", result_df)


def test_preprocessor_no_numeric_cols(mock_streamlit, mock_api):
    """Test Preprocessor fails gracefully with no numeric cols."""
    _, mock_st = mock_streamlit

    manager = PreprocessorManager(mock_api)
    # Only string data
    manager.get_data = MagicMock(return_value=pd.DataFrame({"S": ["x"]}))

    manager.render()

    mock_st.warning.assert_called_once()
    assert "No numeric columns" in mock_st.warning.call_args[0][0]
