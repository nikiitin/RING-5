"""Application-boundary remote source review tests."""

from __future__ import annotations

from src.core.application_api import ApplicationAPI
from src.core.models import HttpSource, RemoteDownload, RemoteSourcePolicy
from src.core.services.remote_source_service import RemoteSourceService


class _Adapter:
    def fetch(self, source: object, policy: RemoteSourcePolicy) -> RemoteDownload:
        assert isinstance(source, HttpSource)
        assert policy.allowed_hosts == ("data.example",)
        return RemoteDownload(
            adapter="http",
            display_uri="https://data.example/results.csv",
            file_name="results.csv",
            content_type="text/csv",
            content=b"benchmark,ipc\nalpha,1.25\n",
        )


def test_remote_download_is_staged_for_review_before_load() -> None:
    # [test->req~ring5.ingestion.remote-sources~1]
    api = ApplicationAPI(remote_source_service=RemoteSourceService({"http": _Adapter()}))
    try:
        upload = api.fetch_remote_source(
            HttpSource("https://data.example/results.csv"),
            RemoteSourcePolicy(("data.example",)),
        )

        assert api.state_manager.get_data() is None
        assert upload.origin_display == "https://data.example/results.csv"
        assert upload.import_path is not None
        preview = api.preview_import(upload.import_path)
        assert api.state_manager.get_data() is None

        data = api.load_import_preview(preview)
        assert data.to_dict("records") == [{"benchmark": "alpha", "ipc": 1.25}]
    finally:
        api.state_manager.clear_data()
