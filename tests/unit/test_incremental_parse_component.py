"""Human-facing incremental parse progress and reuse summary tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from src.core.models import IncrementalParseBatchResult, IncrementalParseResult


def _context() -> MagicMock:
    context = MagicMock()
    context.__enter__.return_value = context
    context.__exit__.return_value = False
    return context


@patch("src.web.components.data_source.data_source_components.DataComponents")
@patch("src.web.components.data_source.data_source_components.st")
def test_incremental_dialog_finalizes_an_all_reused_batch(
    mock_st: MagicMock,
    mock_data_components: MagicMock,
    tmp_path: Path,
) -> None:
    # [test->req~ring5.ingestion.incremental-parsing~1]
    from src.web.components.data_source.data_source_components import DataSourceComponents

    output = tmp_path / "results.csv"
    output.write_text("simTicks\n100\n", encoding="utf-8")
    batch = IncrementalParseBatchResult(
        futures=[],
        var_names=["simTicks"],
        output_dir=str(tmp_path),
        strategy_type="simple",
        cache_path=str(tmp_path / "cache.json"),
        configuration_hash="a" * 64,
        fingerprints=(("/inputs/run/stats.txt", "b" * 64),),
        cached_rows=(("/inputs/run/stats.txt", (("simTicks", "100"),)),),
        changed_files=(),
        removed_files=(),
    )
    api = MagicMock()
    api.state_manager.get_parser_strategy.return_value = "simple"
    api.finalize_incremental_parsing.return_value = IncrementalParseResult(str(output), 0, 1, 0, 1)
    api.add_to_csv_pool.return_value = str(output)
    api.load_csv_file.return_value = pd.DataFrame({"simTicks": [100]})
    mock_st.progress.return_value = MagicMock()
    mock_st.empty.return_value = MagicMock()
    mock_st.status.return_value = _context()
    mock_st.button.return_value = False

    decorated = DataSourceComponents._show_parse_dialog
    dialog = getattr(decorated, "__wrapped__", decorated)
    dialog(api, batch, str(tmp_path))

    api.finalize_incremental_parsing.assert_called_once_with(batch, [])
    mock_st.write.assert_any_call("Incremental update: 0 new or changed, 1 unchanged, 0 removed.")
    mock_st.write.assert_any_call("Updated 1 rows: parsed 0, reused 1, removed 0.")
    mock_data_components.show_missing_data_notice.assert_called_once()
