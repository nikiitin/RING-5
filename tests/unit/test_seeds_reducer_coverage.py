"""Tests for SeedsReducerManager — branch coverage."""

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
            "benchmark": ["a", "a", "b", "b"],
            "random_seed": ["1", "2", "1", "2"],
            "cycles": [100.0, 110.0, 200.0, 210.0],
            "ipc": [0.5, 0.55, 0.6, 0.65],
        }
    )


@pytest.fixture
def mock_api() -> MagicMock:
    api = MagicMock()
    api.has_preview.return_value = False
    api.get_manager_history.return_value = []
    return api


class TestSeedsReducerRender:
    """Test SeedsReducerManager.render branch coverage."""

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_no_data(self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        mock_api.state_manager.get_data.return_value = None
        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_st.error.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_no_random_seed_column(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        df = pd.DataFrame({"benchmark": ["a", "b"], "cycles": [100.0, 200.0]})
        mock_api.state_manager.get_data.return_value = df
        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_random_seed_in_numeric(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        # random_seed as numeric (int)
        df = pd.DataFrame(
            {
                "benchmark": ["a", "b"],
                "random_seed": [1, 2],  # numeric, not string
                "cycles": [100.0, 200.0],
            }
        )
        mock_api.state_manager.get_data.return_value = df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.side_effect = [["benchmark"], ["cycles"]]
        mock_st.button.return_value = False
        mock_st.session_state = {}

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        # random_seed should be removed from numeric_cols
        mock_st.multiselect.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_no_categorical_after_removing_seed(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        # Only categorical col is random_seed itself
        df = pd.DataFrame(
            {
                "random_seed": ["1", "2"],
                "cycles": [100.0, 200.0],
            }
        )
        mock_api.state_manager.get_data.return_value = df
        mock_st.session_state = {}

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_no_numeric_cols(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        df = pd.DataFrame(
            {
                "benchmark": ["a", "b"],
                "random_seed": ["1", "2"],
            }
        )
        mock_api.state_manager.get_data.return_value = df
        mock_st.session_state = {}

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_apply_success(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        reduced = pd.DataFrame(
            {
                "benchmark": ["a", "b"],
                "cycles": [105.0, 205.0],
                "cycles.sd": [5.0, 5.0],
            }
        )
        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_seeds_reducer_inputs.return_value = []
        mock_api.managers.reduce_seeds.return_value = reduced
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.side_effect = [["benchmark"], ["cycles", "ipc"]]
        mock_st.button.side_effect = [True, False]  # Apply=True, Confirm=False
        mock_st.session_state = {}

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_st.success.assert_called()
        mock_api.set_preview.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_apply_validation_errors(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_seeds_reducer_inputs.return_value = ["No cols selected"]
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.side_effect = [[], []]
        mock_st.button.side_effect = [True]  # Apply=True
        mock_st.session_state = {}

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_st.error.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_apply_exception(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.managers.validate_seeds_reducer_inputs.return_value = []
        mock_api.managers.reduce_seeds.side_effect = RuntimeError("Reduce failed")
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.side_effect = [["benchmark"], ["cycles"]]
        mock_st.button.side_effect = [True, False]
        mock_st.session_state = {}

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_st.error.assert_called()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_confirm_applies_data(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        reduced = pd.DataFrame({"benchmark": ["a", "b"], "cycles": [105.0, 205.0]})
        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.has_preview.return_value = True
        mock_api.get_preview.return_value = reduced
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.side_effect = [["benchmark"], ["cycles"]]
        mock_st.button.side_effect = [False, True]
        mock_st.session_state = {}

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_api.state_manager.set_data.assert_called_once()
        mock_api.clear_preview.assert_called_once()
        mock_api.add_manager_history_record.assert_called_once()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_confirm_none_preview(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_api.has_preview.return_value = True
        mock_api.get_preview.return_value = None
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.side_effect = [["benchmark"], ["cycles"]]
        mock_st.button.side_effect = [False, True]
        mock_st.session_state = {}

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_api.state_manager.set_data.assert_not_called()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_history_load_full(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.side_effect = [["benchmark"], ["cycles", "ipc"]]
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_seeds_load": {
                "source_columns": ["benchmark", "cycles", "ipc"],
                "dest_columns": ["cycles", "ipc"],
                "operation": "Seeds Reduction (mean + stdev)",
            }
        }

        mgr = SeedsReducerManager(mock_api)
        mgr.render()

    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.HistoryComponents")
    @patch("src.web.pages.ui.data_managers.impl.seeds_reducer.st")
    def test_history_load_missing_columns(
        self, mock_st: MagicMock, mock_hist: MagicMock, mock_api: MagicMock, sample_df: pd.DataFrame
    ) -> None:
        from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager

        mock_api.state_manager.get_data.return_value = sample_df
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.multiselect.side_effect = [["benchmark"], ["cycles"]]
        mock_st.button.return_value = False
        mock_st.session_state = {
            "_seeds_load": {
                "source_columns": ["benchmark", "missing_cat", "cycles"],
                "dest_columns": ["cycles", "missing_num"],
                "operation": "Seeds Reduction (mean + stdev)",
            }
        }

        mgr = SeedsReducerManager(mock_api)
        mgr.render()
        mock_st.warning.assert_called()
