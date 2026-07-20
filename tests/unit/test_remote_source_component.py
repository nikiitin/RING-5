"""Remote-source form routing tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.core.models import BrowserUpload, HttpSource, RemoteSourcePolicy
from src.web.components.data_source.data_source_components import DataSourceComponents


@patch("src.web.components.data_source.data_source_components.RemoteSourcePolicy.from_environment")
@patch("src.web.components.data_source.data_source_components.st")
def test_remote_source_fetches_into_existing_import_review(
    mock_st: MagicMock,
    policy_from_environment: MagicMock,
) -> None:
    # [test->req~ring5.ingestion.remote-sources~1]
    policy = RemoteSourcePolicy(("data.example",))
    policy_from_environment.return_value = policy
    mock_st.session_state = {}
    mock_st.selectbox.return_value = "HTTPS"
    mock_st.text_input.side_effect = [
        "results.csv",
        "https://data.example/download?token=sensitive",
        "bearer-secret",
    ]
    mock_st.form_submit_button.return_value = True
    api = MagicMock()
    upload = BrowserUpload(
        file_name="results.csv",
        content_type="text/csv",
        kind="csv",
        size_bytes=20,
        source_sha256="a" * 64,
        source_path="/tmp/results.csv",
        import_path="/tmp/results.csv",
        columns=("benchmark", "ipc"),
        row_count=1,
        origin_display="https://data.example/download",
    )
    api.fetch_remote_source.return_value = upload

    with patch.object(DataSourceComponents, "_show_validated_upload") as show_upload:
        DataSourceComponents.render_remote_source(api)

    source = api.fetch_remote_source.call_args.args[0]
    assert isinstance(source, HttpSource)
    assert source.bearer_token == "bearer-secret"
    api.fetch_remote_source.assert_called_once_with(source, policy)
    show_upload.assert_called_once_with(api, upload)
