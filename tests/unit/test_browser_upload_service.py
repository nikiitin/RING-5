"""Tests for bounded browser-upload validation and normalization."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from src.core.services.browser_upload_service import BrowserUploadService
from src.core.services.import_preview_service import ImportPreviewService


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Measurements"
    sheet.append(["benchmark", "ipc", "stable"])
    sheet.append(["alpha", 1.25, True])
    sheet.append(["beta", 1.5, False])
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_csv_json_and_excel_uploads_become_reviewable_tables(tmp_path: Path) -> None:
    # [test->req~ring5.ingestion.browser-upload~1]
    destination = tmp_path / "uploads"
    csv_upload = BrowserUploadService.inspect(
        "measurements.csv",
        "text/csv",
        b"benchmark,ipc\nalpha,1.25\n",
        destination,
    )
    json_upload = BrowserUploadService.inspect(
        "measurements.json",
        "application/json",
        json.dumps(
            [
                {"benchmark": "alpha", "ipc": 1.25},
                {"benchmark": "beta", "ipc": 1.5},
            ]
        ).encode(),
        destination,
    )
    excel_upload = BrowserUploadService.inspect(
        "measurements.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        _workbook_bytes(),
        destination,
    )

    assert csv_upload.kind == "csv"
    assert csv_upload.row_count == 1
    assert json_upload.kind == "json"
    assert json_upload.columns == ("benchmark", "ipc")
    assert json_upload.row_count == 2
    assert excel_upload.kind == "excel"
    assert excel_upload.sheet_name == "Measurements"
    assert excel_upload.row_count == 2
    assert all(upload.source_sha256 for upload in (csv_upload, json_upload, excel_upload))
    for upload in (csv_upload, json_upload, excel_upload):
        assert upload.import_path is not None
        assert (
            ImportPreviewService.preview(upload.import_path).accepted_row_count == upload.row_count
        )


@pytest.mark.parametrize(
    ("name", "media_type", "content", "message"),
    [
        ("../values.csv", "text/csv", b"a\n1\n", "filename"),
        ("values.csv", "image/png", b"a\n1\n", "media type"),
        ("values.json", "application/json", b'[{"a": {"nested": 1}}]', "scalar"),
        ("values.xlsx", "application/octet-stream", b"not a zip", "valid .xlsx"),
    ],
)
def test_upload_validation_rejects_unsafe_or_mismatched_content(
    tmp_path: Path,
    name: str,
    media_type: str,
    content: bytes,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        BrowserUploadService.inspect(name, media_type, content, tmp_path)


def test_portfolio_is_summarized_and_revalidated_before_restore(tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "schema_version": 3,
            "data_csv": "benchmark,ipc\nalpha,1.25\n",
            "plots": [],
            "config": {},
        }
    ).encode()
    upload = BrowserUploadService.inspect(
        "analysis.json",
        "application/json",
        payload,
        tmp_path,
    )

    assert upload.kind == "portfolio"
    assert upload.portfolio_schema_version == 3
    assert upload.portfolio_plot_count == 0
    assert upload.portfolio_has_data is True
    assert BrowserUploadService.load_portfolio(upload)["data_csv"].startswith("benchmark")

    Path(upload.source_path).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="changed after validation"):
        BrowserUploadService.load_portfolio(upload)


def test_csv_uses_browser_specific_size_row_and_cell_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.core.services.browser_upload_service as upload_module

    monkeypatch.setattr(upload_module, "MAX_BROWSER_UPLOAD_ROWS", 1)
    with pytest.raises(ValueError, match="at most 1 rows"):
        BrowserUploadService.inspect(
            "rows.csv",
            "text/csv",
            b"value\n1\n2\n",
            tmp_path,
        )

    monkeypatch.setattr(upload_module, "MAX_BROWSER_UPLOAD_ROWS", 100_000)
    monkeypatch.setattr(upload_module, "MAX_BROWSER_UPLOAD_CELL_LENGTH", 3)
    with pytest.raises(ValueError, match="3-character"):
        BrowserUploadService.inspect(
            "cells.csv",
            "text/csv",
            b"value\ntoolong\n",
            tmp_path,
        )

    monkeypatch.setattr(upload_module, "MAX_BROWSER_UPLOAD_BYTES", 4)
    with pytest.raises(ValueError, match="exceeds"):
        BrowserUploadService.inspect(
            "size.csv",
            "text/csv",
            b"a\n123\n",
            tmp_path,
        )
