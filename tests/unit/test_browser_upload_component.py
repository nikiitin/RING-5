"""Human-first browser-upload component tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.core.models import BrowserUpload, PortfolioBundleInfo, PortfolioIntegrityReport
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


@patch("src.web.components.data_source.data_source_components.st")
def test_signed_portfolio_requires_secret_and_reports_key_id(mock_st: MagicMock) -> None:
    # [test->req~ring5.portfolio.signed-manifests~1]
    api = MagicMock()
    api.restore_browser_portfolio.return_value.complete = True
    mock_st.columns.side_effect = columns_side_effect
    mock_st.text_input.return_value = "shared secret"
    mock_st.button.return_value = True
    inspection = BrowserUpload(
        file_name="analysis.json",
        content_type="application/json",
        kind="portfolio",
        size_bytes=128,
        source_sha256="b" * 64,
        source_path="/tmp/analysis.json",
        portfolio_schema_version=4,
        portfolio_plot_count=2,
        portfolio_has_data=True,
        portfolio_integrity_status="signature-unverified",
        portfolio_signing_key_id="lab-key",
    )

    DataSourceComponents._show_validated_upload(api, inspection)

    mock_st.text_input.assert_called_once()
    assert "lab-key" in mock_st.caption.call_args.args[0]
    api.restore_browser_portfolio.assert_called_once_with(
        inspection,
        signing_key="shared secret",
        require_signature=True,
    )


@patch("src.web.components.data_source.data_source_components.st")
def test_portable_bundle_shows_artifacts_and_requires_signature_secret(
    mock_st: MagicMock,
) -> None:
    # [test->req~ring5.portfolio.portable-bundles~1]
    api = MagicMock()
    api.restore_browser_portfolio_bundle.return_value.complete = True
    mock_st.columns.side_effect = columns_side_effect
    mock_st.text_input.return_value = "shared bundle secret"
    mock_st.button.return_value = True
    integrity = PortfolioIntegrityReport(
        status="signature-unverified",
        message="Signature needs its secret.",
        checksum_valid=True,
        signature_present=True,
        signature_valid=None,
        key_id="transfer-key",
    )
    info = PortfolioBundleInfo(
        name="portable-analysis",
        format_version=1,
        portfolio_schema_version=4,
        portfolio_created_at="2026-07-21T10:00:00+00:00",
        size_bytes=512,
        source_count=1,
        requirement_count=3,
        portfolio_integrity=integrity,
        dataset_snapshot=None,
        result_names=("report.html",),
        artifacts=(),
    )
    inspection = BrowserUpload(
        file_name="portable-analysis.ring5-bundle",
        content_type="application/zip",
        kind="bundle",
        size_bytes=512,
        source_sha256="c" * 64,
        source_path="/tmp/portable-analysis.ring5-bundle",
        bundle_info=info,
    )

    DataSourceComponents._show_validated_upload(api, inspection)

    assert "report.html" in mock_st.caption.call_args_list[0].args[0]
    api.restore_browser_portfolio_bundle.assert_called_once_with(
        inspection,
        signing_key="shared bundle secret",
        require_signature=True,
    )
