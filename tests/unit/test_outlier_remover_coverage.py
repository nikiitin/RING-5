"""Tests for OutlierRemoverManager — branch coverage."""

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
            "benchmark": ["a", "b", "c", "d", "e"],
            "config": ["x", "x", "y", "y", "z"],
            "cycles": [100.0, 200.0, 300.0, 400.0, 9999.0],
            "ipc": [0.5, 0.6, 0.7, 0.8, 0.1],
        }
    )


@pytest.fixture
def mock_api() -> MagicMock:
    api = MagicMock()
    api.has_preview.return_value = False
    api.get_manager_history.return_value = []
    return api


class TestOutlierRemoverRender:
    """Test OutlierRemoverManager.render branch coverage."""

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_no_data(self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        mock_api.state_manager.get_data.return_value = None
        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_st.error.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_no_numeric_cols(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        mock_api.state_manager.get_data.return_value = pd.DataFrame({"name": ["a", "b"]})
        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_with_categorical_cols(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.multiselect.return_value = ["benchmark"]
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_st.multiselect.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_no_categorical_cols(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        # Only numeric cols, no categorical
        df = pd.DataFrame({"cycles": [100.0, 200.0], "ipc": [0.5, 0.6]})
        mock_api.state_manager.get_data.return_value = df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_st.info.assert_called()  # "No categorical columns for grouping"

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_seed_cols_filtered_out(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        # All categorical cols contain "seed" → fallback to first 3
        df = pd.DataFrame(
            {
                "random_seed": ["1", "2", "3"],
                "seed_value": ["a", "b", "c"],
                "cycles": [100.0, 200.0, 300.0],
            }
        )
        mock_api.state_manager.get_data.return_value = df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.multiselect.return_value = []
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        # Should have called multiselect with fallback default_cols
        mock_st.multiselect.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_apply_success(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_outlier_inputs.return_value = []
        mock_api.managers.remove_outliers.return_value = sample_df.iloc[:4]
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.multiselect.return_value = ["benchmark"]
        mock_st.button.side_effect = [True, False]  # Apply=True, Confirm=False
        mock_st.session_state = {}

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_st.success.assert_called()
        mock_api.set_preview.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_apply_validation_errors(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_outlier_inputs.return_value = ["col not found"]
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.multiselect.return_value = ["benchmark"]
        mock_st.button.side_effect = [True]  # Apply=True
        mock_st.session_state = {}

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_st.error.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_apply_exception(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_outlier_inputs.return_value = []
        mock_api.managers.remove_outliers.side_effect = RuntimeError("IQR error")
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.multiselect.return_value = ["benchmark"]
        mock_st.button.side_effect = [True, False]
        mock_st.session_state = {}

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_st.error.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_confirm_applies_data(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        filtered = sample_df.iloc[:4]
        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.has_preview.return_value = True
        mock_api.get_preview.return_value = filtered
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.multiselect.return_value = ["benchmark"]
        mock_st.button.side_effect = [False, True]  # Apply=False, Confirm=True
        mock_st.session_state = {}

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_api.state_manager.set_data.assert_called_once()
        mock_api.clear_preview.assert_called_once()
        mock_api.add_manager_history_record.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_history_load_full(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.multiselect.return_value = ["benchmark"]
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_outlier_load": {
                "source_columns": ["benchmark", "cycles"],
                "dest_columns": ["cycles"],
                "operation": "Outlier Removal (Q3)",
            }
        }

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()

    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.outlier_remover.st")
    def test_history_load_missing_col(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.selectbox.return_value = "cycles"
        mock_st.multiselect.return_value = []
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_outlier_load": {
                "source_columns": ["nonexistent_group", "missing_outlier_col"],
                "dest_columns": ["missing_outlier_col"],
                "operation": "Outlier Removal (Q3)",
            }
        }

        mgr = OutlierRemoverManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()
