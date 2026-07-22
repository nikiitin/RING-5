"""Tests for the human-first review-before-load CSV workflow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from src.core.models import (
    ImportColumn,
    ImportColumnCorrection,
    ImportOptions,
    ImportPreview,
    ImportRejectedRow,
)


def _context() -> MagicMock:
    value = MagicMock()
    value.__enter__.return_value = value
    value.__exit__.return_value = False
    return value


def _preview(*, corrected: bool) -> ImportPreview:
    options = ImportOptions(
        column_types=(ImportColumnCorrection("score", "number"),) if corrected else (),
    )
    return ImportPreview(
        source_path="/pool/results.csv",
        source_sha256="a" * 64,
        encoding="utf-8",
        delimiter=";",
        options=options,
        columns=(
            ImportColumn("name", "text", "text", False),
            ImportColumn("score", "text", "number" if corrected else "text", False),
        ),
        rows=(("alpha", "1.5"),),
        accepted_row_count=1,
        rejected_row_count=1 if corrected else 0,
        total_row_count=2 if corrected else 1,
        rejected_rows=(
            (ImportRejectedRow(3, ("beta", "bad"), "Column 'score' expects number."),)
            if corrected
            else ()
        ),
    )


@patch("src.web.components.data_source.data_source_components.DataComponents")
@patch("src.web.components.data_source.data_source_components.st")
def test_review_applies_type_correction_and_loads_only_after_confirmation(
    mock_st: MagicMock, mock_data_components: MagicMock
) -> None:
    # [test->req~ring5.ingestion.import-preview~1]
    from src.web.components.data_source.data_source_components import DataSourceComponents

    mock_st.columns.side_effect = lambda count: [_context() for _index in range(int(count))]
    mock_st.selectbox.side_effect = ["Auto detect", "Auto detect"]
    mock_st.number_input.side_effect = [1, 50]
    mock_st.checkbox.return_value = True
    mock_st.text_input.return_value = ",NA,N/A,null,None"

    def edit_types(frame: pd.DataFrame, **_kwargs: object) -> pd.DataFrame:
        edited = frame.copy()
        edited.loc[edited["Column"] == "score", "Import as"] = "Number"
        return edited

    mock_st.data_editor.side_effect = edit_types
    mock_st.button.side_effect = [True, False]
    api = MagicMock()
    api.preview_import.side_effect = [_preview(corrected=False), _preview(corrected=True)]
    api.load_import_preview.return_value = pd.DataFrame({"name": ["alpha"], "score": [1.5]})

    DataSourceComponents.render_import_preview(api, "/pool/results.csv")

    assert api.preview_import.call_count == 2
    corrected_options = api.preview_import.call_args_list[1].args[1]
    assert corrected_options.column_types == (ImportColumnCorrection("score", "number"),)
    api.load_import_preview.assert_called_once_with(_preview(corrected=True))
    mock_st.warning.assert_called_once()
    mock_data_components.show_data_preview.assert_called_once()
