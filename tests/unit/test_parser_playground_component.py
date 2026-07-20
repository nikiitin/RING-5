"""Human-first parser playground dialog contracts."""

from __future__ import annotations

from concurrent.futures import Future
from unittest.mock import MagicMock, patch

from src.core.models import ParserPlaygroundBatchResult, ParserPlaygroundResult


def _context() -> MagicMock:
    context = MagicMock()
    context.__enter__.return_value = context
    context.__exit__.return_value = False
    return context


@patch("src.web.components.data_source.data_source_components.st")
def test_playground_dialog_shows_evidence_without_loading_workspace(mock_st: MagicMock) -> None:
    # [test->req~ring5.ingestion.parser-playground~1]
    from src.web.components.data_source.data_source_components import DataSourceComponents

    future: Future[dict[str, object]] = Future()
    future.set_result({"simTicks": 100})
    batch = ParserPlaygroundBatchResult(
        futures=[future],
        var_names=["simTicks"],
        output_dir="/preview",
        strategy_type="simple",
        matched_file_count=4,
        sampled_files=("/inputs/run-00/stats.txt",),
        diagnostics=("Previewed 1 of 4 matching files in lexical order.",),
    )
    result = ParserPlaygroundResult(
        matched_file_count=4,
        sampled_files=batch.sampled_files,
        columns=("simTicks",),
        rows=(("100",),),
        missing_variables=(),
        diagnostics=(
            "Previewed 1 of 4 matching files in lexical order.",
            "The sampled configuration is ready for a full parse.",
        ),
        ready_for_full_parse=True,
    )
    api = MagicMock()
    api.finalize_parser_playground.return_value = result
    mock_st.progress.return_value = MagicMock()
    mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
    mock_st.expander.return_value = _context()

    decorated = DataSourceComponents._show_parser_playground_dialog
    dialog = getattr(decorated, "__wrapped__", decorated)
    dialog(api, batch)

    api.finalize_parser_playground.assert_called_once_with(batch, [{"simTicks": 100}])
    api.add_to_csv_pool.assert_not_called()
    api.load_csv_file.assert_not_called()
    api.state_manager.set_data.assert_not_called()
    mock_st.code.assert_called_once_with("/inputs/run-00/stats.txt", language=None)
    mock_st.dataframe.assert_called_once()
    mock_st.success.assert_called_once_with("Ready for a full parse.")
