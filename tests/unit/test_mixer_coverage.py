"""Tests for MixerManager — branch coverage."""

from typing import Any, List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _make_col_mock() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _columns_side_effect(n: Any) -> List[MagicMock]:
    count = len(n) if isinstance(n, list) else n
    return [_make_col_mock() for _ in range(count)]


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": ["a", "b", "c"],
            "cycles": [100.0, 200.0, 300.0],
            "instructions": [50.0, 100.0, 150.0],
            "cycles.sd": [5.0, 10.0, 15.0],
        }
    )


@pytest.fixture
def mock_api() -> MagicMock:
    api = MagicMock()
    api.has_preview.return_value = False
    api.get_manager_history.return_value = []
    return api


class TestMixerRender:
    """Test MixerManager.render branch coverage."""

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_no_data(self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = None
        mgr = MixerManager(mock_api)
        mgr.render()
        mock_st.error.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_numerical_mode(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = ["cycles", "instructions"]
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "total"
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = MixerManager(mock_api)
        mgr.render()
        mock_st.radio.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_config_merge_mode(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Configuration Merge"
        mock_st.multiselect.return_value = ["benchmark"]
        mock_st.selectbox.return_value = "Concatenate"
        mock_st.text_input.side_effect = ["_", "concat_benchmark"]  # separator, col name
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = MixerManager(mock_api)
        mgr.render()
        # Concatenate mode shows separator text_input
        assert mock_st.text_input.call_count >= 2

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_preview_success_with_sd(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        result_df = sample_df.copy()
        result_df["total"] = [150.0, 300.0, 450.0]
        result_df["total.sd"] = [7.07, 14.14, 21.21]
        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_merge_inputs.return_value = []
        mock_api.managers.apply_mixer.return_value = result_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = ["cycles", "instructions"]
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "total"
        mock_st.button.side_effect = [True, False]  # Preview=True, Confirm=False
        mock_st.session_state = {}

        mgr = MixerManager(mock_api)
        mgr.render()
        # Should detect the .sd column
        assert mock_st.success.call_count >= 2  # "Created" + "Propagated SD"
        mock_api.set_preview.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_preview_success_without_sd(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        result_df = sample_df.copy()
        result_df["total"] = [150.0, 300.0, 450.0]
        # No total.sd column
        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_merge_inputs.return_value = []
        mock_api.managers.apply_mixer.return_value = result_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = ["cycles", "instructions"]
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "total"
        mock_st.button.side_effect = [True, False]
        mock_st.session_state = {}

        mgr = MixerManager(mock_api)
        mgr.render()
        mock_api.set_preview.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_preview_validation_errors(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_merge_inputs.return_value = ["Select at least 2 columns"]
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = ["cycles"]
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "total"
        mock_st.button.side_effect = [True]
        mock_st.session_state = {}

        mgr = MixerManager(mock_api)
        mgr.render()
        mock_st.error.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_preview_exception(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_merge_inputs.return_value = []
        mock_api.managers.apply_mixer.side_effect = ValueError("Cannot merge")
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = ["cycles", "instructions"]
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "total"
        mock_st.button.side_effect = [True, False]
        mock_st.session_state = {}

        mgr = MixerManager(mock_api)
        mgr.render()
        mock_st.error.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_confirm_applies_data(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        merged = sample_df.copy()
        merged["total"] = [150.0, 300.0, 450.0]
        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.has_preview.return_value = True
        mock_api.get_preview.return_value = merged
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = ["cycles", "instructions"]
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "total"
        mock_st.button.side_effect = [False, True]  # Preview=False, Confirm=True
        mock_st.session_state = {}

        mgr = MixerManager(mock_api)
        mgr.render()
        mock_api.state_manager.set_data.assert_called_once()
        mock_api.clear_preview.assert_called_once()
        mock_api.add_manager_history_record.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_history_load_concatenate(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Configuration Merge"
        mock_st.multiselect.return_value = ["benchmark"]
        mock_st.selectbox.return_value = "Concatenate"
        mock_st.text_input.side_effect = ["_", "concat_col"]
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_mixer_load": {
                "operation": "Mixer: Concatenate",
                "source_columns": ["benchmark"],
                "dest_columns": ["concat_col"],
            }
        }

        mgr = MixerManager(mock_api)
        mgr.render()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_history_load_numerical(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = ["cycles", "instructions"]
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "total"
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_mixer_load": {
                "operation": "Mixer: Sum",
                "source_columns": ["cycles", "instructions"],
                "dest_columns": ["total"],
            }
        }

        mgr = MixerManager(mock_api)
        mgr.render()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_history_load_missing_columns(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = []
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "total"
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_mixer_load": {
                "operation": "Mixer: Sum",
                "source_columns": ["nonexistent1", "nonexistent2"],
                "dest_columns": ["total"],
            }
        }

        mgr = MixerManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.mixer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.mixer.st")
    def test_empty_multiselect_default_name(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.mixer import MixerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.radio.return_value = "Numerical Operations"
        mock_st.multiselect.return_value = []  # No cols selected → fallback name
        mock_st.selectbox.return_value = "Sum"
        mock_st.text_input.return_value = "sum_merged"
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = MixerManager(mock_api)
        mgr.render()
        # default_name_parts = ["merged"] when empty
        mock_st.text_input.assert_called()
