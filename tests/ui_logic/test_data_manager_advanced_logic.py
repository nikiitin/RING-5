from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.ui.data_managers.mixer import MixerManager
from src.web.ui.data_managers.preprocessor import PreprocessorManager


@pytest.fixture
def mock_streamlit():
    with patch("src.web.ui.data_managers.mixer.st") as mock_st_mixer, patch(
        "src.web.ui.data_managers.preprocessor.st"
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
def sample_data():
    return pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6], "S": ["x", "y", "z"]})


def test_mixer_render_numeric_op(mock_streamlit, sample_data):
    """Test Mixer numeric operation workflow."""
    mock_st, _ = mock_streamlit

    manager = MixerManager()
    manager.get_data = MagicMock(return_value=sample_data)
    manager.set_data = MagicMock()

    # Interactions:
    # Radio Mode -> "Numerical Operations"
    # Multiselect Cols -> ["A", "B"]
    # Selectbox Op -> "Sum"
    # TextInput Name -> "merged"
    # Button Preview -> True

    mock_st.radio.return_value = "Numerical Operations"
    mock_st.multiselect.return_value = ["A", "B"]
    mock_st.selectbox.return_value = "Sum"
    mock_st.text_input.return_value = "merged"
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "mixer_preview"

    with patch(
        "src.web.services.data_processing_service.DataProcessingService.apply_mixer"
    ) as mock_apply:
        result_df = pd.DataFrame({"A": [1], "B": [4], "merged": [5]})
        mock_apply.return_value = result_df

        manager.render()

        mock_apply.assert_called_once()
        assert "mixer_result" in mock_st.session_state
        mock_st.success.assert_called()


def test_mixer_confirm(mock_streamlit, sample_data):
    """Test Mixer confirm workflow."""
    mock_st, _ = mock_streamlit

    manager = MixerManager()
    manager.get_data = MagicMock(return_value=sample_data)
    manager.set_data = MagicMock()

    # Pre-populate session state
    result_df = pd.DataFrame({"merged": [1]})
    mock_st.session_state["mixer_result"] = result_df

    # Simulate button interactions: Confirm clicked
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "confirm_mixer"

    manager.render()

    manager.set_data.assert_called_with(result_df)
    assert "mixer_result" not in mock_st.session_state


def test_preprocessor_render_op(mock_streamlit, sample_data):
    """Test Preprocessor operation workflow."""
    _, mock_st = mock_streamlit

    manager = PreprocessorManager()
    manager.get_data = MagicMock(return_value=sample_data)

    # Interactions:
    # Select Src1 -> A
    # Select Op -> Divide
    # Select Src2 -> B
    # Text Name -> "new_col"
    # Button Preview -> True

    mock_st.selectbox.side_effect = ["A", "Divide", "B"]
    mock_st.text_input.return_value = "new_col"
    mock_st.button.side_effect = lambda label, key=None, **kwargs: key == "preview_preproc"

    # Mock DataProcessingService
    with patch(
        "src.web.services.data_processing_service.DataProcessingService.apply_operation"
    ) as mock_op:
        with patch(
            "src.web.services.data_processing_service.DataProcessingService.list_operators"
        ) as mock_list:
            mock_list.return_value = ["Divide"]
            result_df = pd.DataFrame({"A": [1], "B": [4], "new_col": [0.25]})
            mock_op.return_value = result_df

            manager.render()

            mock_op.assert_called_once()

            # Debug failure if it happens
            if "preproc_result" not in mock_st.session_state:
                print(f"ST ERROR CALLS: {mock_st.error.call_args_list}")

            assert "preproc_result" in mock_st.session_state


def test_preprocessor_no_numeric_cols(mock_streamlit):
    """Test Preprocessor fails gracefully with no numeric cols."""
    _, mock_st = mock_streamlit

    manager = PreprocessorManager()
    # Only string data
    manager.get_data = MagicMock(return_value=pd.DataFrame({"S": ["x"]}))

    manager.render()

    mock_st.warning.assert_called_once()
    assert "No numeric columns" in mock_st.warning.call_args[0][0]
