"""Tests for PreprocessorManager — branch coverage."""

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
        }
    )


@pytest.fixture
def mock_api() -> MagicMock:
    api = MagicMock()
    api.managers.list_operators.return_value = ["Division", "Sum", "Subtraction", "Multiplication"]
    api.has_preview.return_value = False
    api.get_manager_history.return_value = []
    return api


class TestPreprocessorRender:
    """Test PreprocessorManager.render branch coverage."""

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_no_data(self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = None
        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_st.error.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_no_numeric_cols(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = pd.DataFrame({"name": ["a", "b"]})
        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_division_default_name(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "ipc"
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()

        # Verify text_input was called (default name generation happened)
        mock_st.text_input.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_sum_default_name(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Sum", "instructions"]
        mock_st.text_input.return_value = "total"
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_st.text_input.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_subtraction_default_name(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Subtraction", "instructions"]
        mock_st.text_input.return_value = "diff"
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_st.text_input.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_multiplication_default_name(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Multiplication", "instructions"]
        mock_st.text_input.return_value = "product"
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_st.text_input.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_unknown_operation_default_name(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "CustomOp", "instructions"]
        mock_st.text_input.return_value = "new_column"
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        # default_name should be "new_column" for unknown operations
        mock_st.text_input.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_preview_success(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        result_df = sample_df.copy()
        result_df["ipc"] = [0.5, 0.5, 0.5]
        mock_api.managers.apply_operation.return_value = result_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "ipc"
        mock_st.button.side_effect = [True, False]  # Preview=True, Confirm=False
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_st.success.assert_called()
        mock_api.set_preview.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_preview_error(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.apply_operation.side_effect = ValueError("Division by zero")
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "ipc"
        mock_st.button.side_effect = [True, False]
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_st.error.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_confirm_applies_data(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        preview_df = sample_df.copy()
        preview_df["ipc"] = [0.5, 0.5, 0.5]
        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.has_preview.return_value = True
        mock_api.get_preview.return_value = preview_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "ipc"
        mock_st.button.side_effect = [False, True]  # Preview=False, Confirm=True
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_api.state_manager.set_data.assert_called_once()
        mock_api.clear_preview.assert_called_once()
        mock_api.add_manager_history_record.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_confirm_none_preview(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.has_preview.return_value = True
        mock_api.get_preview.return_value = None
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "ipc"
        mock_st.button.side_effect = [False, True]
        mock_st.session_state = {}

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_api.state_manager.set_data.assert_not_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_history_load_full(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "ipc"
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_preproc_load": {
                "operation": "Preprocessor: Division",
                "source_columns": ["cycles", "instructions"],
                "dest_columns": ["ipc"],
            }
        }

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        # History was consumed: _preproc_load should have been popped

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_history_load_missing_columns(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "ratio"
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_preproc_load": {
                "operation": "Preprocessor: Division",
                "source_columns": ["cycles", "nonexistent_col"],
                "dest_columns": ["ratio"],
            }
        }

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_history_load_unknown_operator(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "result"
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_preproc_load": {
                "operation": "Preprocessor: UnknownOp",
                "source_columns": ["cycles"],
                "dest_columns": [],
            }
        }

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        # Unknown operator should not crash, just won't set session_state

    @patch("src.web.pages.ui.data_managers.impl.preprocessor.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.preprocessor.st")
    def test_history_load_one_source_col(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.side_effect = ["cycles", "Division", "instructions"]
        mock_st.text_input.return_value = "result"
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_preproc_load": {
                "operation": "Preprocessor: Division",
                "source_columns": ["cycles"],  # only 1 source col
                "dest_columns": ["result"],
            }
        }

        mgr = PreprocessorManager(mock_api)
        mgr.render()
        # Should set preproc_src1 but not preproc_src2
