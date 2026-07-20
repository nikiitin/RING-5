"""Human-first browser-upload component tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.core.models import BrowserUpload
from src.web.components.data_source.data_source_components import DataSourceComponents
from tests.conftest import columns_side_effect


@patch("src.web.components.data_source.data_source_components.st")
def test_dataset_upload_routes_to_import_review(mock_st: MagicMock) -> None:
    # [test->req~ring5.ingestion.browser-upload~1]
    api = MagicMock()
    uploaded = MagicMock()
    uploaded.name = "measurements.json"
    uploaded.type = "application/json"
    uploaded.getvalue.return_value = b'[{"benchmark":"alpha","ipc":1.25}]'
    mock_st.file_uploader.return_value = uploaded
    mock_st.selectbox.return_value = "Auto detect"
    mock_st.columns.side_effect = columns_side_effect
    inspection = BrowserUpload(
        file_name="measurements.json",
        content_type="application/json",
        kind="json",
        size_bytes=34,
        source_sha256="a" * 64,
        source_path="/tmp/a.json",
        import_path="/tmp/a.normalized.csv",
        columns=("benchmark", "ipc"),
        row_count=1,
    )
    api.inspect_browser_upload.return_value = inspection

    with patch.object(DataSourceComponents, "render_import_preview") as render_preview:
        DataSourceComponents.render_browser_upload(api)

    api.inspect_browser_upload.assert_called_once_with(
        "measurements.json",
        "application/json",
        uploaded.getvalue.return_value,
        "auto",
    )
    render_preview.assert_called_once_with(api, "/tmp/a.normalized.csv")
    api.restore_browser_portfolio.assert_not_called()


@patch("src.web.components.data_source.data_source_components.st")
def test_invalid_upload_stays_out_of_the_workspace(mock_st: MagicMock) -> None:
    api = MagicMock()
    uploaded = MagicMock(name="bad upload")
    uploaded.name = "bad.csv"
    uploaded.type = "image/png"
    uploaded.getvalue.return_value = b"bad"
    mock_st.file_uploader.return_value = uploaded
    mock_st.selectbox.return_value = "Auto detect"
    api.inspect_browser_upload.side_effect = ValueError("declared media type does not match")

    DataSourceComponents.render_browser_upload(api)

    mock_st.error.assert_called_once()
    api.load_import_preview.assert_not_called()
    api.restore_browser_portfolio.assert_not_called()
