"""Tests for HistoryComponents — branch coverage."""

from typing import List
from unittest.mock import MagicMock, patch

from src.core.models.history_models import OperationRecord
from src.web.pages.ui.components.history_components import HistoryComponents


def _make_record(
    op: str = "Preprocessor: Division",
    src: List[str] | None = None,
    dst: List[str] | None = None,
    ts: str = "2024-01-15T10:30:00",
) -> OperationRecord:
    return {
        "operation": op,
        "source_columns": src or ["col_a", "col_b"],
        "dest_columns": dst or ["col_c"],
        "timestamp": ts,
    }


def _columns_side_effect(n: "int | list[int]") -> "list[MagicMock]":
    count = len(n) if isinstance(n, list) else n
    cols = []
    for _ in range(count):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        cols.append(m)
    return cols


class TestRenderHistoryTable:
    """Test render_history_table."""

    @patch("src.web.pages.ui.components.history_components.st")
    def test_empty_records_noop(self, mock_st: MagicMock) -> None:
        HistoryComponents.render_history_table([])
        mock_st.dataframe.assert_not_called()

    @patch("src.web.pages.ui.components.history_components.st")
    def test_with_title(self, mock_st: MagicMock) -> None:
        records = [_make_record()]
        HistoryComponents.render_history_table(records, title="My History")
        mock_st.markdown.assert_any_call("#### My History")
        mock_st.dataframe.assert_called_once()

    @patch("src.web.pages.ui.components.history_components.st")
    def test_without_title(self, mock_st: MagicMock) -> None:
        records = [_make_record()]
        HistoryComponents.render_history_table(records)
        # markdown should not be called with #### prefix
        for c in mock_st.markdown.call_args_list:
            assert not c[0][0].startswith("####")
        mock_st.dataframe.assert_called_once()

    @patch("src.web.pages.ui.components.history_components.st")
    def test_multiple_records_reversed(self, mock_st: MagicMock) -> None:
        r1 = _make_record(ts="2024-01-01T00:00:00")
        r2 = _make_record(ts="2024-01-02T00:00:00")
        HistoryComponents.render_history_table([r1, r2])
        # Get the DataFrame passed to st.dataframe
        df = mock_st.dataframe.call_args[0][0]
        # Should be reversed: r2 first
        assert df.iloc[0]["Timestamp"] == "2024-01-02 00:00:00"


class TestRenderManagerHistory:
    """Test render_manager_history."""

    @patch("src.web.pages.ui.components.history_components.st")
    def test_no_matching_records(self, mock_st: MagicMock) -> None:
        records = [_make_record(op="Outlier: Q3")]
        HistoryComponents.render_manager_history(records, "Preprocessor", "_load_key", MagicMock())
        mock_st.expander.assert_not_called()

    @patch("src.web.pages.ui.components.history_components.st")
    def test_matching_records_renders_expander(self, mock_st: MagicMock) -> None:
        records = [_make_record(op="Preprocessor: Division")]
        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = False

        HistoryComponents.render_manager_history(records, "Preprocessor", "_load_key", MagicMock())
        mock_st.expander.assert_called_once()

    @patch("src.web.pages.ui.components.history_components.st")
    def test_operation_display_strips_prefix(self, mock_st: MagicMock) -> None:
        records = [_make_record(op="Preprocessor: Division")]
        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = False

        HistoryComponents.render_manager_history(records, "Preprocessor", "_load_key", MagicMock())
        # Verify st.text was called with "Division" (stripped prefix)
        text_calls = [c[0][0] for c in mock_st.text.call_args_list]
        assert "Division" in text_calls

    @patch("src.web.pages.ui.components.history_components.st")
    def test_load_button_sets_session_state(self, mock_st: MagicMock) -> None:
        record = _make_record()
        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp
        mock_st.columns.side_effect = _columns_side_effect
        # First button (load) returns True; second (delete) returns False
        mock_st.button.side_effect = [True, False]
        mock_st.session_state = {}

        HistoryComponents.render_manager_history(
            [record], "Preprocessor", "_preproc_load", MagicMock()
        )
        assert mock_st.session_state["_preproc_load"] == record
        mock_st.rerun.assert_called()

    @patch("src.web.pages.ui.components.history_components.st")
    def test_delete_button_calls_callback(self, mock_st: MagicMock) -> None:
        record = _make_record()
        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp
        mock_st.columns.side_effect = _columns_side_effect
        # First button (load) returns False; second (delete) returns True
        mock_st.button.side_effect = [False, True]

        delete_cb = MagicMock()
        HistoryComponents.render_manager_history([record], "Preprocessor", "_load_key", delete_cb)
        delete_cb.assert_called_once_with(record)
        mock_st.rerun.assert_called()


class TestRenderPortfolioHistory:
    """Test render_portfolio_history."""

    @patch("src.web.pages.ui.components.history_components.st")
    def test_empty_records_warning(self, mock_st: MagicMock) -> None:
        HistoryComponents.render_portfolio_history([])
        mock_st.warning.assert_called_once()

    @patch("src.web.pages.ui.components.history_components.st")
    def test_with_records_shows_metric(self, mock_st: MagicMock) -> None:
        records = [_make_record(), _make_record()]
        HistoryComponents.render_portfolio_history(records)
        mock_st.metric.assert_called_once_with("Total Operations", 2)
        mock_st.dataframe.assert_called_once()
